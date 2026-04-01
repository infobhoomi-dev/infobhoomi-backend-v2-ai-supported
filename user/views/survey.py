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

import json, os, time, logging
from datetime import timedelta

import user

from ..models import *
from ..serializers import *
from ..constant import *
from ..tests import *

User = get_user_model()

#________________________________________________ Survey Rep DATA View __________________________________________________________
class Survey_Rep_DATA_Save_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = Survey_Rep_DATA_Serializer

    def post(self, request):

        import logging
        logger = logging.getLogger('survey_rep_save')

        _t_start = time.perf_counter()
        data = request.data
        user = request.user
        user_id = user.id

        logger.debug(f"[SAVE⏱] ── New save request from user_id={user_id}, feature_count={len(data) if isinstance(data, list) else 'NOT A LIST'}")

        _t = time.perf_counter()
        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response({"error": "User has no assigned roles."}, status=403)
        role_id = user_roles.values_list('role_id', flat=True).first()
        logger.debug(f"[SAVE⏱] Role lookup: {(time.perf_counter()-_t)*1000:.1f}ms")

        if not isinstance(data, list):
            return Response({"Expected a list of GEOM DATA"}, status=400)

        # --- Hoist per-request queries outside the loop ---
        _t = time.perf_counter()
        permission_id = 201
        has_add_permission = Role_Permission_Model.objects.filter(
            role_id=role_id, permission_id=permission_id, add=True
        ).exists()
        has_edit_permission = Role_Permission_Model.objects.filter(
            role_id=role_id, permission_id=permission_id, edit=True
        ).exists()
        logger.debug(f"[SAVE⏱] Permission checks: {(time.perf_counter()-_t)*1000:.1f}ms")

        _t = time.perf_counter()
        my_layerIDs = set(
            LayersModel.objects.filter(group_name__contains=[user_id]).values_list('layer_id', flat=True)
        )
        logger.debug(f"[SAVE⏱] Layer IDs fetch: {(time.perf_counter()-_t)*1000:.1f}ms")

        _t = time.perf_counter()
        org_area_obj = Org_Area_Model.objects.filter(org_id=user.org_id).first()
        logger.debug(f"[SAVE⏱] Org area fetch: {(time.perf_counter()-_t)*1000:.1f}ms")

        saved_records = []
        errors = []
        warnings = []

        with transaction.atomic():
            for index, item in enumerate(data):
                _props = item.get("properties", {})
                _geom  = item.get("geometry", {})
                logger.debug(
                    f"[SAVE] [{index}] uuid={_props.get('uuid')} | layer_id={_props.get('layer_id')} "
                    f"| geom_type={_geom.get('type')} | calculated_area={_props.get('calculated_area')} "
                    f"| gnd_id={_props.get('gnd_id')} | parent_uuid={_props.get('parent_uuid')} "
                    f"| feature_Id={_props.get('feature_Id')} | isUpdateOnly={_props.get('isUpdateOnly')}"
                )
                try:
                  _t_feat = time.perf_counter()
                  with transaction.atomic():
                    # Step 1: Check if user has save/edit permission
                    parent_uuid = item.get("properties", {}).get("parent_uuid", [])

                    if not parent_uuid:  # parent_uuid is null or empty → ADD permission
                        if not has_add_permission:
                            return Response({"error": "You do not have add permission."}, status=403)
                    else:  # parent_uuid exists → EDIT permission
                        if not has_edit_permission:
                            return Response({"error": "You do not have edit permission."}, status=403)

                    item.setdefault("properties", {})["user_id"] = user.id
                    item["properties"]["org_id"] = user.org_id

                    # Extract geom_type for save it to geom_type field
                    geom_type = item.get("geometry", {}).get("type", None)
                    if not geom_type:
                        raise ValueError("The 'geometry.type' field is required")

                    geom_type = geom_type.lower()
                    item["properties"]["geom_type"] = geom_type

                    _t = time.perf_counter()
                    # Parse geometry once — reused for both area calculation and GND detection
                    _geom_json = item.get("geometry")
                    _crs = item.get("properties", {}).get("crs", "EPSG:4326")
                    try:
                        _srid = int(_crs.split(":")[-1]) if _crs else 4326
                    except (ValueError, AttributeError):
                        _srid = 4326
                    # Parse once with the actual SRID declared by the client
                    _geom_obj_native = GEOSGeometry(json.dumps(_geom_json), srid=_srid)
                    # WGS84 reference — needed for GND spatial queries (PostGIS spatial index is in EPSG:4326)
                    _geom_obj_4326 = _geom_obj_native.transform(4326, clone=True) if _srid != 4326 else _geom_obj_native
                    # Project to EPSG:5235 (Sri Lanka 1999, metric) for accurate area/length in square metres
                    _geom_obj = _geom_obj_native.transform(5235, clone=True)
                    if geom_type in ["polygon", "multipolygon"]:
                        item["properties"]["calculated_area"] = round(_geom_obj.area, 4)
                    elif geom_type in ["linestring", "multilinestring"]:
                        item["properties"]["calculated_area"] = round(_geom_obj.length, 4)
                    else:
                        item["properties"]["calculated_area"] = 0
                    logger.debug(f"[SAVE⏱]   Geometry parse + area calc: {(time.perf_counter()-_t)*1000:.1f}ms")

                    # Check gnd_id for all geometry types
                    _t = time.perf_counter()
                    if geom_type in ["polygon", "multipolygon"]:
                        layer_id_val = item.get("properties", {}).get("layer_id")
                        is_land_parcel = layer_id_val in [1, 6]
                        gndID = item.get("properties", {}).get("gnd_id")
                        if not gndID:
                            # Reuse already-parsed geometry (no second parse)
                            geom_obj = _geom_obj_4326
                            dominant_gnd = None
                            try:
                                # Wrap in its own savepoint so a DB error (e.g. missing
                                # geom column on sl_gnd_10m) is rolled back before we
                                # continue — otherwise PostgreSQL leaves the connection in
                                # an ABORTED state and all subsequent queries fail with
                                # "current transaction is aborted".
                                with transaction.atomic():
                                    # Fast path: centroid point-in-polygon (uses spatial index, no geometry computation)
                                    centroid = geom_obj.centroid
                                    dominant_gnd = sl_gnd_10m_Model.objects.filter(geom__contains=centroid).first()
                                    if not dominant_gnd:
                                        # Slow fallback: parcel straddles a GND boundary — find dominant by intersection area
                                        dominant_gnd = (
                                            sl_gnd_10m_Model.objects
                                            .filter(geom__intersects=geom_obj)
                                            .annotate(inter_area=Area(GeoIntersection('geom', geom_obj)))
                                            .order_by('-inter_area')
                                            .first()
                                        )
                            except Exception:
                                # sl_gnd_10m has no geom column — skip GND validation
                                dominant_gnd = None
                                is_land_parcel = False  # allow save without GND

                            if not dominant_gnd:
                                if is_land_parcel:
                                    raise ValueError("Cannot save land parcel: geometry does not fall within any GND boundary.")
                                else:
                                    item["properties"]["gnd_id"] = None
                            else:
                                # Validate detected GND is within the org's allowed area
                                if org_area_obj and org_area_obj.org_area and org_area_obj.org_area != [0]:
                                    if dominant_gnd.gid not in org_area_obj.org_area:
                                        if is_land_parcel:
                                            raise ValueError("Cannot save land parcel: geometry falls outside your organisation's allowed GND area.")
                                        else:
                                            item["properties"]["gnd_id"] = None
                                    else:
                                        item["properties"]["gnd_id"] = dominant_gnd.gid
                                else:
                                    item["properties"]["gnd_id"] = dominant_gnd.gid

                    elif geom_type in ["point", "multipoint", "linestring", "multilinestring"]:
                        gndID = item.get("properties", {}).get("gnd_id")
                        if not gndID:
                            # Reuse already-parsed geometry (no second parse)
                            lookup_point = _geom_obj_4326.centroid
                            try:
                                with transaction.atomic():
                                    containing_gnd = sl_gnd_10m_Model.objects.filter(geom__contains=lookup_point).first()
                            except Exception:
                                containing_gnd = None
                            if not containing_gnd:
                                raise ValueError("Cannot save feature: geometry does not fall within any GND boundary.")
                            else:
                                if org_area_obj and org_area_obj.org_area and org_area_obj.org_area != [0]:
                                    if containing_gnd.gid not in org_area_obj.org_area:
                                        raise ValueError("Cannot save feature: geometry falls outside your organisation's allowed GND area.")
                                    else:
                                        item["properties"]["gnd_id"] = containing_gnd.gid
                                else:
                                    item["properties"]["gnd_id"] = containing_gnd.gid
                    logger.debug(f"[SAVE⏱]   GND detection: {(time.perf_counter()-_t)*1000:.1f}ms (gnd_id provided: {bool(gndID)})")

                    # Extract parent_id
                    _t = time.perf_counter()
                    parent_ids = item.get("properties", {}).get("parent_id", []) # [11287]
                    if isinstance(parent_ids, list) and parent_ids:
                        Survey_Rep_DATA_Model.objects.filter(id__in=parent_ids).update(status=False)

                    # Extract parent_uuid and convert it to parent_id
                    parent_uuids = item.get("properties", {}).get("parent_uuid", [])
                    parent_ids = []

                    if isinstance(parent_uuids, list) and parent_uuids:
                        parent_ids = list(Survey_Rep_DATA_Model.objects.filter(uuid__in=parent_uuids).values_list('id', flat=True))
                        item["properties"]["parent_id"] = parent_ids  # Assign retrieved IDs to parent_id

                    # Update status for parent_ids if they exist
                    if parent_ids:
                        Survey_Rep_DATA_Model.objects.filter(id__in=parent_ids).update(status=False)
                    logger.debug(f"[SAVE⏱]   Parent ID lookup + status update: {(time.perf_counter()-_t)*1000:.1f}ms")

                    # Inject the already-parsed GEOSGeometry so GeometryField.to_internal_value
                    # hits its isinstance(value, GEOSGeometry) short-circuit and skips re-parsing.
                    item["geometry"] = _geom_obj_native
                    _t = time.perf_counter()
                    serializer = self.serializer_class(data=item)
                    serializer_valid = serializer.is_valid()
                    logger.debug(f"[SAVE⏱]   Serializer validation (geom pre-injected, no re-parse): {(time.perf_counter()-_t)*1000:.1f}ms")

                    if serializer_valid:
                        _t = time.perf_counter()
                        # Save Survey_Rep_DATA_Model instance.
                        # trg_survey_rep_su_id (BEFORE INSERT trigger) sets su_id = id
                        # at the DB level — no second UPDATE round-trip needed.
                        survey_rep = serializer.save()
                        survey_rep.su_id_id = survey_rep.id  # sync Python object only
                        logger.debug(f"[SAVE⏱]   INSERT survey_rep (su_id set by trigger): {(time.perf_counter()-_t)*1000:.1f}ms")

                        # Batch all related object creation into bulk_create lists
                        geom_history_objs = [Survey_Rep_Geom_History_Model(
                            su_id=survey_rep.id,
                            user_id=survey_rep.user_id,
                            layer_id=survey_rep.layer_id,
                            calculated_area=survey_rep.calculated_area,
                            reference_coordinate=survey_rep.reference_coordinate,
                            geom=survey_rep.geom,
                            status=survey_rep.status,
                            ref_id=survey_rep.ref_id,
                        )]
                        Survey_Rep_Geom_History_Model.objects.bulk_create(geom_history_objs)
                        logger.debug(f"[SAVE⏱]   Geom history INSERT: {(time.perf_counter()-_t)*1000:.1f}ms")

                        _t = time.perf_counter()
                        # Create the LADM spatial unit anchor — required immediately so that
                        # land/building detail views can look it up via FK.
                        # All other detail records (Assessment, Tax_Info, Land_Unit, etc.) are
                        # created lazily by their respective update views on first edit, avoiding
                        # empty placeholder rows for parcels that are never annotated.
                        LA_Spatial_Unit_Model.objects.create(su_id=survey_rep.id)
                        logger.debug(f"[SAVE⏱]   Spatial unit INSERT: {(time.perf_counter()-_t)*1000:.1f}ms")
                        logger.debug(f"[SAVE⏱] ── Feature [{index}] total: {(time.perf_counter()-_t_feat)*1000:.1f}ms")

                        # Return only the fields the frontend needs to update feature IDs/metadata.
                        # Avoids serializing the full geometry back (GeoFeatureModelSerializer is expensive).
                        saved_records.append({
                            "type": "Feature",
                            "geometry": None,
                            "properties": {
                                "id": survey_rep.id,
                                "su_id": survey_rep.id,
                                "uuid": str(survey_rep.uuid),
                                "gnd_id": survey_rep.gnd_id,
                                "calculated_area": float(survey_rep.calculated_area) if survey_rep.calculated_area is not None else None,
                                "layer_id": survey_rep.layer_id,
                                "status": survey_rep.status,
                                "parent_id": survey_rep.parent_id,
                            },
                        })

                    else:
                        logger.debug(f"[SAVE] [{index}] Serializer validation FAILED: {serializer.errors}")
                        errors.append({"index": index, "errors": serializer.errors})
                except Exception as e:
                        logger.debug(f"[SAVE] [{index}] Exception during save: {e}", exc_info=True)
                        errors.append({"index": index, "detail": str(e)})

        # Return the response with saved records and errors
        response_data = {
            "saved_records": saved_records,
            "errors": errors,
            "warnings": warnings,
        }

        logger.debug(f"[SAVE⏱] ══ TOTAL backend time: {(time.perf_counter()-_t_start)*1000:.1f}ms | saved={len(saved_records)} errors={len(errors)} ══")
        if saved_records:
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

