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

#________________________________________________ Search Geom View ______________________________________________________________
class Search_Geom_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only process if su_id is provided
        if "su_id" not in request.data:
            return Response(
                {"error": "su_id field is required at this time."},
                status=status.HTTP_400_BAD_REQUEST
            )

        su_id = request.data.get("su_id")

        records = Survey_Rep_DATA_Model.objects.filter(
            id=su_id,  # using su_id as id
            org_id=request.user.org_id
        )

        if not records.exists():
            return Response(
                {"error": f"No records found for su_id {su_id} in your organization."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = Search_Geom_Serializer(records, many=True)
        data = serializer.data

        # ── Batch-fetch all related data before the loop (prevents N+1 queries) ──

        layer_ids = {item["layer_id"] for item in data if item.get("layer_id") is not None}
        gnd_ids = {item["gnd_id"] for item in data if item.get("gnd_id") is not None}

        layer_map = {
            layer.layer_id: layer.layer_name
            for layer in LayersModel.objects.filter(layer_id__in=layer_ids).only("layer_id", "layer_name")
        }

        gnd_map = {
            row["gid"]: {"gnd": row["gnd"], "dsd": row["dsd"]}
            for row in sl_gnd_10m_Model.objects.filter(gid__in=gnd_ids).values("gid", "gnd", "dsd")
        }

        # su_id is fixed (from request), so postal lookups are pre-fetched once
        land_postal = None
        try:
            land_postal = LA_LS_Land_Unit_Model.objects.values("postal_ad_lnd").get(su_id=su_id)["postal_ad_lnd"]
        except LA_LS_Land_Unit_Model.DoesNotExist:
            pass

        build_postal = None
        try:
            build_postal = LA_LS_Build_Unit_Model.objects.values("postal_ad_build").get(su_id=su_id)["postal_ad_build"]
        except LA_LS_Build_Unit_Model.DoesNotExist:
            pass

        # Enrich each item from lookup dicts — zero DB calls in the loop
        for item in data:
            item["layer_name"] = layer_map.get(item["layer_id"])

            gnd_data = gnd_map.get(item["gnd_id"])
            if gnd_data:
                item.update(gnd_data)
            else:
                item["gnd"] = None
                item["dsd"] = None

            if item["layer_id"] in [1, 6]:
                item["postal_address"] = land_postal
            elif item["layer_id"] == 3:
                item["postal_address"] = build_postal
            else:
                item["postal_address"] = None

        return Response(data, status=status.HTTP_200_OK)


#________________________________________________ Query Parcels View ___________________________________________________________
class Query_Parcels_View(APIView):
    """
    POST /api/user/query-parcels/
    Body: { layer_id, conditions: [{field, operator, value}], logic: 'AND'|'OR' }
    Returns matching features with GeoJSON geometry + attribute data for table display.
    """
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    LAND_LAYER_IDS = {1, 6}
    BUILDING_LAYER_IDS = {3, 12}

    # operator string → Django ORM lookup suffix
    OPERATOR_MAP = {
        '=':  '',
        '!=': '',       # handled as exclude
        '>':  '__gt',
        '<':  '__lt',
        '>=': '__gte',
        '<=': '__lte',
        '%':  '__icontains',
    }

    # field_name → (source, db_field, value_type)
    LAND_FIELDS = {
        'area_m2':          ('survey',     'area',                   'decimal'),
        'land_name':        ('land_unit',  'land_name',              'string'),
        'access_road':      ('land_unit',  'access_road',            'string'),
        'sl_land_type':     ('land_unit',  'sl_land_type',           'string'),
        'postal_address':   ('land_unit',  'postal_ad_lnd',          'string'),
        'assessment_value': ('assessment', 'assessment_annual_value', 'decimal'),
        'market_value':     ('assessment', 'market_value',           'decimal'),
        'land_value':       ('assessment', 'land_value',             'decimal'),
        'tax_status':       ('assessment', 'tax_status',             'string'),
    }

    BUILDING_FIELDS = {
        'area_m2':            ('survey',     'area',                   'decimal'),
        'building_name':      ('build_unit', 'building_name',          'string'),
        'no_floors':          ('build_unit', 'no_floors',              'int'),
        'structure_type':     ('build_unit', 'structure_type',         'string'),
        'condition':          ('build_unit', 'condition',              'string'),
        'roof_type':          ('build_unit', 'roof_type',              'string'),
        'construction_year':  ('build_unit', 'construction_year',      'int'),
        'assessment_value':   ('assessment', 'assessment_annual_value', 'decimal'),
        'market_value':       ('assessment', 'market_value',           'decimal'),
        'land_value':         ('assessment', 'land_value',             'decimal'),
        'tax_status':         ('assessment', 'tax_status',             'string'),
    }

    def _matching_ids(self, base_qs, source, db_field, suffix, value, negated):
        """Return a Python set of Survey_Rep_DATA_Model PKs matching one condition."""
        if source == 'survey':
            if negated:
                ids = set(base_qs.exclude(**{db_field: value}).values_list('id', flat=True))
            else:
                ids = set(base_qs.filter(**{f'{db_field}{suffix}': value}).values_list('id', flat=True))
        elif source == 'land_unit':
            if negated:
                matched = LA_LS_Land_Unit_Model.objects.filter(**{db_field: value}).values_list('su_id', flat=True)
                ids = set(base_qs.exclude(su_id_id__in=matched).values_list('id', flat=True))
            else:
                matched = LA_LS_Land_Unit_Model.objects.filter(**{f'{db_field}{suffix}': value}).values_list('su_id', flat=True)
                ids = set(base_qs.filter(su_id_id__in=matched).values_list('id', flat=True))
        elif source == 'build_unit':
            if negated:
                matched = LA_LS_Build_Unit_Model.objects.filter(**{db_field: value}).values_list('su_id', flat=True)
                ids = set(base_qs.exclude(su_id_id__in=matched).values_list('id', flat=True))
            else:
                matched = LA_LS_Build_Unit_Model.objects.filter(**{f'{db_field}{suffix}': value}).values_list('su_id', flat=True)
                ids = set(base_qs.filter(su_id_id__in=matched).values_list('id', flat=True))
        elif source == 'assessment':
            if negated:
                matched = Assessment_Model.objects.filter(**{db_field: value}).values_list('su_id', flat=True)
                ids = set(base_qs.exclude(su_id_id__in=matched).values_list('id', flat=True))
            else:
                matched = Assessment_Model.objects.filter(**{f'{db_field}{suffix}': value}).values_list('su_id', flat=True)
                ids = set(base_qs.filter(su_id_id__in=matched).values_list('id', flat=True))
        else:
            ids = set()
        return ids

    def _run_query(self, request):
        """
        Execute the query and return (features, layer_id, error_response).
        error_response is None on success, a Response object on failure.
        """
        layer_id = request.data.get('layer_id')
        conditions = request.data.get('conditions', [])
        logic = str(request.data.get('logic', 'AND')).upper()

        if not layer_id:
            return None, None, Response({'error': 'layer_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            layer_id = int(layer_id)
        except (ValueError, TypeError):
            return None, None, Response({'error': 'layer_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        if layer_id in self.LAND_LAYER_IDS:
            field_map = self.LAND_FIELDS
            is_land = True
        elif layer_id in self.BUILDING_LAYER_IDS:
            field_map = self.BUILDING_FIELDS
            is_land = False
        else:
            return None, None, Response(
                {'error': f'Unsupported layer_id: {layer_id}. Supported: 1, 3, 6, 12'},
                status=status.HTTP_400_BAD_REQUEST
            )

        base_qs = Survey_Rep_DATA_Model.objects.filter(
            layer_id=layer_id,
            org_id=request.user.org_id,
            status=True,
        )

        if not conditions:
            qs = base_qs
        else:
            id_sets = []
            for cond in conditions:
                field    = str(cond.get('field', '')).strip()
                operator = str(cond.get('operator', '='))
                value    = cond.get('value', '')

                if field not in field_map:
                    continue

                source, db_field, field_type = field_map[field]

                try:
                    if field_type == 'int':
                        value = int(value)
                    elif field_type == 'decimal':
                        value = float(value)
                    else:
                        value = str(value)
                except (ValueError, TypeError):
                    return None, None, Response(
                        {'error': f'Invalid value "{value}" for field "{field}"'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                negated  = (operator == '!=')
                suffix   = self.OPERATOR_MAP.get(operator, '')
                cond_ids = self._matching_ids(base_qs, source, db_field, suffix, value, negated)
                id_sets.append(cond_ids)

            if not id_sets:
                qs = base_qs.none()
            elif logic == 'OR':
                result_ids = set().union(*id_sets)
                qs = base_qs.filter(id__in=result_ids)
            else:  # AND
                result_ids = id_sets[0]
                for s in id_sets[1:]:
                    result_ids &= s
                qs = base_qs.filter(id__in=result_ids)

        # ── Bulk-fetch attributes to enrich each feature row ──────────────────
        records  = list(qs[:500])
        su_ids   = [r.su_id_id for r in records if r.su_id_id is not None]

        assessments = {
            a.su_id_id: a
            for a in Assessment_Model.objects.filter(su_id_id__in=su_ids)
        }
        if is_land:
            attr_map = {
                lu.su_id_id: lu
                for lu in LA_LS_Land_Unit_Model.objects.filter(su_id_id__in=su_ids)
            }
        else:
            attr_map = {
                bu.su_id_id: bu
                for bu in LA_LS_Build_Unit_Model.objects.filter(su_id_id__in=su_ids)
            }

        features = []
        for record in records:
            su_id = record.su_id_id
            try:
                geom_json = json.loads(record.geom.geojson) if record.geom else None
            except Exception:
                geom_json = None

            a   = attr_map.get(su_id)
            ass = assessments.get(su_id)

            feat = {
                'su_id':            su_id,
                'layer_id':         record.layer_id,
                'area_m2':          float(record.calculated_area) if record.calculated_area else None,
                'geojson':          geom_json,
                'assessment_value': float(ass.assessment_annual_value) if ass and ass.assessment_annual_value is not None else None,
                'market_value':     float(ass.market_value)            if ass and ass.market_value is not None else None,
                'land_value':       float(ass.land_value)              if ass and ass.land_value is not None else None,
                'tax_status':       ass.tax_status                     if ass else None,
            }
            if is_land:
                feat.update({
                    'land_name':      a.land_name      if a else None,
                    'access_road':    a.access_road    if a else None,
                    'sl_land_type':   a.sl_land_type   if a else None,
                    'postal_address': a.postal_ad_lnd  if a else None,
                })
            else:
                feat.update({
                    'building_name':     a.building_name     if a else None,
                    'no_floors':         a.no_floors         if a else None,
                    'structure_type':    a.structure_type    if a else None,
                    'condition':         a.condition         if a else None,
                    'roof_type':         a.roof_type         if a else None,
                    'construction_year': a.construction_year if a else None,
                })
            features.append(feat)

        return features, layer_id, None

    def post(self, request):
        features, layer_id, err = self._run_query(request)
        if err:
            return err
        return Response({
            'count':    len(features),
            'layer_id': layer_id,
            'features': features,
        }, status=status.HTTP_200_OK)


#________________________________________________ Query Parcels SHP Export View ________________________________________________
class Query_Parcels_SHP_Export_View(Query_Parcels_View):
    """
    POST /api/user/query-parcels/export-shp/
    Same body as query-parcels/. Returns a ZIP containing a shapefile of the results.
    Requires: pip install pyshp
    """
    WGS84_PRJ = (
        'GEOGCS["GCS_WGS_1984",'
        'DATUM["D_WGS_1984",'
        'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
        'PRIMEM["Greenwich",0.0],'
        'UNIT["Degree",0.0174532925199433]]'
    )

    def post(self, request):
        try:
            import shapefile
        except ImportError:
            return Response({'error': 'pyshp not installed. Run: pip install pyshp'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        import io, zipfile
        from django.http import HttpResponse

        features, layer_id, err = self._run_query(request)
        if err:
            return err

        is_land = layer_id in self.LAND_LAYER_IDS

        shp_buf = io.BytesIO()
        shx_buf = io.BytesIO()
        dbf_buf = io.BytesIO()

        w = shapefile.Writer(shp=shp_buf, shx=shx_buf, dbf=dbf_buf, shapeType=shapefile.POLYGON)
        w.autoBalance = 1

        # Common fields
        w.field('SU_ID',     'N', 10)
        w.field('LAYER_ID',  'N', 4)
        w.field('AREA_M2',   'N', 15, 2)
        w.field('TAX_STAT',  'C', 10)
        w.field('ASMT_VAL',  'N', 15, 2)
        w.field('MKT_VAL',   'N', 15, 2)
        if is_land:
            w.field('LAND_NAME', 'C', 100)
            w.field('LAND_TYPE', 'C', 50)
            w.field('POSTAL',    'C', 100)
        else:
            w.field('BLD_NAME',  'C', 100)
            w.field('FLOORS',    'N', 4)
            w.field('STRUCT',    'C', 30)
            w.field('COND',      'C', 20)

        for feat in features:
            geom = feat.get('geojson')
            if not geom:
                continue
            try:
                gtype  = geom.get('type', '')
                coords = geom.get('coordinates', [])
                if gtype == 'Polygon':
                    w.poly(coords)
                elif gtype == 'MultiPolygon':
                    w.poly([ring for polygon in coords for ring in polygon])
                else:
                    w.null()
            except Exception:
                w.null()

            common = [
                feat.get('su_id') or 0,
                feat.get('layer_id') or 0,
                float(feat.get('area_m2') or 0),
                (feat.get('tax_status') or '')[:10],
                float(feat.get('assessment_value') or 0),
                float(feat.get('market_value') or 0),
            ]
            if is_land:
                w.record(*common,
                         (feat.get('land_name') or '')[:100],
                         (feat.get('sl_land_type') or '')[:50],
                         (feat.get('postal_address') or '')[:100])
            else:
                w.record(*common,
                         (feat.get('building_name') or '')[:100],
                         int(feat.get('no_floors') or 0),
                         (feat.get('structure_type') or '')[:30],
                         (feat.get('condition') or '')[:20])

        w.close()

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('query_results.shp', shp_buf.getvalue())
            zf.writestr('query_results.shx', shx_buf.getvalue())
            zf.writestr('query_results.dbf', dbf_buf.getvalue())
            zf.writestr('query_results.prj', self.WGS84_PRJ)

        resp = HttpResponse(zip_buf.getvalue(), content_type='application/zip')
        resp['Content-Disposition'] = 'attachment; filename="query_results.zip"'
        return resp


#________________________________________________ Geom Create by View ___________________________________________________________
class Geom_Create_by_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Restrict to admin or super_admin
        if request.user.user_type not in ['admin', 'super_admin']:
            return Response(
                {"error": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        su_id = request.data.get('su_id')

        if not su_id:
            return Response(
                {"error": "su_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get survey
        survey_rep = get_object_or_404(Survey_Rep_DATA_Model, id=su_id)

        # Get user
        user = get_object_or_404(User, id=survey_rep.user_id)

        # Combine data
        data = {
            "id": survey_rep.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_created": survey_rep.date_created
        }

        # Serialize and return
        serializer = Geom_Create_by_Serializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
