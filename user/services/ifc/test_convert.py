"""
P1 golden / smoke test for the cadastral converter.

Run with a Python that has ifcopenshell + shapely installed:
    python user/services/ifc/test_convert.py [path/to/LargeBuilding.ifc]

Asserts the contract the import endpoint relies on:
  * Building + per-space BuildingRoom hierarchy
  * semantic surfaces present
  * floor/area attributes extracted
  * footprint = valid 2D Polygon in EPSG:4326 of plausible size
  * each unit solid = parseable 3D MULTIPOLYGON Z (lon/lat/z) for geom_3d
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ifc2cityjson_cadastral import process_ifc, TransformParams  # noqa: E402

DEFAULT_IFC = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..",
    "3D-Cadastre", "IFC", "LargeBuilding.ifc",
)
ANCHOR_LON, ANCHOR_LAT = 79.861, 6.921


def main(ifc_path: str) -> int:
    from shapely import wkt as W

    r = process_ifc(ifc_path, TransformParams(anchor_lon=ANCHOR_LON, anchor_lat=ANCHOR_LAT))
    co = r.cityjson["CityObjects"]
    buildings = [v for v in co.values() if v["type"] == "Building"]
    rooms = [v for v in co.values() if v["type"] == "BuildingRoom"]

    checks = []

    def check(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    check("1 Building object", len(buildings) == 1, f"got {len(buildings)}")
    check("8 BuildingRoom units", len(rooms) == 8, f"got {len(rooms)}")
    check("building has all children", bool(buildings) and len(buildings[0]["children"]) == len(rooms))
    check("stats: 8 explicit, 0 failed",
          r.stats.get("explicit") == 8 and r.stats.get("failed") == 0, str(r.stats))

    sem_ok = all("semantics" in v["geometry"][0] for v in rooms)
    check("every room has semantic surfaces", sem_ok)

    # In LargeBuilding.ifc, IfcRelAggregates puts all 8 IfcSpaces on "Level 1"
    # (Level 2 exists as a storey but contains no spaces). So the truthful
    # expectation is: every unit resolves to a storey, and it matches the
    # explicit IFC aggregation.
    floors = sorted({u.floor for u in r.units if u.floor})
    check("every unit has a resolved storey", all(u.floor for u in r.units), str(floors))
    check("storey matches IFC aggregation (Level 1)", floors == ["Level 1"], str(floors))
    check("areas extracted", all(u.area_m2 for u in r.units))

    fp = r.footprint
    check("footprint present & valid", fp is not None and fp.is_valid)
    check("footprint is 2D", fp is not None and not fp.has_z)
    if fp is not None:
        minx, miny, maxx, maxy = fp.bounds
        w = (maxx - minx) * 111320 * math.cos(math.radians(ANCHOR_LAT))
        h = (maxy - miny) * 110574
        check("footprint plausible size (3-100 m)", 3 < w < 100 and 3 < h < 100,
              f"{w:.1f}m x {h:.1f}m")

    solids_ok = 0
    for u in r.units:
        if not u.solid_wkt_4326:
            continue
        g = W.loads(u.solid_wkt_4326)
        if g.geom_type == "MultiPolygon" and g.has_z:
            solids_ok += 1
    check("all unit solids parse as 3D MultiPolygon", solids_ok == len(r.units),
          f"{solids_ok}/{len(r.units)}")

    print("=" * 64)
    passed = 0
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f"  ({detail})" if detail else ""))
        passed += ok
    print("=" * 64)
    print(f"{passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IFC
    sys.exit(main(path))