#------------------------------------------------------------------------------
class Survey_Rep_DATA_Filter_User_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        user_obj = request.user
        userID = user_obj.id # Retrieve userID from the User model
        org_id = user_obj.org_id

        layer_ids = list(LayersModel.objects.filter(
            Q(group_name__contains=["default"]) |
            Q(group_name__contains=[userID]) |
            (Q(group_name__contains=["org"]) & Q(org_id=org_id)) |
            Q(user_id=userID)
        ).values_list('layer_id', flat=True))

        # Use the retrieved layer_ids to filter Survey_Rep_DATA_Model
        # Exclude null-geometry records — these are legacy LADM records imported
        # without spatial data.  Sending them to the frontend causes console spam
        # and wastes bandwidth since they can never be rendered.
        geom_data = list(Survey_Rep_DATA_Model.objects.filter(
            layer_id__in=layer_ids,
            status=True,
            org_id=org_id,
            geom__isnull=False,
        ).only('id', 'su_id', 'uuid', 'layer_id', 'gnd_id', 'calculated_area', 'parent_id', 'status', 'geom'))

        # Serialize geom data — lean serializer sends only map-required fields
        serializer = Survey_Rep_Map_Serializer(geom_data, many=True)
        return Response(serializer.data, status=200)

#------------------------------------------------------------------------------
class Survey_Rep_DATA_Update_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Survey_Rep_DATA_Model.objects.all()
    serializer_class = Survey_Rep_DATA_Serializer

    def update(self, request, *args, **kwargs):

        import copy as _copy
        logger = logging.getLogger('survey_rep_update')

        _t_start = time.perf_counter()
        data = request.data
        user = request.user
        user_id = user.id
        feature_id = kwargs.get('pk', '?')
        logger.debug(f"[UPDATE⏱] ── PATCH id={feature_id} user_id={user_id}")

        # 🔐 Step 1: Check if user has edit permission
        _t = time.perf_counter()
        edit_permission_id = 201

        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response({"error": "User has no assigned roles."}, status=403)

        role_id = user_roles.values_list('role_id', flat=True).first()

        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=edit_permission_id,
            edit=True
        ).exists()

        if not has_permission:
            return Response({"error": "You do not have permission."}, status=403)
        logger.debug(f"[UPDATE⏱] Step 1 — permission check: {(time.perf_counter()-_t)*1000:.1f}ms")

        # Step 2: Fetch org area once — reused in both polygon and point/line GND branches
        _t = time.perf_counter()
        org_area_obj = Org_Area_Model.objects.filter(org_id=user.org_id).first()
        logger.debug(f"[UPDATE⏱] Step 2 — org area fetch: {(time.perf_counter()-_t)*1000:.1f}ms")

        with transaction.atomic():
            # Step 3: Fetch instance + snapshot old data
            _t = time.perf_counter()
            instance = self.get_object()
            logger.debug(f"[UPDATE⏱] Step 3 — get_object(): {(time.perf_counter()-_t)*1000:.1f}ms | geom_type={instance.geom_type} layer_id={instance.layer_id}")

            old_data = {
                "user_id": instance.user_id,
                "layer_id": instance.layer_id,
                "calculated_area": instance.calculated_area,
                "reference_coordinate": instance.reference_coordinate,
                "geom": instance.geom,
                "status": instance.status,
                "ref_id": instance.ref_id,
            }

            # Ensure gnd_id is not null in the request payload before serializer
            # validation runs.  The frontend sends null when geometry is edited
            # (gnd_id is unknown until spatial detection runs post-update).
            # We temporarily inject the instance's current value so validation
            # passes; the post-update block below will re-enforce the correct
            # gnd_id based on the new geometry.
            _raw = request.data
            _props = _raw.get('properties', {}) if isinstance(_raw, dict) else {}
            if not _props.get('gnd_id'):
                _mutable = _copy.deepcopy(dict(_raw))
                _mutable.setdefault('properties', {})['gnd_id'] = instance.gnd_id
                request._full_data = _mutable

            # Step 4: DRF serializer validate + write geometry to DB
            _t = time.perf_counter()
            super().update(request, *args, **kwargs)
            logger.debug(f"[UPDATE⏱] Step 4 — serializer validate + DB write (super().update): {(time.perf_counter()-_t)*1000:.1f}ms")

            # Step 5: Refresh instance with what was just written
            _t = time.perf_counter()
            instance.refresh_from_db()
            logger.debug(f"[UPDATE⏱] Step 5 — refresh_from_db: {(time.perf_counter()-_t)*1000:.1f}ms")

            # Accumulate all post-update field changes; flush with one save() at end.
            fields_to_save = ['date_modified']
            instance.date_modified = now()

            # Step 6: Recalculate area/length from updated geometry
            _t = time.perf_counter()
            if instance.geom:
                _crs = instance.reference_coordinate or "EPSG:4326"
                try:
                    _srid = int(_crs.split(":")[-1])
                except (ValueError, AttributeError):
                    _srid = 4326
                _geom_projected = instance.geom.transform(5235, clone=True) if _srid in [4326, 4269, 4230] else instance.geom.transform(_srid, clone=True)
                if instance.geom_type in ["polygon", "multipolygon"]:
                    instance.calculated_area = round(_geom_projected.area, 4)
                elif instance.geom_type in ["linestring", "multilinestring"]:
                    instance.calculated_area = round(_geom_projected.length, 4)
                else:
                    instance.calculated_area = 0
                fields_to_save.append('calculated_area')
            logger.debug(f"[UPDATE⏱] Step 6 — area/length recalculation: {(time.perf_counter()-_t)*1000:.1f}ms")

            # Step 7: GND detection after geometry update
            _t = time.perf_counter()
            if instance.geom_type in ["polygon", "multipolygon"] and instance.geom:
                layer_id_val = instance.layer_id
                is_land_parcel = layer_id_val in [1, 6]
                try:
                    with transaction.atomic():
                        # Fast path: centroid point-in-polygon (uses spatial index, no area computation)
                        centroid = instance.geom.centroid
                        dominant_gnd = sl_gnd_10m_Model.objects.filter(geom__contains=centroid).first()
                        _gnd_path = 'centroid'
                        if not dominant_gnd:
                            # Slow fallback: parcel straddles a GND boundary — find dominant by intersection area
                            dominant_gnd = (
                                sl_gnd_10m_Model.objects
                                .filter(geom__intersects=instance.geom)
                                .annotate(inter_area=Area(GeoIntersection('geom', instance.geom)))
                                .order_by('-inter_area')
                                .first()
                            )
                            _gnd_path = 'intersection-fallback'
                    logger.debug(f"[UPDATE⏱] Step 7 — GND detect ({_gnd_path}) → gnd={dominant_gnd.gid if dominant_gnd else None}: {(time.perf_counter()-_t)*1000:.1f}ms")
                    if not dominant_gnd:
                        if is_land_parcel:
                            return Response(
                                {"error": "Cannot update land parcel: geometry does not fall within any GND boundary."},
                                status=400
                            )
                    else:
                        if org_area_obj and org_area_obj.org_area and org_area_obj.org_area != [0]:
                            if dominant_gnd.gid not in org_area_obj.org_area:
                                if is_land_parcel:
                                    return Response(
                                        {"error": "Cannot update land parcel: geometry falls outside your organisation's allowed GND area."},
                                        status=400
                                    )
                            else:
                                instance.gnd_id = dominant_gnd.gid
                                fields_to_save.append('gnd_id')
                        else:
                            instance.gnd_id = dominant_gnd.gid
                            fields_to_save.append('gnd_id')
                except Exception:
                    logger.debug(f"[UPDATE⏱] Step 7 — GND detect exception after {(time.perf_counter()-_t)*1000:.1f}ms", exc_info=True)
                    if is_land_parcel:
                        raise

            elif instance.geom_type in ["point", "multipoint", "linestring", "multilinestring"] and instance.geom:
                try:
                    with transaction.atomic():
                        lookup_point = instance.geom.centroid
                        containing_gnd = sl_gnd_10m_Model.objects.filter(geom__contains=lookup_point).first()
                    logger.debug(f"[UPDATE⏱] Step 7 — GND detect (centroid point/line) → gnd={containing_gnd.gid if containing_gnd else None}: {(time.perf_counter()-_t)*1000:.1f}ms")
                    if not containing_gnd:
                        return Response(
                            {"error": "Cannot update feature: geometry does not fall within any GND boundary."},
                            status=400
                        )
                    if org_area_obj and org_area_obj.org_area and org_area_obj.org_area != [0]:
                        if containing_gnd.gid not in org_area_obj.org_area:
                            return Response(
                                {"error": "Cannot update feature: geometry falls outside your organisation's allowed GND area."},
                                status=400
                            )
                    instance.gnd_id = containing_gnd.gid
                    fields_to_save.append('gnd_id')
                except Exception:
                    logger.debug(f"[UPDATE⏱] Step 7 — GND detect exception after {(time.perf_counter()-_t)*1000:.1f}ms", exc_info=True)
                    raise
            else:
                logger.debug(f"[UPDATE⏱] Step 7 — GND detect skipped (no geom): 0.0ms")

            # Step 8: Single DB write for all post-update field changes
            _t = time.perf_counter()
            instance.save(update_fields=list(set(fields_to_save)))
            logger.debug(f"[UPDATE⏱] Step 8 — save({fields_to_save}): {(time.perf_counter()-_t)*1000:.1f}ms")

            # Step 9: History comparison + optional INSERT
            _t = time.perf_counter()
            new_data = {
                "user_id": instance.user_id,
                "layer_id": instance.layer_id,
                "calculated_area": instance.calculated_area,
                "reference_coordinate": instance.reference_coordinate,
                "geom": instance.geom,
                "status": instance.status,
                "ref_id": instance.ref_id,
            }

            history_written = False
            if old_data != new_data:
                Survey_Rep_Geom_History_Model.objects.create(
                    su_id=instance.id,
                    user_id=instance.user_id,
                    layer_id=instance.layer_id,
                    calculated_area=instance.calculated_area,
                    reference_coordinate=instance.reference_coordinate,
                    geom=instance.geom,
                    status=instance.status,
                    ref_id=instance.ref_id,
                )
                history_written = True
            logger.debug(f"[UPDATE⏱] Step 9 — history write (written={history_written}): {(time.perf_counter()-_t)*1000:.1f}ms")

            logger.debug(f"[UPDATE⏱] ══ TOTAL: {(time.perf_counter()-_t_start)*1000:.1f}ms | id={feature_id} ══")

            # Return lean response — no geometry re-serialization (mirrors save view)
            return Response({
                "type": "Feature",
                "geometry": None,
                "properties": {
                    "id": instance.id,
                    "su_id": instance.id,
                    "uuid": str(instance.uuid),
                    "gnd_id": instance.gnd_id,
                    "calculated_area": float(instance.calculated_area) if instance.calculated_area is not None else None,
                    "layer_id": instance.layer_id,
                    "status": instance.status,
                    "parent_id": instance.parent_id,
                    "date_modified": instance.date_modified.isoformat() if instance.date_modified else None,
                },
            }, status=200)

