from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView, RetrieveUpdateAPIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import check_password
from django.db.models import Q, Min, Subquery, OuterRef
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.timezone import now
from django.utils import timezone
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.functions import Area, Intersection as GeoIntersection

import json, os
from datetime import timedelta

from ..models import *
from ..serializers import *
from ..constant import *
from ..tests import *

User = get_user_model()

#________________________________________________ Lst_gnd View (for Admin Info drop down) _______________________________________
class Lst_gnd_10m_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:
            user = request.user

            orgID = user.org_id

            gnd_ids_from_org = Org_Area_Model.objects.filter(org_id=orgID).values_list('org_area', flat=True)
            gnd_ids = [gnd_id for sublist in gnd_ids_from_org for gnd_id in sublist]

            list_data = sl_gnd_10m_Model.objects.filter(gid__in=gnd_ids).values('gid', 'gnd')

            return Response(list(list_data))

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#==========================================================================================================================================



#________________________________________________ TESTING _______________________________________________________________________

class TestJsonView(ListCreateAPIView):

    queryset = TestJsonModel.objects.all()
    serializer_class = TestJsonSerializer
    pagination_class = PageNumberPagination


class Test_Data_MyLayerIDs_View(APIView):
    http_method_names = ['post']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        # Retrieve username from request data
        userID = request.data.get("user_id")
        if not userID:
            return Response({"detail": "user_id is required."}, status=400)

        # Filter LayersModel to get relevant layer_ids
        my_layerIDs = LayersModel.objects.filter(group_name__contains=[userID]).values_list('layer_id', flat=True)

        return Response(my_layerIDs, status=200)


class Temp_Import_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Temp_Import_Model.objects.filter(layer_id=1)
    serializer_class = Temp_Import_Serializer


#________________________________________________ CityJson View _________________________________________________________________
class CityJSON_Model_ListCreate(generics.ListCreateAPIView):
    serializer_class = CityJSON_Serializer

    def get_queryset(self):
        qs = CityJSON_Model.objects.all().order_by('-id')
        su_id = self.request.query_params.get('su_id')
        if su_id:
            qs = qs.filter(su_id=su_id)
        return qs

#------------------------------------------------------------------------------
class CityJSON_Model_Retrieve(generics.RetrieveAPIView):
    queryset = CityJSON_Model.objects.all()
    serializer_class = CityJSON_Serializer

#------------------------------------------------------------------------------
class CityJSON_Upload(generics.CreateAPIView):
    serializer_class = CityJSON_Serializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Extract CityObjects after saving the CityJSONModel
        city_objects_count = self.extract_city_objects(serializer.instance.cityjson_data)

        return Response({
            "message": "CityJSON data uploaded successfully",
            "cityjson_id": serializer.instance.id,
            "city_objects_count": city_objects_count
        }, status=status.HTTP_201_CREATED)

    def extract_city_objects(self, cityjson_data):
        try:
            city_objects = cityjson_data.get('CityObjects', {})
            bulk_objects = []

            for city_object_id, data in city_objects.items():
                bulk_objects.append(City_Object_Model(
                    city_object_id=city_object_id,
                    type=data.get('type'),
                    attributes=data.get('attributes'),
                    parents=data.get('parents'),
                    children=data.get('children'),
                    geometry=data.get('geometry'),
                ))

            # Bulk insert to optimize performance
            with transaction.atomic():
                City_Object_Model.objects.bulk_create(bulk_objects, ignore_conflicts=True)

            return len(bulk_objects)

        except Exception as e:
            print(f"Error extracting CityObjects: {e}")
            return 0  # Return 0 if extraction fails

#------------------------------------------------------------------------------
class City_Object_List(generics.ListAPIView):
    queryset = City_Object_Model.objects.all()
    serializer_class = City_Object_Serializer

#------------------------------------------------------------------------------
class City_Object_Retrieve(generics.RetrieveAPIView):
    queryset = City_Object_Model.objects.all()
    serializer_class = City_Object_Serializer


# =============================================================================
#  IFC / CityJSON 3D Cadastre Import  (P2)
# =============================================================================
#  POST /api/user/cityjson/import/   (multipart)
#    file          : .ifc | .json (CityJSON)            (required)
#    parent_su_id  : survey_rep.id of the target parcel (required)
#    anchor_lon    : float  (default = parcel centroid lon)
#    anchor_lat    : float  (default = parcel centroid lat)
#    rotation_deg  : float  (default 0)   CCW about vertical
#    scale         : float  (default 1)
#    base_z        : float  (default 0)
#
#  Pipeline (single transaction):
#    1. Convert IFC -> CityJSON (+ footprint 4326 + per-unit MULTIPOLYGON Z solids)
#       using user.services.ifc.process_ifc  (manual georeferencing transform).
#    2. Create a building survey_rep (layer_id=3) child of the parcel, geom=footprint.
#    3. Store the CityJSON in city_json keyed by the building su_id.
#    4. Create each room as a layer_id=12 child unit (parent_id=[building]) with
#       la_ls_build_unit.geom_3d = the room solid (SRID 4326).
#
#  Heavy deps (ifcopenshell, shapely) are imported lazily so this module still
#  loads on a server that hasn't installed them yet.
# =============================================================================
import re as _re
import tempfile as _tempfile

