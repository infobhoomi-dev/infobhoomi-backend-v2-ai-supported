"""
IFC4 → CityJSON Cadastral Converter (InfoBhoomi 3D Cadastre)
============================================================

Consolidated converter for the InfoBhoomi 3D-cadastre pipeline. Builds on the
backbone of ifc_to_cityjson_FINAL.py (semantic surfaces, attribute/property-set
extraction) + ifc2cityjson_vox.py (CityJSON structure), and ADDS the two pieces
the cadastre needs and neither original had:

  1. FootprintExtractor  — 2D building outline (EPSG:4326) for the parcel layer.
  2. TransformParams      — MANUAL georeferencing (anchor / rotation / scale),
                            because most IFC files carry no valid IfcMapConversion.

Outputs, all derived from ONE transform pass so 2D and 3D cannot drift:
  * CityJSON 2.0 — vertices in a local metric ENU frame (metres), with the
    geographic anchor stored in metadata.georeferencing (the iTowns/three.js
    way of placing a local model on a map). Rooms = "BuildingRoom" units.
  * footprint    — shapely Polygon in EPSG:4326 (lon/lat) for survey_rep.geom.
  * per-unit solids — MULTIPOLYGON Z WKT in EPSG:4326 for la_ls_build_unit.geom_3d
    (GEOS-parseable; feeds the existing Bld_Unit_Create_View geom_3d_wkt path).

CRS strategy: rotate/scale/union math is done in LOCAL METRES; only the final
geographic outputs (footprint, solids) are projected to 4326. Projection uses
pyproj if available, else an equirectangular tangent-plane approximation around
the anchor (accurate to well within a building footprint).

Library API:
    process_ifc(ifc_path, transform=None) -> ConversionResult
    convert_ifc_to_cityjson(ifc_path, transform=None) -> dict
    extract_footprint(ifc_path, transform=None) -> shapely.Polygon | None

CLI:
    python ifc2cityjson_cadastral.py input.ifc output.json \
        [--lon 79.86 --lat 6.92 --rotation 0 --scale 1]
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement

try:
    import ifcopenshell.util.unit as _ifc_unit
except Exception:  # pragma: no cover
    _ifc_unit = None

try:
    from shapely.geometry import Polygon, MultiPolygon
    from shapely.ops import unary_union
    SHAPELY_AVAILABLE = True
    try:
        from shapely import make_valid as _shp_make_valid
    except Exception:  # shapely < 2.0
        _shp_make_valid = None
    try:
        from shapely import set_precision as _shp_set_precision
    except Exception:  # shapely < 2.0
        _shp_set_precision = None
except ImportError:  # pragma: no cover
    SHAPELY_AVAILABLE = False
    _shp_make_valid = None
    _shp_set_precision = None

# Grid size (degrees) for footprint precision reduction. ~1e-7 deg ≈ 1.1 cm —
# fine for a building footprint, and snapping to this grid removes the
# near-degenerate self-intersections that differ between GEOS versions
# (system shapely vs the GDAL/PostGIS GEOS the DB writes go through).
_FOOTPRINT_GRID_DEG = 1e-7

logger = logging.getLogger(__name__)

WGS84_A = 6378137.0  # WGS84 semi-major axis (m)


# ---------------------------------------------------------------------------
# Manual georeferencing
# ---------------------------------------------------------------------------

@dataclass
class TransformParams:
    """Manual placement of an IFC model onto a parcel.

    The IFC local point ``src_anchor_xy`` (metres) is mapped to the geographic
    point (``anchor_lon``, ``anchor_lat``); the model is rotated CCW by
    ``rotation_deg`` about the vertical axis and uniformly ``scale``-d.

        world_enu = scale * R(rotation) * (local_xy - src_anchor_xy)
        world_z   = base_z + scale * local_z
    """
    anchor_lon: float = 0.0
    anchor_lat: float = 0.0
    base_z: float = 0.0
    rotation_deg: float = 0.0
    scale: float = 1.0
    src_anchor_xy: Tuple[float, float] = (0.0, 0.0)
    # Diagnostics populated when built from anchor pairs (Part A):
    method: str = "manual_placement"
    fit_rms_m: Optional[float] = None       # RMS residual of the fit (metres)
    n_anchors: int = 0

    def as_metadata(self) -> Dict[str, Any]:
        meta = {
            "method": self.method,
            "anchor_lon": self.anchor_lon,
            "anchor_lat": self.anchor_lat,
            "base_z": self.base_z,
            "rotation_deg": self.rotation_deg,
            "scale": self.scale,
            "src_anchor_xy": list(self.src_anchor_xy),
            "crs": "EPSG:4326",
        }
        if self.n_anchors:
            meta["n_anchors"] = self.n_anchors
        if self.fit_rms_m is not None:
            meta["fit_rms_m"] = round(self.fit_rms_m, 4)
        return meta

    @classmethod
    def from_anchor_pairs(cls, pairs, base_z: float = 0.0) -> "TransformParams":
        """Derive a 2D similarity (Helmert) transform from >=2 anchor pairs.

        Each pair maps an IFC-local point to a WGS84 point:
            { "local": [x, y, z?], "lon": <deg>, "lat": <deg> }

        With 2 pairs the transform (rotation, uniform scale, translation) is
        exact; with 3+ it is least-squares fitted and ``fit_rms_m`` reports the
        residual so a mis-typed control point is visible. The world side is
        worked in local ENU metres around the first anchor's latitude (the same
        equirectangular frame the converter uses), then the solved origin is
        expressed back as anchor_lon/anchor_lat.
        """
        norm = []
        for p in pairs:
            loc = p.get("local") or [p.get("x"), p.get("y"), p.get("z", 0.0)]
            lon = float(p["lon"])
            lat = float(p["lat"])
            norm.append(((float(loc[0]), float(loc[1])), (lon, lat)))
        if len(norm) < 2:
            raise ValueError("from_anchor_pairs requires at least 2 anchor pairs.")

        # ENU metres around the first anchor's latitude
        lat0 = norm[0][1][1]
        m_per_deg_lat = math.pi * WGS84_A / 180.0
        m_per_deg_lon = m_per_deg_lat * math.cos(math.radians(lat0))
        lon0, lat0v = norm[0][1]

        src = [(lx, ly) for (lx, ly), _ in norm]
        dst = [((lon - lon0) * m_per_deg_lon, (lat - lat0v) * m_per_deg_lat)
               for _, (lon, lat) in norm]

        # centroids
        n = len(norm)
        sx = sum(p[0] for p in src) / n
        sy = sum(p[1] for p in src) / n
        dx = sum(p[0] for p in dst) / n
        dy = sum(p[1] for p in dst) / n

        # similarity solve (Umeyama, 2D): scale s, rotation theta
        Sxx = Syy = Sxy = Syx = 0.0
        var_src = 0.0
        for (lx, ly), (wx, wy) in zip(src, dst):
            ax, ay = lx - sx, ly - sy
            bx, by = wx - dx, wy - dy
            Sxx += ax * bx
            Syy += ay * by
            Sxy += ax * by
            Syx += ay * bx
            var_src += ax * ax + ay * ay
        # rotation that best maps src->dst
        theta = math.atan2(Sxy - Syx, Sxx + Syy)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        scale = ((Sxx + Syy) * cos_t + (Sxy - Syx) * sin_t) / var_src if var_src else 1.0
        if scale <= 0:
            scale = 1.0

        # world position of the IFC local origin (0,0):
        #   world = s*R*(local - src_centroid) + dst_centroid
        ox = scale * (cos_t * (0 - sx) - sin_t * (0 - sy)) + dx
        oy = scale * (sin_t * (0 - sx) + cos_t * (0 - sy)) + dy
        anchor_lon = lon0 + (ox / m_per_deg_lon if m_per_deg_lon else 0.0)
        anchor_lat = lat0v + (oy / m_per_deg_lat)

        # residual RMS (metres) for quality reporting
        sq = 0.0
        for (lx, ly), (wx, wy) in zip(src, dst):
            px = scale * (cos_t * lx - sin_t * ly)
            py = scale * (sin_t * lx + cos_t * ly)
            # predicted world relative to origin uses local (not centred):
            pred_x = scale * (cos_t * lx - sin_t * ly) + (ox - scale * (cos_t * 0 - sin_t * 0))
            pred_y = scale * (sin_t * lx + cos_t * ly) + (oy - scale * (sin_t * 0 + cos_t * 0))
            sq += (pred_x - wx) ** 2 + (pred_y - wy) ** 2
        rms = math.sqrt(sq / n)

        return cls(
            anchor_lon=anchor_lon,
            anchor_lat=anchor_lat,
            base_z=base_z,
            rotation_deg=math.degrees(theta),
            scale=scale,
            src_anchor_xy=(0.0, 0.0),  # origin already solved into anchor_lon/lat
            method="anchor_pairs",
            fit_rms_m=rms,
            n_anchors=n,
        )


class GeoProjector:
    """Local metric ENU (metres, origin at the anchor) → geographic lon/lat.

    Uses an equirectangular approximation around the anchor latitude. This is
    sub-centimetre accurate over the extent of a single building and needs no
    pyproj. (A projected-CRS path can be added later via pyproj for large areas.)
    """

    def __init__(self, anchor_lon: float, anchor_lat: float):
        self.anchor_lon = anchor_lon
        self.anchor_lat = anchor_lat
        self._m_per_deg_lat = math.pi * WGS84_A / 180.0
        self._m_per_deg_lon = self._m_per_deg_lat * math.cos(math.radians(anchor_lat))

    def enu_to_lonlat(self, east_m: float, north_m: float) -> Tuple[float, float]:
        lon = self.anchor_lon + (east_m / self._m_per_deg_lon if self._m_per_deg_lon else 0.0)
        lat = self.anchor_lat + (north_m / self._m_per_deg_lat)
        return lon, lat


class Transformer:
    """Applies a TransformParams to IFC-world vertices, producing both the local
    metric ENU coords (for CityJSON) and geographic lon/lat (for PostGIS)."""

    def __init__(self, params: TransformParams):
        self.p = params
        self._cos = math.cos(math.radians(params.rotation_deg))
        self._sin = math.sin(math.radians(params.rotation_deg))
        self._geo = GeoProjector(params.anchor_lon, params.anchor_lat)

    def to_enu(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        dx = x - self.p.src_anchor_xy[0]
        dy = y - self.p.src_anchor_xy[1]
        ex = self.p.scale * (dx * self._cos - dy * self._sin)
        ny = self.p.scale * (dx * self._sin + dy * self._cos)
        ez = self.p.base_z + self.p.scale * z
        return ex, ny, ez

    def to_lonlat(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        ex, ny, ez = self.to_enu(x, y, z)
        lon, lat = self._geo.enu_to_lonlat(ex, ny)
        return lon, lat, ez


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass
class UnitResult:
    """A single room/space (a 'unit' in the cadastral model)."""
    guid: str
    name: str
    cityjson_id: str
    floor: Optional[str] = None
    area_m2: Optional[float] = None
    solid_wkt_4326: Optional[str] = None     # MULTIPOLYGON Z, lon/lat/z(m)
    is_fallback: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionResult:
    cityjson: Dict[str, Any]
    footprint: Any = None                     # shapely Polygon (EPSG:4326) | None
    footprint_wkt_4326: Optional[str] = None
    units: List[UnitResult] = field(default_factory=list)
    building_guid: Optional[str] = None
    building_name: Optional[str] = None
    stats: Dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# IFC reading
# ---------------------------------------------------------------------------

def _make_settings():
    """Build ifcopenshell geom settings across 0.7/0.8 API variants."""
    s = ifcopenshell.geom.settings()

    def _set(name_attr, name_str):
        for key in (getattr(s, name_attr, None), name_str):
            if key is None:
                continue
            try:
                s.set(key, True)
                return
            except Exception:
                continue

    _set("USE_WORLD_COORDS", "use-world-coords")
    _set("WELD_VERTICES", "weld-vertices")
    return s


class IFCReader:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.ifc_file = None
        self.settings = None

    def load(self) -> bool:
        try:
            self.ifc_file = ifcopenshell.open(self.filepath)
            self.settings = _make_settings()
            logger.info("Loaded IFC: %s", self.filepath)
            return True
        except Exception as e:  # pragma: no cover
            logger.error("Failed to load IFC: %s", e)
            return False

    def by(self, t: str) -> List:
        return self.ifc_file.by_type(t) if self.ifc_file else []

    def get_buildings(self) -> List:
        return self.by("IfcBuilding")

    def get_spaces(self) -> List:
        return self.by("IfcSpace")

    # Footprint-defining / context elements
    SHELL_TYPES = ("IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcRoof",
                   "IfcColumn", "IfcBeam", "IfcStair")

    def get_shell_elements(self) -> List:
        out = []
        for t in self.SHELL_TYPES:
            out.extend(self.by(t))
        return out


# ---------------------------------------------------------------------------
# Geometry extraction
# ---------------------------------------------------------------------------

@dataclass
class RawMesh:
    vertices: List[Tuple[float, float, float]]   # IFC world metres
    faces: List[Tuple[int, int, int]]


def _extract_mesh(reader: IFCReader, entity) -> Optional[RawMesh]:
    try:
        shape = ifcopenshell.geom.create_shape(reader.settings, entity)
    except Exception:
        return None
    geom = getattr(shape, "geometry", None)
    if geom is None:
        return None
    verts = list(geom.verts)
    faces = list(geom.faces)
    if not verts or not faces:
        return None
    vertices = [(verts[i], verts[i + 1], verts[i + 2]) for i in range(0, len(verts), 3)]
    tris = [(faces[i], faces[i + 1], faces[i + 2]) for i in range(0, len(faces), 3)]
    return RawMesh(vertices=vertices, faces=tris)


class SemanticMapper:
    VERT = 0.15
    HORIZ = 0.7

    @staticmethod
    def _normal_z(v0, v1, v2) -> float:
        ux, uy, uz = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
        vx, vy, vz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
        nz = ux * vy - uy * vx
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        L = math.sqrt(nx * nx + ny * ny + nz * nz)
        return nz / L if L else 0.0

    def classify(self, entity, nz: float) -> str:
        t = entity.is_a()
        if t == "IfcWindow":
            return "Window"
        if t == "IfcDoor":
            return "Door"
        is_vert = -self.VERT <= nz <= self.VERT
        up = nz > self.HORIZ
        down = nz < -self.HORIZ
        if t in ("IfcWall", "IfcWallStandardCase"):
            return "WallSurface"
        if t == "IfcRoof":
            return "CeilingSurface" if down else "RoofSurface"
        if t == "IfcSlab":
            if getattr(entity, "PredefinedType", None) == "ROOF":
                return "RoofSurface"
            if up:
                return "FloorSurface"
            if down:
                return "CeilingSurface"
            return "WallSurface"
        if t == "IfcSpace":
            if down:
                return "FloorSurface"
            if up:
                return "CeilingSurface"
            return "InteriorWallSurface"
        if is_vert:
            return "WallSurface"
        if up:
            return "RoofSurface"
        if down:
            return "GroundSurface"
        return "WallSurface"


def _extract_attributes(entity) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {}
    for a in ("Name", "Description", "GlobalId", "LongName"):
        v = getattr(entity, a, None)
        if v:
            attrs[a.lower()] = v
    # property sets
    psets: Dict[str, Any] = {}
    try:
        for rel in (getattr(entity, "IsDefinedBy", None) or []):
            if rel.is_a("IfcRelDefinesByProperties"):
                ps = rel.RelatingPropertyDefinition
                if ps.is_a("IfcPropertySet"):
                    props = {}
                    for p in ps.HasProperties:
                        if p.is_a("IfcPropertySingleValue") and p.NominalValue:
                            props[p.Name] = p.NominalValue.wrappedValue
                    if props:
                        psets[ps.Name] = props
    except Exception:
        pass
    if psets:
        attrs["property_sets"] = psets
    return attrs


class StoreyResolver:
    """Resolve which storey a space belongs to.

    Strategy, in order:
      1. Explicit IFC links: space.Decomposes (IfcRelAggregates) -> storey,
         then space.ContainedInStructure -> storey.
      2. Elevation fallback (common in sparse IFCs that omit space->storey rels):
         pick the highest storey whose elevation (in metres) is at or below the
         space's floor Z. Storey ``Elevation`` is in the file's length unit, so
         it is converted to metres via the project unit scale.
    """

    def __init__(self, reader: "IFCReader"):
        self.unit_scale = 1.0
        if _ifc_unit is not None and reader.ifc_file is not None:
            try:
                self.unit_scale = float(_ifc_unit.calculate_unit_scale(reader.ifc_file))
            except Exception:
                self.unit_scale = 1.0
        # storeys sorted by elevation (metres), ascending
        storeys = []
        for s in reader.by("IfcBuildingStorey"):
            elev_m = (float(getattr(s, "Elevation", 0) or 0.0)) * self.unit_scale
            storeys.append((elev_m, s.Name or "Storey"))
        self.storeys = sorted(storeys, key=lambda t: t[0])

    @staticmethod
    def _explicit(space) -> Optional[str]:
        try:
            for rel in (getattr(space, "Decomposes", None) or []):
                parent = rel.RelatingObject
                if parent.is_a("IfcBuildingStorey"):
                    return parent.Name
        except Exception:
            pass
        try:
            for rel in (getattr(space, "ContainedInStructure", None) or []):
                s = rel.RelatingStructure
                if s.is_a("IfcBuildingStorey"):
                    return s.Name
        except Exception:
            pass
        return None

    def resolve(self, space, mesh_min_z_m: Optional[float]) -> Optional[str]:
        name = self._explicit(space)
        if name:
            return name
        if not self.storeys or mesh_min_z_m is None:
            return self.storeys[0][1] if self.storeys else None
        # highest storey at/below the space floor (small tolerance for slab thickness)
        tol = 0.5
        chosen = self.storeys[0][1]
        for elev_m, sname in self.storeys:
            if mesh_min_z_m + tol >= elev_m:
                chosen = sname
            else:
                break
        return chosen


# ---------------------------------------------------------------------------
# Footprint extraction
# ---------------------------------------------------------------------------

class FootprintExtractor:
    """Union the 2D projection of the building shell into an outer footprint."""

    def __init__(self, reader: IFCReader, transformer: Transformer):
        self.reader = reader
        self.tf = transformer

    def extract(self) -> Tuple[Optional[Any], Optional[str]]:
        if not SHAPELY_AVAILABLE:
            logger.warning("shapely not installed — skipping footprint extraction.")
            return None, None

        elements = self.reader.get_shell_elements()
        if not elements:
            elements = self.reader.get_spaces()

        tris_2d: List[Polygon] = []
        for el in elements:
            mesh = _extract_mesh(self.reader, el)
            if not mesh:
                continue
            # project to geographic lon/lat, keep only XY
            pts = [self.tf.to_lonlat(*v)[:2] for v in mesh.vertices]
            for (a, b, c) in mesh.faces:
                try:
                    tri = Polygon([pts[a], pts[b], pts[c]])
                    if tri.is_valid and tri.area > 0:
                        tris_2d.append(tri)
                except Exception:
                    continue

        if not tris_2d:
            return None, None

        try:
            merged = unary_union([t.buffer(0) for t in tris_2d])
        except Exception:
            merged = unary_union(tris_2d)

        outer = self._largest_valid_polygon(merged)
        if outer is None or outer.is_empty:
            return None, None

        # Drop interior holes (cadastral footprint = outer building outline),
        # then re-clean: reconstructing from the exterior ring can introduce a
        # self-intersection, so buffer(0) and re-pick the largest valid polygon.
        if outer.interiors:
            outer = self._largest_valid_polygon(Polygon(outer.exterior))
            if outer is None or outer.is_empty:
                return None, None

        # Light simplify (~1e-6 deg ≈ 0.1 m), then a final validity clean so the
        # WKT is always accepted by PostGIS / GEOS (GEOSGeometry, ST_*).
        simplified = outer.simplify(1e-6, preserve_topology=True)
        cleaned = self._largest_valid_polygon(simplified) or outer
        return cleaned, cleaned.wkt

    @staticmethod
    def _largest_valid_polygon(geom):
        """Return the largest OGC-valid Polygon from a (possibly invalid/multi)
        geometry, robust across GEOS versions.

        Order: grid-snap (set_precision) → make_valid → buffer(0) fallback.
        set_precision performs GEOS precision reduction, which eliminates the
        near-degenerate self-intersections that one GEOS build tolerates and
        another flags — so the emitted WKT validates in the DB's GEOS too.
        """
        if geom is None or geom.is_empty:
            return None

        # 1. snap to a small grid to kill micro self-touches deterministically
        if _shp_set_precision is not None:
            try:
                snapped = _shp_set_precision(geom, _FOOTPRINT_GRID_DEG)
                if snapped is not None and not snapped.is_empty:
                    geom = snapped
            except Exception:
                pass

        # 2. repair if still invalid: make_valid (preferred) then buffer(0)
        if not geom.is_valid:
            repaired = None
            if _shp_make_valid is not None:
                try:
                    repaired = _shp_make_valid(geom)
                except Exception:
                    repaired = None
            if repaired is None or repaired.is_empty or not repaired.is_valid:
                try:
                    repaired = geom.buffer(0)
                except Exception:
                    repaired = None
            if repaired is not None and not repaired.is_empty:
                geom = repaired

        if geom.is_empty:
            return None

        # 3. reduce to a single Polygon (largest part)
        if isinstance(geom, Polygon):
            return geom
        polys = [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon) and not g.is_empty]
        return max(polys, key=lambda g: g.area) if polys else None


# ---------------------------------------------------------------------------
# CityJSON building + per-unit solids
# ---------------------------------------------------------------------------

class CityJSONBuilder:
    """Assembles CityJSON 2.0 with vertices in a local metric ENU frame."""

    def __init__(self, transformer: Transformer, precision: int = 3):
        self.tf = transformer
        self.precision = precision
        self.city_objects: Dict[str, Any] = {}
        self.vertices: List[List[float]] = []
        self._vmap: Dict[Tuple[float, float, float], int] = {}

    def _add_vertex_enu(self, x: float, y: float, z: float) -> int:
        ex, ny, ez = self.tf.to_enu(x, y, z)
        key = (round(ex, self.precision), round(ny, self.precision), round(ez, self.precision))
        idx = self._vmap.get(key)
        if idx is None:
            idx = len(self.vertices)
            self.vertices.append([key[0], key[1], key[2]])
            self._vmap[key] = idx
        return idx

    def add_building(self, bid: str, attrs: Dict[str, Any], children: List[str]):
        self.city_objects[bid] = {
            "type": "Building",
            "attributes": attrs,
            "children": children,
            "geometry": [],
        }

    def add_room(self, rid: str, building_id: str, mesh: RawMesh,
                 entity, attrs: Dict[str, Any], mapper: SemanticMapper):
        boundaries = []
        semantics_values = []
        surfaces: List[Dict[str, str]] = []
        surf_index: Dict[str, int] = {}

        for (a, b, c) in mesh.faces:
            i0 = self._add_vertex_enu(*mesh.vertices[a])
            i1 = self._add_vertex_enu(*mesh.vertices[b])
            i2 = self._add_vertex_enu(*mesh.vertices[c])
            boundaries.append([[i0, i1, i2]])
            nz = mapper._normal_z(mesh.vertices[a], mesh.vertices[b], mesh.vertices[c])
            stype = mapper.classify(entity, nz)
            if stype not in surf_index:
                surf_index[stype] = len(surfaces)
                surfaces.append({"type": stype})
            semantics_values.append(surf_index[stype])

        geom = {
            "type": "MultiSurface",
            "lod": "2.2",
            "boundaries": boundaries,
            "semantics": {"surfaces": surfaces, "values": semantics_values},
        }
        self.city_objects[rid] = {
            "type": "BuildingRoom",
            "attributes": attrs,
            "parents": [building_id],
            "geometry": [geom],
        }

    def to_dict(self, transform_params: TransformParams) -> Dict[str, Any]:
        return {
            "type": "CityJSON",
            "version": "2.0",
            "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
            "metadata": {
                "datasetTitle": "InfoBhoomi IFC Cadastral Export",
                "referenceSystem": "local-ENU-metres",
                "georeferencing": transform_params.as_metadata(),
            },
            "CityObjects": self.city_objects,
            "vertices": self.vertices,
        }


def _room_solid_wkt_4326(mesh: RawMesh, tf: Transformer) -> Optional[str]:
    """Build a MULTIPOLYGON Z (lon lat z) WKT from a room mesh — for geom_3d."""
    rings = []
    for (a, b, c) in mesh.faces:
        p0 = tf.to_lonlat(*mesh.vertices[a])
        p1 = tf.to_lonlat(*mesh.vertices[b])
        p2 = tf.to_lonlat(*mesh.vertices[c])
        ring = f"({p0[0]} {p0[1]} {p0[2]}, {p1[0]} {p1[1]} {p1[2]}, " \
               f"{p2[0]} {p2[1]} {p2[2]}, {p0[0]} {p0[1]} {p0[2]})"
        rings.append(f"({ring})")
    if not rings:
        return None
    return "MULTIPOLYGON Z (" + ", ".join(rings) + ")"


def _polygon_area_m2(mesh: RawMesh) -> Optional[float]:
    """Approx floor area = sum of |XY| of downward/upward-ish faces / 2 — but
    simpler: use the 2D footprint area of the room in local metres."""
    if not SHAPELY_AVAILABLE:
        return None
    tris = []
    for (a, b, c) in mesh.faces:
        va, vb, vc = mesh.vertices[a], mesh.vertices[b], mesh.vertices[c]
        try:
            tri = Polygon([(va[0], va[1]), (vb[0], vb[1]), (vc[0], vc[1])])
            if tri.is_valid and tri.area > 0:
                tris.append(tri.buffer(0))
        except Exception:
            continue
    if not tris:
        return None
    merged = unary_union(tris)
    return round(merged.area, 2)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def process_ifc(ifc_path: str, transform: Optional[TransformParams] = None) -> ConversionResult:
    """Full pipeline: IFC → (CityJSON, footprint 4326, per-unit solids 4326)."""
    transform = transform or TransformParams()
    tf = Transformer(transform)

    reader = IFCReader(ifc_path)
    if not reader.load():
        raise RuntimeError(f"Could not open IFC: {ifc_path}")

    buildings = reader.get_buildings()
    if not buildings:
        raise RuntimeError("No IfcBuilding found.")
    building = buildings[0]
    bid = building.GlobalId.replace("-", "_")

    mapper = SemanticMapper()
    builder = CityJSONBuilder(tf)
    storeys = StoreyResolver(reader)
    stats = {"explicit": 0, "fallback": 0, "failed": 0}
    units: List[UnitResult] = []
    children: List[str] = []

    spaces = reader.get_spaces()
    logger.info("Found %d building(s), %d space(s)", len(buildings), len(spaces))

    for sp in spaces:
        sid = sp.GlobalId.replace("-", "_")
        mesh = _extract_mesh(reader, sp)
        if not mesh:
            stats["failed"] += 1
            logger.warning("No geometry for space %s", getattr(sp, "Name", sid))
            continue

        attrs = _extract_attributes(sp)
        mesh_min_z = min((v[2] for v in mesh.vertices), default=None)
        storey = storeys.resolve(sp, mesh_min_z)
        if storey:
            attrs["floor"] = storey
        area = _polygon_area_m2(mesh)
        if area is not None:
            attrs["area_m2"] = area
        attrs["geometry_source"] = "ifc_shape"

        builder.add_room(sid, bid, mesh, sp, attrs, mapper)
        children.append(sid)
        units.append(UnitResult(
            guid=sp.GlobalId, name=attrs.get("name", sid), cityjson_id=sid,
            floor=storey, area_m2=area,
            solid_wkt_4326=_room_solid_wkt_4326(mesh, tf),
            is_fallback=False, attributes=attrs,
        ))
        stats["explicit"] += 1

    b_attrs = _extract_attributes(building)
    builder.add_building(bid, b_attrs, children)

    # Footprint
    footprint, footprint_wkt = FootprintExtractor(reader, tf).extract()

    cityjson = builder.to_dict(transform)
    return ConversionResult(
        cityjson=cityjson,
        footprint=footprint,
        footprint_wkt_4326=footprint_wkt,
        units=units,
        building_guid=building.GlobalId,
        building_name=b_attrs.get("name"),
        stats=stats,
    )


def convert_ifc_to_cityjson(ifc_path: str, transform: Optional[TransformParams] = None) -> Dict[str, Any]:
    return process_ifc(ifc_path, transform).cityjson


def extract_footprint(ifc_path: str, transform: Optional[TransformParams] = None):
    return process_ifc(ifc_path, transform).footprint


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    ap = argparse.ArgumentParser(description="IFC → CityJSON cadastral converter")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--lon", type=float, default=0.0, help="anchor longitude (EPSG:4326)")
    ap.add_argument("--lat", type=float, default=0.0, help="anchor latitude (EPSG:4326)")
    ap.add_argument("--base-z", type=float, default=0.0)
    ap.add_argument("--rotation", type=float, default=0.0, help="CCW degrees")
    ap.add_argument("--scale", type=float, default=1.0)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if not os.path.exists(args.input):
        logger.error("Input not found: %s", args.input)
        sys.exit(1)

    tp = TransformParams(anchor_lon=args.lon, anchor_lat=args.lat,
                         base_z=args.base_z, rotation_deg=args.rotation, scale=args.scale)
    result = process_ifc(args.input, tp)

    with open(args.output, "w") as f:
        json.dump(result.cityjson, f, indent=2)

    logger.info("=" * 60)
    logger.info("CityJSON : %s", args.output)
    logger.info("Building : %s (%s)", result.building_name, result.building_guid)
    logger.info("Units    : %d explicit, %d fallback, %d failed",
                result.stats["explicit"], result.stats["fallback"], result.stats["failed"])
    logger.info("Vertices : %d", len(result.cityjson["vertices"]))
    logger.info("Footprint: %s", "yes" if result.footprint else "NONE")
    if result.footprint is not None:
        logger.info("  area(deg^2)=%.3e  bounds=%s", result.footprint.area, result.footprint.bounds)
    logger.info("=" * 60)


if __name__ == "__main__":
    _main()