#------------------------ Bulk DELETE by IDs ----------------------------------
class Survey_Rep_DATA_BulkDelete_id_View(APIView):
    http_method_names = ['delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete_record_and_related(self, su_id, logger):
        """Delete a single survey record and its related data. Permission must be verified before calling."""
        _t = time.perf_counter()
        total_deleted = 0
        parent_ids = []

        try:
            primary = Survey_Rep_DATA_Model.objects.get(id=su_id)
            parent_ids = primary.parent_id or []
            _t2 = time.perf_counter()
            logger.debug(f"[DELETE⏱]   fetch record id={su_id}: {(_t2-_t)*1000:.1f}ms")

            # Delete LA_Spatial_Unit_Model for this su_id
            _t2 = time.perf_counter()
            n = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).delete()[0]
            total_deleted += n
            logger.debug(f"[DELETE⏱]   DELETE LA_Spatial_Unit (n={n}): {(time.perf_counter()-_t2)*1000:.1f}ms")

            # Delete ref_id-related Survey_Rep_DATA_Model and LA_Spatial_Unit_Model
            _t2 = time.perf_counter()
            ref_qs = Survey_Rep_DATA_Model.objects.filter(ref_id=su_id)
            ref_ids = list(ref_qs.values_list("id", flat=True))
            n_ref = ref_qs.delete()[0]
            n_ref_su = LA_Spatial_Unit_Model.objects.filter(su_id__in=ref_ids).delete()[0]
            total_deleted += n_ref + n_ref_su
            logger.debug(f"[DELETE⏱]   DELETE ref children (survey={n_ref}, spatial_units={n_ref_su}): {(time.perf_counter()-_t2)*1000:.1f}ms")

            # Delete the main record
            _t2 = time.perf_counter()
            primary.delete()
            total_deleted += 1
            logger.debug(f"[DELETE⏱]   DELETE primary record id={su_id}: {(time.perf_counter()-_t2)*1000:.1f}ms")

        except Survey_Rep_DATA_Model.DoesNotExist:
            logger.debug(f"[DELETE⏱]   id={su_id} not found — skipped")

        logger.debug(f"[DELETE⏱]   record id={su_id} total: {(time.perf_counter()-_t)*1000:.1f}ms | rows_deleted={total_deleted}")
        return total_deleted, parent_ids

    def delete(self, request):
        logger = logging.getLogger('survey_rep_delete')
        _t_start = time.perf_counter()

        su_ids = request.data.get('ids', [])
        if not isinstance(su_ids, list) or not su_ids:
            return Response({"error": "Please provide a list of ids to delete."}, status=status.HTTP_400_BAD_REQUEST)

        logger.debug(f"[DELETE⏱] ── DELETE request | ids={su_ids}")

        # 🔐 Step 1: Permission check once — not repeated per record
        _t = time.perf_counter()
        user = request.user
        user_id = user.id

        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response({"error": "User has no assigned roles."}, status=403)

        role_id = user_roles.values_list('role_id', flat=True).first()

        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=201,
            delete=True
        ).exists()

        if not has_permission:
            return Response({"error": "You do not have delete permission."}, status=403)
        logger.debug(f"[DELETE⏱] Step 1 — permission check: {(time.perf_counter()-_t)*1000:.1f}ms")

        total_deleted = 0
        deleted_ids = set()
        parent_ids_to_update = set()

        # Step 2: Delete each requested record
        for su_id in su_ids:
            if su_id in deleted_ids:
                continue

            logger.debug(f"[DELETE⏱] Step 2 — processing id={su_id}")
            deleted, parent_ids = self.delete_record_and_related(su_id, logger)
            total_deleted += deleted
            deleted_ids.add(su_id)

            # Step 3: Resolve and delete siblings
            if len(parent_ids) == 1:
                parent_id = parent_ids[0]
                _t = time.perf_counter()
                siblings = Survey_Rep_DATA_Model.objects.filter(parent_id__contains=[parent_id])
                sibling_ids = [s.id for s in siblings if s.id not in deleted_ids]
                logger.debug(f"[DELETE⏱] Step 3 — sibling query (parent_id={parent_id}, found={len(sibling_ids)}): {(time.perf_counter()-_t)*1000:.1f}ms")
                for sib_id in sibling_ids:
                    d, _ = self.delete_record_and_related(sib_id, logger)
                    total_deleted += d
                    deleted_ids.add(sib_id)

                parent_ids_to_update.add(parent_id)

            elif len(parent_ids) > 1:
                parent_ids_to_update.update(parent_ids)

        # Step 4: Restore parent status
        if parent_ids_to_update:
            _t = time.perf_counter()
            Survey_Rep_DATA_Model.objects.filter(id__in=parent_ids_to_update).update(status=True)
            logger.debug(f"[DELETE⏱] Step 4 — restore parent status (ids={list(parent_ids_to_update)}): {(time.perf_counter()-_t)*1000:.1f}ms")

        logger.debug(f"[DELETE⏱] ══ TOTAL: {(time.perf_counter()-_t_start)*1000:.1f}ms | deleted_ids={list(deleted_ids)} rows={total_deleted} ══")

        return Response(
            {"message": f"Records deleted. {total_deleted} total record(s) affected."},
            status=status.HTTP_200_OK
        )