from rest_framework.parsers import MultiPartParser, FormParser


def _parse_floor_no(storey_name):
    if not storey_name:
        return None
    m = _re.search(r'(\d+)', str(storey_name))
    return int(m.group(1)) if m else None


class IFC_Cadastre_Import_View(APIView):
    """Import an IFC/CityJSON building onto a parcel and create LADM records."""
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not _has_3d_perm(request.user, PERM_3D_IMPORT, "add"):
            return _perm_denied("import 3D objects")

        upload = request.FILES.get('file')
        if not upload:
            return Response({"error": "No file provided (field 'file')."},
                            status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in ('.ifc', '.json'):
            return Response({"error": "File must be .ifc or .json (CityJSON)."},
                            status=status.HTTP_400_BAD_REQUEST)

        parent_su_id = request.data.get('parent_su_id') or request.data.get('su_id')
        try:
            parent_su_id = int(parent_su_id)
        except (TypeError, ValueError):
            return Response({"error": "parent_su_id (int) is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        parcel = Survey_Rep_DATA_Model.objects.filter(id=parent_su_id).first()
        if not parcel:
            return Response({"error": f"Parcel survey_rep id={parent_su_id} not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if parcel.geom is None:
            return Response({"error": "Target parcel has no geometry."},
                            status=status.HTTP_400_BAD_REQUEST)

        # anchor defaults to the parcel centroid (SRID 4326 -> lon/lat)
        try:
            centroid = parcel.geom.centroid
            default_lon, default_lat = float(centroid.x), float(centroid.y)
        except Exception:
            default_lon = default_lat = 0.0

        def _f(key, default):
            v = request.data.get(key)
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        anchor_lon = _f('anchor_lon', default_lon)
        anchor_lat = _f('anchor_lat', default_lat)
        rotation_deg = _f('rotation_deg', 0.0)
        scale = _f('scale', 1.0)
        base_z = _f('base_z', 0.0)

        # Optional multi-anchor georeferencing (Part A): a JSON list of
        # { "local": [x,y,z], "lon": <deg>, "lat": <deg> } pairs. When >=2 are
        # given, the similarity transform (rotation+scale+translation) is solved
        # from them and overrides the single-anchor/rotation inputs.
        anchor_pairs = request.data.get('anchor_pairs')
        if isinstance(anchor_pairs, str):
            try:
                anchor_pairs = json.loads(anchor_pairs)
            except Exception:
                anchor_pairs = None

        # write upload to a temp file
        suffix = ext
        tmp_path = None
        try:
            with _tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in upload.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
        except Exception as e:
            return Response({"error": f"Could not buffer upload: {e}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # ---- run the converter (lazy import of heavy deps) ----
            try:
                from ..services.ifc import process_ifc, TransformParams
            except Exception as e:
                return Response(
                    {"error": "3D conversion is unavailable on this server "
                              "(ifcopenshell/shapely not installed).",
                     "detail": str(e)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)

            from django.contrib.gis.geos import GEOSGeometry

            # ── Guard against lon/lat being entered in the wrong columns ──────────
            # Every import targets a parcel with a known location, so each anchor's
            # geographic point must sit near that parcel. If the entered (lon, lat)
            # is far from the parcel but the swapped (lat, lon) is close, the values
            # were reversed at entry — auto-correct and report it instead of writing
            # the building to the wrong hemisphere.
            anchor_warning = None

            def _closer_orientation(lon, lat):
                """Return ((lon, lat), swapped_bool) choosing whichever orientation
                is nearer the parcel centroid (default_lon/default_lat)."""
                d_normal = (lon - default_lon) ** 2 + (lat - default_lat) ** 2
                d_swap = (lat - default_lon) ** 2 + (lon - default_lat) ** 2
                # Only swap when latitude is out of range, or swapping is dramatically
                # closer (avoids flipping legitimately-near points by tiny margins).
                if abs(lat) > 90 or (d_swap * 100 < d_normal and d_normal > 1.0):
                    return (lat, lon), True
                return (lon, lat), False

            if isinstance(anchor_pairs, (list, tuple)) and len(anchor_pairs) >= 2:
                swapped_any = False
                for p in anchor_pairs:
                    try:
                        (p["lon"], p["lat"]), sw = _closer_orientation(
                            float(p["lon"]), float(p["lat"]))
                        swapped_any = swapped_any or sw
                    except (KeyError, TypeError, ValueError):
                        continue
                if swapped_any:
                    anchor_warning = ("Anchor longitude/latitude looked reversed "
                                      "(far from the target parcel) and were auto-corrected.")
                try:
                    tp = TransformParams.from_anchor_pairs(anchor_pairs, base_z=base_z)
                except Exception as e:
                    return Response(
                        {"error": f"Could not solve transform from anchor_pairs: {e}"},
                        status=status.HTTP_400_BAD_REQUEST)
            else:
                (anchor_lon, anchor_lat), sw = _closer_orientation(anchor_lon, anchor_lat)
                if sw:
                    anchor_warning = ("Anchor longitude/latitude looked reversed "
                                      "(far from the target parcel) and were auto-corrected.")
                tp = TransformParams(
                    anchor_lon=anchor_lon, anchor_lat=anchor_lat, base_z=base_z,
                    rotation_deg=rotation_deg, scale=scale,
                )

            if ext == '.ifc':
                try:
                    result = process_ifc(tmp_path, tp)
                except Exception as e:
                    return Response({"error": f"IFC conversion failed: {e}"},
                                    status=status.HTTP_400_BAD_REQUEST)
                cityjson = result.cityjson
                footprint_wkt = result.footprint_wkt_4326
                units = result.units
                building_name = result.building_name or upload.name
            else:
                # CityJSON direct upload: store as-is, no auto footprint/units (P5).
                try:
                    with open(tmp_path, 'r', encoding='utf-8') as _cjf:
                        cityjson = json.load(_cjf)
                except Exception as e:
                    return Response({"error": f"Invalid CityJSON: {e}"},
                                    status=status.HTTP_400_BAD_REQUEST)
                footprint_wkt = None
                units = []
                building_name = upload.name

            if ext == '.ifc' and not footprint_wkt:
                return Response(
                    {"error": "Could not extract a building footprint from the IFC."},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # ---- persist (one transaction) ----
            with transaction.atomic():
                building_geom = (GEOSGeometry(footprint_wkt, srid=4326)
                                 if footprint_wkt else parcel.geom)

                building = Survey_Rep_DATA_Model(
                    layer_id=3,
                    parent_id=[parent_su_id],
                    gnd_id=parcel.gnd_id,
                    org_id=parcel.org_id,
                    geom=building_geom,
                    geom_type=building_geom.geom_type,
                    user_id=request.user.id,
                    dimension_2d_3d='3D',
                    reference_coordinate='EPSG:4326',
                    status=True,
                )
                building.save()
                building_su_id = building.id

                LA_Spatial_Unit_Model.objects.get_or_create(
                    su_id=building_su_id,
                    defaults={"status": True, "label": building_name,
                              "parcel_status": "Active"},
                )
                LA_LS_Build_Unit_Model.objects.get_or_create(
                    su_id_id=building_su_id,
                    defaults={"building_name": building_name,
                              "no_floors": None, "status": True},
                )

                cj_row = CityJSON_Model.objects.create(
                    cityjson_data=cityjson,
                    su_id=building_su_id,
                    name=building_name,
                    source_file=upload.name,
                )

                units_created = 0
                for u in units:
                    unit_survey = Survey_Rep_DATA_Model(
                        layer_id=12,
                        parent_id=[building_su_id],
                        gnd_id=parcel.gnd_id,
                        org_id=parcel.org_id,
                        geom=building_geom,          # 2D placeholder = building outline
                        geom_type=building_geom.geom_type,
                        user_id=request.user.id,
                        dimension_2d_3d='3D',
                        reference_coordinate='EPSG:4326',
                        status=True,
                    )
                    unit_survey.save()
                    unit_su_id = unit_survey.id

                    LA_Spatial_Unit_Model.objects.get_or_create(
                        su_id=unit_su_id,
                        defaults={"status": True, "label": u.name,
                                  "parcel_status": "Active"},
                    )

                    geom_3d = None
                    if u.solid_wkt_4326:
                        try:
                            geom_3d = GEOSGeometry(u.solid_wkt_4326, srid=4326)
                        except Exception:
                            geom_3d = None

                    LA_LS_Build_Unit_Model.objects.create(
                        su_id_id=unit_su_id,
                        apt_name=u.name,
                        floor_no=_parse_floor_no(u.floor),
                        floor_area=u.area_m2,
                        geom_3d=geom_3d,
                        building_unit_type="UNASSIGNED",
                        component_units=[u.cityjson_id],
                        status=True,
                    )
                    units_created += 1

            return Response({
                "detail": "Import successful.",
                "building_su_id": building_su_id,
                "cityjson_id": cj_row.id,
                "footprint_created": bool(footprint_wkt),
                "units_created": units_created,
                "georeferencing": tp.as_metadata(),  # incl. method + fit_rms_m for anchor_pairs
                "warning": anchor_warning,
            }, status=status.HTTP_201_CREATED)

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass


def upload_to_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# =============================================================================
#  P4 — City 3D feed (admin-area filtered) + cadastral search
# =============================================================================
#
#  A user's administrative area is org-based: Org_Area_Model.org_area is an
#  ArrayField of GND ids for the user's org_id, matched against
#  survey_rep.gnd_id.  Both endpoints below are scoped to that area so the
#  city-3D view and search only ever return buildings the user may see.
# =============================================================================

def _user_gnd_ids(user):
    """Return the list of GND ids in the user's organisation's area."""
    org_id = getattr(user, 'org_id', None)
    if org_id is None:
        return []
    nested = Org_Area_Model.objects.filter(org_id=org_id).values_list('org_area', flat=True)
    gnd_ids = []
    for sub in nested:
        if sub:
            gnd_ids.extend(sub)
    return gnd_ids


# --- 3D Cadastre permission ids (seeded by migration 0016) -------------------
PERM_3D_IMPORT       = 254   # add
PERM_3D_DELETE       = 255   # delete
PERM_3D_VIEW         = 256   # view (single building)
PERM_3D_CITY_VIEW    = 257   # view (city / admin area)
PERM_3D_SEARCH       = 258   # view (search)
PERM_3D_COMPOSE_OPEN = 259   # view (open composition picker)
PERM_3D_COMPOSE      = 260   # add/edit (create LSBU)


def _has_3d_perm(user, permission_id, action="view"):
    """True if the user's role has `action` (view/add/edit/delete) on the given
    3D-cadastre permission. Mirrors building.py's Role_Permission gate. Fails
    OPEN if the user simply has no role rows yet (so existing installs that
    haven't configured the new perms keep working) — but once a role exists,
    the explicit grant is required."""
    role_ids = list(
        User_Roles_Model.objects.filter(users__contains=[user.id])
        .values_list("role_id", flat=True)
    )
    if not role_ids:
        return True  # no RBAC configured for this user → don't hard-block
    # granted if ANY of the user's roles carries the action on this permission
    return Role_Permission_Model.objects.filter(
        role_id__in=role_ids, permission_id=permission_id, **{action: True},
    ).exists()


def _perm_denied(name):
    return Response(
        {"error": f"You do not have permission to {name}."},
        status=status.HTTP_403_FORBIDDEN,
    )


class City3D_AdminArea_View(APIView):
    """GET /api/user/cityjson/admin-area/

    List every imported 3D building (layer_id=3 survey_rep that has a stored
    CityJSON) whose gnd_id falls within the login user's organisation area.
    Returns lightweight rows (NO cityjson payload) for the city-3D index;
    the viewer fetches each building's model via /cityjson/?su_id=.

    Optional ``?parcel_su_id=<int>`` restricts the result to buildings that sit
    on that parcel (parent_id contains it) — the "View as 3D" parcel-focused
    mode. When given, the parcel's own 2D geometry (GeoJSON, 4326) is returned
    as ``parcel`` so the viewer can lay the reused parcel fabric as a ground
    plane (no IFC-derived shell needed — cadastral context is reused).
    """
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # parcel-focused single-building view vs whole-city view
            _pf = request.query_params.get('parcel_su_id')
            if not _has_3d_perm(request.user,
                                PERM_3D_VIEW if _pf else PERM_3D_CITY_VIEW, "view"):
                return _perm_denied("view 3D buildings")
            gnd_ids = _user_gnd_ids(request.user)
            if not gnd_ids:
                return Response({"count": 0, "buildings": [], "parcel": None},
                                status=status.HTTP_200_OK)

            # buildings (layer_id=3) inside the user's area
            # NOTE: survey_rep.status is varchar in the DB despite the model's
            # BooleanField — do not filter on it (matches Bld_Units_List_View).
            buildings = (Survey_Rep_DATA_Model.objects
                         .filter(layer_id=3, gnd_id__in=gnd_ids)
                         .order_by('-id'))

            # parcel-focused mode: only buildings on this parcel + return parcel geom
            parcel_payload = None
            parcel_su_id = request.query_params.get('parcel_su_id')
            if parcel_su_id:
                try:
                    parcel_su_id = int(parcel_su_id)
                except (TypeError, ValueError):
                    return Response({"error": "parcel_su_id must be an integer."},
                                    status=status.HTTP_400_BAD_REQUEST)
                buildings = buildings.filter(parent_id__contains=[parcel_su_id])
                parcel = Survey_Rep_DATA_Model.objects.filter(id=parcel_su_id).first()
                if parcel and parcel.geom is not None:
                    try:
                        c = parcel.geom.centroid
                        parcel_payload = {
                            "su_id": parcel.id,
                            "geojson": json.loads(parcel.geom.geojson),
                            "centroid": [float(c.x), float(c.y)],
                        }
                    except Exception:
                        parcel_payload = {"su_id": parcel.id, "geojson": None, "centroid": None}

            # which of those have a stored CityJSON (su_id = building survey_rep id)
            b_ids = list(buildings.values_list('id', flat=True))
            cj_rows = CityJSON_Model.objects.filter(su_id__in=b_ids)
            cj_by_su = {}
            for r in cj_rows.values('id', 'su_id', 'name'):
                cj_by_su.setdefault(r['su_id'], r)  # newest already first by id? keep first seen

            out = []
            for b in buildings:
                cj = cj_by_su.get(b.id)
                if not cj:
                    continue  # only buildings that actually have a 3D model
                centroid = None
                try:
                    c = b.geom.centroid
                    centroid = [float(c.x), float(c.y)]
                except Exception:
                    centroid = None
                out.append({
                    "su_id": b.id,
                    "gnd_id": b.gnd_id,
                    "parent_su_id": (b.parent_id[0] if b.parent_id else None),
                    "name": cj.get('name'),
                    "cityjson_id": cj.get('id'),
                    "centroid": centroid,
                })

            # Parcel context. In parcel-focused (right-click) mode, return only
            # parcels NEAR the focus (within a bbox around it) so the local scene
            # is complete without loading the whole GND. In city mode, return all
            # area parcels (capped).
            PARCEL_CAP = 2000
            base_qs = Survey_Rep_DATA_Model.objects.filter(
                layer_id__in=[1, 6], gnd_id__in=gnd_ids, geom__isnull=False)

            def _materialize(qs):
                rows = []
                for p in qs.order_by('id')[:PARCEL_CAP]:
                    try:
                        rows.append({"su_id": p.id, "geojson": json.loads(p.geom.geojson)})
                    except Exception:
                        continue
                return rows

            parcels_out = []
            used_bbox = False
            if parcel_su_id and parcel_payload and parcel_payload.get("centroid"):
                # ~400 m bbox around the focus parcel centroid. If the spatial
                # filter errors at evaluation (e.g. SRID mismatch on the geom
                # column), fall back to the plain area query instead of 500.
                try:
                    from django.contrib.gis.geos import Polygon as _GEOSPoly
                    clon, clat = parcel_payload["centroid"]
                    dlat = 0.0036
                    dlon = 0.0036 / max(math.cos(math.radians(clat)), 1e-6)
                    bbox = _GEOSPoly.from_bbox(
                        (clon - dlon, clat - dlat, clon + dlon, clat + dlat))
                    bbox.srid = 4326
                    parcels_out = _materialize(base_qs.filter(geom__bboverlaps=bbox))
                    used_bbox = True
                except Exception:
                    parcels_out = []  # fall through to the plain query below

            if not used_bbox:
                parcels_out = _materialize(base_qs)

            return Response({
                "count": len(out),
                "buildings": out,
                "parcel": parcel_payload,      # focus parcel (right-click mode) or None
                "parcels": parcels_out,        # all parcels in area (full city ground)
                "parcels_capped": len(parcels_out) >= PARCEL_CAP,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class City3D_Search_View(APIView):
    """GET /api/user/cityjson/search/?q=<term>

    Search imported 3D buildings + their units by label / apartment name /
    cadastral id, scoped to the login user's organisation area. Returns each
    match with its building su_id and centroid so the client can fly-to.
    """
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            if not _has_3d_perm(request.user, PERM_3D_SEARCH, "view"):
                return _perm_denied("search 3D objects")
            q = (request.query_params.get('q') or '').strip()
            if not q:
                return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

            gnd_ids = _user_gnd_ids(request.user)
            if not gnd_ids:
                return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

            # candidate buildings + units (layer 3 or 12) within the area
            # (survey_rep.status is varchar in DB — don't filter on it)
            in_area = Survey_Rep_DATA_Model.objects.filter(
                layer_id__in=[3, 12], gnd_id__in=gnd_ids,
            )
            in_area_ids = list(in_area.values_list('id', flat=True))
            if not in_area_ids:
                return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

            # match on la_spatial_unit.label OR la_ls_build_unit apt/cadastral fields
            su_label_matches = set(
                LA_Spatial_Unit_Model.objects
                .filter(su_id__in=in_area_ids, label__icontains=q)
                .values_list('su_id', flat=True)
            )
            bu_qs = LA_LS_Build_Unit_Model.objects.filter(su_id__in=in_area_ids)
            bu_filter = Q(apt_name__icontains=q) | Q(building_name__icontains=q)
            # cadastral_id may not exist until P4b migration — guard dynamically
            if any(f.name == 'cadastral_id' for f in LA_LS_Build_Unit_Model._meta.get_fields()):
                bu_filter = bu_filter | Q(cadastral_id__icontains=q)
            bu_matches = set(
                bu_qs.filter(bu_filter).values_list('su_id', flat=True)
            )

            match_ids = su_label_matches | bu_matches
            if not match_ids:
                return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)

            rows = Survey_Rep_DATA_Model.objects.filter(id__in=match_ids).order_by('-id')[:50]

            # resolve display label per matched su
            su_models = {
                m.su_id: m for m in
                LA_Spatial_Unit_Model.objects.filter(su_id__in=[r.id for r in rows])
            }

            results = []
            for r in rows:
                # the building to fly to: itself if layer 3, else its parent
                building_su_id = r.id
                if r.layer_id == 12 and r.parent_id:
                    building_su_id = r.parent_id[0]
                centroid = None
                try:
                    c = r.geom.centroid
                    centroid = [float(c.x), float(c.y)]
                except Exception:
                    centroid = None
                sm = su_models.get(r.id)
                results.append({
                    "su_id": r.id,
                    "building_su_id": building_su_id,
                    "layer_id": r.layer_id,
                    "kind": "building" if r.layer_id == 3 else "unit",
                    "label": (sm.label if sm else None),
                    "gnd_id": r.gnd_id,
                    "centroid": centroid,
                })

            return Response({"count": len(results), "results": results},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
#  P4b — Legal Space Building Unit (LSBU) composition
# =============================================================================
#
#  Terminology (LADM):
#    * Unit  = atomic imported room (layer_id=12, building_unit_type='UNASSIGNED',
#              component_units=[<cityjson room id>]).  Auto UUID.
#    * LSBU  = a group of units forming an apartment / common space. It is one of
#              the units promoted to building_unit_type in
#              {RESIDENTIAL, COMMERCIAL, CIRCULATION, SERVICE, PARKING, AMENITY}
#              with component_units = all member room ids, geom_3d = union of the
#              member solids, and (for private types) a user-entered cadastral_id.
#
#  Model (2-level, exclusive membership — see design §11): rooms stay in the
#  CityJSON; we don't create per-room extra rows. When units are composed into an
#  LSBU, the chosen "primary" unit becomes the LSBU and the other members are
#  marked building_unit_type='ABSORBED' (hidden from the pool, reversible) with a
#  parent_lsbu pointer. No rows are deleted, so composition can be undone.
# =============================================================================

PRIVATE_LSBU_TYPES = {"RESIDENTIAL", "COMMERCIAL"}
COMMON_LSBU_TYPES = {"CIRCULATION", "SERVICE", "PARKING", "AMENITY"}
VALID_LSBU_TYPES = PRIVATE_LSBU_TYPES | COMMON_LSBU_TYPES


def _multipolygon_z_union_wkt(geoms):
    """Concatenate several MULTIPOLYGON Z geometries into one. Each room solid is
    a MULTIPOLYGON Z; the union for an LSBU is just the collection of all member
    polygons (they are disjoint rooms), so we merge their polygon lists."""
    polys = []
    for g in geoms:
        if g is None:
            continue
        try:
            if g.geom_type == "MultiPolygon":
                polys.extend(list(g))
            elif g.geom_type == "Polygon":
                polys.append(g)
        except Exception:
            continue
    if not polys:
        return None
    from django.contrib.gis.geos import MultiPolygon as _MP
    return _MP(*polys, srid=4326)


class LSBU_Units_List_View(APIView):
    """GET /api/user/bld-3d/units/?building_su_id=<int>

    List the rooms/units of a building for the Unit Composition picker.
    Returns unassigned units (the pool) and existing LSBUs separately so the
    picker can show what's still available vs already grouped.
    """
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            if not _has_3d_perm(request.user, PERM_3D_COMPOSE_OPEN, "view"):
                return _perm_denied("open unit composition")
            bsu = request.query_params.get('building_su_id')
            try:
                bsu = int(bsu)
            except (TypeError, ValueError):
                return Response({"error": "building_su_id (int) is required."},
                                status=status.HTTP_400_BAD_REQUEST)

            child_ids = list(
                Survey_Rep_DATA_Model.objects
                .filter(layer_id=12, parent_id__contains=[bsu])
                .values_list('id', flat=True)
            )
            rows = LA_LS_Build_Unit_Model.objects.filter(su_id__in=child_ids)

            pool, lsbus = [], []
            for r in rows:
                item = {
                    "su_id": r.su_id_id,
                    "apt_name": r.apt_name,
                    "floor_no": r.floor_no,
                    "floor_area": float(r.floor_area) if r.floor_area is not None else None,
                    "building_unit_type": r.building_unit_type,
                    "cadastral_id": r.cadastral_id,
                    "component_units": r.component_units or [],
                    "has_geom_3d": r.geom_3d is not None,
                }
                t = (r.building_unit_type or "").upper()
                if t in VALID_LSBU_TYPES:
                    lsbus.append(item)
                elif t == "ABSORBED":
                    continue  # member of an LSBU — not shown standalone
                else:
                    pool.append(item)  # UNASSIGNED / null

            return Response(
                {"building_su_id": bsu, "pool": pool, "lsbus": lsbus,
                 "pool_count": len(pool), "lsbu_count": len(lsbus)},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LSBU_Compose_View(APIView):
    """POST /api/user/bld-3d/lsbu/compose/

    Group selected room-units into ONE Legal Space Building Unit.

    Body:
        building_su_id   : int    (required) parent building
        unit_su_ids      : [int]  (required) member units to group (>=1)
        building_unit_type : str  (required) one of VALID_LSBU_TYPES
        cadastral_id     : str    (required for PRIVATE types; optional for COMMON)
        apt_name         : str    (optional) display label for the LSBU

    Effect (one transaction, reversible):
        * first unit becomes the LSBU (keeps its su_id);
        * its component_units = union of all members' component_units (room ids);
        * its geom_3d = union of all members' solids;
        * the other members → building_unit_type='ABSORBED', parent_lsbu=<lsbu su_id>;
        * exclusive membership enforced: a unit already ABSORBED/!=UNASSIGNED is rejected.
    """
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _has_3d_perm(request.user, PERM_3D_COMPOSE, "add"):
            return _perm_denied("compose legal space building units")
        data = request.data
        bsu = data.get('building_su_id')
        unit_ids = data.get('unit_su_ids')
        lsbu_type = (data.get('building_unit_type') or '').upper()
        cadastral_id = data.get('cadastral_id')
        apt_name = data.get('apt_name')

        try:
            bsu = int(bsu)
        except (TypeError, ValueError):
            return Response({"error": "building_su_id (int) is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(unit_ids, (list, tuple)) or not unit_ids:
            return Response({"error": "unit_su_ids (non-empty list) is required."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            unit_ids = [int(x) for x in unit_ids]
        except (TypeError, ValueError):
            return Response({"error": "unit_su_ids must be integers."},
                            status=status.HTTP_400_BAD_REQUEST)

        if lsbu_type not in VALID_LSBU_TYPES:
            return Response(
                {"error": f"building_unit_type must be one of {sorted(VALID_LSBU_TYPES)}."},
                status=status.HTTP_400_BAD_REQUEST)

        if lsbu_type in PRIVATE_LSBU_TYPES and not (cadastral_id and str(cadastral_id).strip()):
            return Response(
                {"error": "cadastral_id is required for a private (RESIDENTIAL/COMMERCIAL) LSBU."},
                status=status.HTTP_400_BAD_REQUEST)

        # validate the units all belong to this building and are still poolable
        valid_child_ids = set(
            Survey_Rep_DATA_Model.objects
            .filter(layer_id=12, parent_id__contains=[bsu])
            .values_list('id', flat=True)
        )
        bad = [u for u in unit_ids if u not in valid_child_ids]
        if bad:
            return Response({"error": f"Units not children of building {bsu}: {bad}"},
                            status=status.HTTP_404_NOT_FOUND)

        rows = {r.su_id_id: r for r in LA_LS_Build_Unit_Model.objects.filter(su_id__in=unit_ids)}
        missing = [u for u in unit_ids if u not in rows]
        if missing:
            return Response({"error": f"No build_unit rows for: {missing}"},
                            status=status.HTTP_404_NOT_FOUND)

        # exclusive membership: every unit must be UNASSIGNED/empty (not already in an LSBU)
        already = [
            u for u, r in rows.items()
            if (r.building_unit_type or "UNASSIGNED").upper() not in ("UNASSIGNED", "")
        ]
        if already:
            return Response(
                {"error": f"These units are already part of an LSBU (re-assign first): {already}"},
                status=status.HTTP_409_CONFLICT)

        try:
            with transaction.atomic():
                ordered = [rows[u] for u in unit_ids]
                lsbu_row = ordered[0]
                members = ordered

                # union component_units (room ids) + geom_3d
                room_ids = []
                solids = []
                for m in members:
                    room_ids.extend(m.component_units or [])
                    if m.geom_3d is not None:
                        solids.append(m.geom_3d)

                merged_geom = _multipolygon_z_union_wkt(solids)

                lsbu_row.building_unit_type = lsbu_type
                lsbu_row.cadastral_id = (str(cadastral_id).strip() if cadastral_id else None)
                if apt_name:
                    lsbu_row.apt_name = apt_name
                lsbu_row.component_units = room_ids
                if merged_geom is not None:
                    lsbu_row.geom_3d = merged_geom
                lsbu_row.save(update_fields=[
                    "building_unit_type", "cadastral_id", "apt_name",
                    "component_units", "geom_3d",
                ])

                # absorb the other members (reversible: keep rows, mark + point to LSBU)
                absorbed = []
                for m in members[1:]:
                    m.building_unit_type = "ABSORBED"
                    cu = list(m.component_units or [])
                    # stash a back-pointer so re-assignment can restore the room
                    m.component_units = {"parent_lsbu": lsbu_row.su_id_id, "rooms": cu}
                    m.save(update_fields=["building_unit_type", "component_units"])
                    absorbed.append(m.su_id_id)

            return Response({
                "detail": "LSBU composed.",
                "lsbu_su_id": lsbu_row.su_id_id,
                "building_unit_type": lsbu_type,
                "cadastral_id": lsbu_row.cadastral_id,
                "member_room_count": len(room_ids),
                "absorbed_unit_su_ids": absorbed,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#------------------------------------------------------------------------------
# from rest_framework.parsers import MultiPartParser
# import tempfile
# import ifcopenshell
# import ifcopenshell.geom


# class IFCtoCityJSONView(APIView):
#     parser_classes = [MultiPartParser]

#     def post(self, request):

#         # 1️⃣ Get IFC file
#         ifc_file = request.FILES.get("file")
#         if not ifc_file:
#             return Response({"error": "No IFC file provided"}, status=400)

#         # 2️⃣ Save IFC temporarily
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
#             for chunk in ifc_file.chunks():
#                 tmp.write(chunk)
#             tmp_path = tmp.name

#         try:
#             # 3️⃣ Open IFC
#             ifc = ifcopenshell.open(tmp_path)

#             # 4️⃣ Geometry settings
#             settings = ifcopenshell.geom.settings()
#             settings.set(settings.USE_WORLD_COORDS, True)
#             settings.set(settings.DISABLE_OPENING_SUBTRACTIONS, True)

#             # 5️⃣ List of IFC element types to include
#             element_types = ["IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow"]

#             city_vertices = []
#             vertex_map = {}
#             city_objects = {}

#             for elem_type in element_types:
#                 elements = ifc.by_type(elem_type)
#                 for elem in elements:
#                     try:
#                         shape = ifcopenshell.geom.create_shape(settings, elem)
#                     except RuntimeError:
#                         # Skip elements with no geometry
#                         continue

#                     verts = shape.geometry.verts
#                     faces = shape.geometry.faces

#                     boundaries = []
#                     for i in range(0, len(faces), 3):
#                         ring = []
#                         for idx in faces[i:i+3]:
#                             v = (verts[idx*3], verts[idx*3+1], verts[idx*3+2])
#                             key = (round(v[0],5), round(v[1],5), round(v[2],5))
#                             if key not in vertex_map:
#                                 vertex_map[key] = len(city_vertices)
#                                 city_vertices.append(list(key))
#                             ring.append(vertex_map[key])
#                         boundaries.append([ring])

#                     city_objects[elem.GlobalId] = {
#                         "type": "Building",
#                         "attributes": {
#                             "ifc_type": elem_type,
#                             "name": getattr(elem, "Name", "")
#                         },
#                         "geometry": [
#                             {
#                                 "type": "MultiSurface",
#                                 "lod": "2",
#                                 "boundaries": boundaries
#                             }
#                         ]
#                     }

#             # 8️⃣ Build final CityJSON
#             cityjson = {
#                 "type": "CityJSON",
#                 "version": "1.1",
#                 "CityObjects": city_objects,
#                 "vertices": city_vertices
#             }

#             return Response(cityjson)

#         finally:
#             # 9️⃣ Cleanup temp file
#             if os.path.exists(tmp_path):
#                 os.remove(tmp_path)


#________________________________________________ sl_gnd_10m View _______________________________________________________________
class GND_All_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = sl_gnd_10m_Model.objects.all()
    serializer_class = sl_gnd_10m_Attrb_Serializer

#------------------------------------------------------------------------------
class PD_List_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pd_values = sl_gnd_10m_Model.objects.values_list('pd', flat=True).distinct()
        return Response({"pd_list": pd_values})

#------------------------------------------------------------------------------
class PD_Data_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pd_name):
        queryset = sl_gnd_10m_Model.objects.filter(pd=pd_name)
        if not queryset.exists():
            return Response({"error": "No data found for this PD"}, status=status.HTTP_404_NOT_FOUND)

        serializer = sl_gnd_10m_Attrb_Serializer(queryset, many=True)
        return Response(serializer.data)

#------------------------------------------------------------------------------
class Dist_List_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dist_values = sl_gnd_10m_Model.objects.values_list('dist', flat=True).distinct().order_by('dist')
        return Response(dist_values)