#________________________________________________ Survey Rep History View _______________________________________________________ not used
class Survey_Rep_History_View_filter(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        rep_history = Survey_Rep_History_Model.objects.filter(su_id=su_id)
        serializer = Survey_Rep_History_Serializer(rep_history, many=True)
        return Response(serializer.data, status=200)

#------------------------------------------------------------------------------
class Survey_Rep_History_View_filter_username(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user  # Get user from token
        user_id = user.id    # Extract user_id


        # Step 1: Get Survey_Rep_History records for the given userID
        rep_history = Survey_Rep_History_Model.objects.filter(user_id=user_id)
        serializer = Survey_Rep_History_Serializer_username(rep_history, many=True)

        # Step 2: Extract `layer_id` for each record in `serializer.data`
        response_data = []
        for record in serializer.data:
            su_id = record.get('su_id')  # Assuming `su_id` is in serializer.data

            # Add `layer_id` to the response
            layer_id_record = Survey_Rep_DATA_Model.objects.filter(id=su_id).values('layer_id').first()
            record['layer_id'] = layer_id_record['layer_id'] if layer_id_record else None

            # Fetch `user_email` from User model
            user_id = record.get('user_id')
            user = User.objects.filter(id=user_id).values('email').first()
            record['username'] = user['email'] if user else None

            response_data.append(record)

        # Return the response with layer_id and other serializer data
        return Response(response_data, status=200)

#------------------------------------------------------------------------------
class Survey_Rep_History_View_update(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch', 'put', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Survey_Rep_History_Model.objects.all()
    serializer_class = Survey_Rep_History_Serializer


#________________________________________________ Geom Edit History View ________________________________________________________
class Geom_Edit_History_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = Survey_Rep_Geom_History_Serializer

    def get_queryset(self):
        # Get the su_id from the URL
        ver_suid = self.kwargs.get('ver_suid')

        # Subquery to find the earliest record for each unique geom
        earliest_geom_records = (Survey_Rep_Geom_History_Model.objects.filter(su_id=ver_suid)
            .values('geom')  # Group by geom
            .annotate(earliest_date=Min('date_created'))  # Find the earliest date for each geom
            .values_list('geom', 'earliest_date')  # Get geom and earliest date pairs
        )

        # Filter to include only records with the earliest date for each unique geom
        queryset = Survey_Rep_Geom_History_Model.objects.filter(su_id=ver_suid).filter(
            Q(geom__in=[record[0] for record in earliest_geom_records]) &
            Q(date_created__in=[record[1] for record in earliest_geom_records])
        )

        return queryset.order_by('date_created')
