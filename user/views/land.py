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

#________________________________________________ SL BA Unit View _______________________________________________________________ not used
class SL_BA_Unit_ID_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        ba_unit_id = SL_BA_Unit_Model.objects.filter(su_id=su_id).values_list('ba_unit_id', flat=True).first()
        return Response({"ba_unit_id": ba_unit_id}, status=200)

#________________________________________________ Summary (Land) View ___________________________________________________________
class Lnd_Summary_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get roles for the user
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"detail": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 2: Field to permission mapping
            FIELD_PERMISSION_MAP = {
                "property_type": 10,
                "postal_ad_lnd": 11,
                "assessment_no": 24,
                "assessment_div": 6,
                "land_area": 14
            }

            # Step 3: Check permissions — one query for all IDs (avoids N+1)
            _allowed_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=FIELD_PERMISSION_MAP.values(),
                    view=True,
                ).values_list("permission_id", flat=True)
            )
            allowed_fields = [f for f, pid in FIELD_PERMISSION_MAP.items() if pid in _allowed_ids]

            # Step 4: Get land unit data
            land_unit = LA_LS_Land_Unit_Model.objects.filter(su_id=su_id).first()
            land_unit_data = {
                "property_type": land_unit.sl_land_type if land_unit else None,
                "postal_ad_lnd": land_unit.postal_ad_lnd if land_unit else None,
            }

            # Step 4a: Get Land Area
            land_area = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
            land_area_data = {
                "land_area": land_area.area if land_area else None
            }

            # Step 5: Get assessment data
            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            assessment_unit_data = {
                "assessment_div": None,
                "assessment_no": None
            }

            if assessment_unit:
                assessment_unit_data["assessment_no"] = assessment_unit.assessment_no

                ass_div = getattr(assessment_unit, 'ass_div', None)
                if ass_div:
                    ward = Assessment_Ward_Model.objects.filter(id=ass_div).first()
                    if ward:
                        assessment_unit_data["assessment_div"] = ward.ward_name

            # Step 6: Combine + Filter by permission
            combined_data = {}

            # Merge both dictionaries
            all_data = {**land_unit_data, **assessment_unit_data, **land_area_data}

            # Add only allowed fields to the response
            for field in allowed_fields:
                if field in all_data:
                    combined_data[field] = all_data[field]

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#________________________________________________ Admin_Info (Land) View ________________________________________________________
class Lnd_Admin_Info_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)

            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 2: Define permission map
            FIELD_PERMISSION_MAP = {
                "administrative_type": 1,
                "pd": 2,
                "dist": 3,
                "dsd": 4,
                "gnd_id": 5,
                "gnd": 5,
                "ass_div": 6,
                "eletorate": 7,
                "local_auth": 8,
                "access_road": 9,
                "sl_land_type": 10,
                "postal_ad_lnd": 11,
                "land_name": 12,
            }

            # Step 3: Get allowed fields — one query for all IDs (avoids N+1)
            _allowed_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=FIELD_PERMISSION_MAP.values(),
                    view=True,
                ).values_list("permission_id", flat=True)
            )
            allowed_fields = [f for f, pid in FIELD_PERMISSION_MAP.items() if pid in _allowed_ids]

            # Step 4: Derive gnd_id from spatial intersection of the parcel polygon
            # Falls back to stored gnd_id when the sl_gnd_10m table has no geometry column.
            survey_data = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
            gnd_id = None
            if survey_data and survey_data.geom:
                from django.db import transaction as _tx
                _geom_sid = _tx.savepoint()
                try:
                    gnd_match = sl_gnd_10m_Model.objects.filter(geom__intersects=survey_data.geom).first()
                    gnd_id = gnd_match.gid if gnd_match else None
                    # Cache result back to survey_rep so other queries stay consistent
                    if gnd_id and survey_data.gnd_id != gnd_id:
                        Survey_Rep_DATA_Model.objects.filter(su_id=su_id).update(gnd_id=gnd_id)
                    _tx.savepoint_commit(_geom_sid)
                except Exception:
                    _tx.savepoint_rollback(_geom_sid)
                    gnd_id = survey_data.gnd_id  # geom column missing — use stored value
            elif survey_data:
                gnd_id = survey_data.gnd_id  # fallback to stored value if no geometry yet

            gnd_data = sl_gnd_10m_Model.objects.filter(gid=gnd_id).values("gnd", "dsd", "dist", "pd").first()
            elect_data = SL_Elect_LocalAuth_Model.objects.filter(gnd_id=gnd_id).values("eletorate", "local_auth").first()

            land_unit = LA_LS_Land_Unit_Model.objects.filter(su_id=su_id).first()
            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            spatial_unit = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).first()

            # Step 5: Collect all possible data
            all_data = {
                "gnd_id": gnd_id,
                "gnd": gnd_data["gnd"] if gnd_data else None,
                "dsd": gnd_data["dsd"] if gnd_data else None,
                "dist": gnd_data["dist"] if gnd_data else None,
                "pd": gnd_data["pd"] if gnd_data else None,
                "eletorate": elect_data["eletorate"] if elect_data else None,
                "local_auth": (land_unit.local_auth if (land_unit and land_unit.local_auth) else (elect_data["local_auth"] if elect_data else None)),
                "sl_land_type": land_unit.sl_land_type if land_unit else None,
                "tenure_type": land_unit.tenure_type if land_unit else None,
                "access_road": land_unit.access_road if land_unit else None,
                "postal_ad_lnd": land_unit.postal_ad_lnd if land_unit else None,
                "land_name": land_unit.land_name if land_unit else None,
                "registration_date": str(land_unit.registration_date) if land_unit and land_unit.registration_date else None,
                "ass_div": getattr(assessment_unit, 'ass_div', None) if assessment_unit else None,
                "administrative_type": "None"
            }

            # Step 6: Filter by allowed fields
            response_data = {field: value for field, value in all_data.items() if field in allowed_fields}

            # Fields without dedicated permission IDs — always returned
            response_data["registration_date"] = all_data.get("registration_date")
            response_data["tenure_type"] = all_data.get("tenure_type")
            response_data["parcel_status"] = spatial_unit.parcel_status if spatial_unit else None
            response_data["adjacent_parcels"] = land_unit.adjacent_parcels if land_unit else None
            response_data["parent_parcel"] = land_unit.parent_parcel if land_unit else None
            response_data["child_parcels"] = land_unit.child_parcels if land_unit else None
            response_data["part_of_estate"] = land_unit.part_of_estate if land_unit else None

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Lnd_Admin_Info_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "LND"

            # Step 1: Get user's roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: editable fields and permission IDs
            # gnd_id is excluded — it is auto-derived from spatial intersection, not user-editable
            FIELD_PERMISSION_MAP = {
                "ass_div": 6,
                "local_auth": 8,
                "access_road": 9,
                "sl_land_type": 10,
                "postal_ad_lnd": 11,
                "land_name": 12,
            }

            # Step 3: allowed editable fields — one query for all IDs (avoids N+1)
            _edit_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=FIELD_PERMISSION_MAP.values(),
                    edit=True,
                ).values_list("permission_id", flat=True)
            )
            allowed_fields = [f for f, pid in FIELD_PERMISSION_MAP.items() if pid in _edit_ids]

            # Step 4: Filter request data by allowed fields
            filtered_data = {field: value for field, value in request.data.items() if field in allowed_fields}

            # --- LA_LS_Land_Unit_Model update ---
            # Use get_or_create so parcels imported before this record was auto-created still work
            spatial_unit_ref = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).first()
            if spatial_unit_ref:
                land_unit, _ = LA_LS_Land_Unit_Model.objects.get_or_create(su_id=spatial_unit_ref)
            else:
                land_unit = None
            if land_unit:
                lu_fields = ["sl_land_type", "tenure_type", "access_road", "postal_ad_lnd", "land_name", "local_auth"]
                lu_data = {f: filtered_data[f] for f in lu_fields if f in filtered_data}
                # Fields without dedicated permission IDs — always allowed
                for rel_field in ["adjacent_parcels", "parent_parcel", "child_parcels", "part_of_estate"]:
                    if rel_field in request.data:
                        lu_data[rel_field] = request.data[rel_field] or None
                if "registration_date" in request.data and request.data["registration_date"]:
                    lu_data["registration_date"] = request.data["registration_date"]
                if "tenure_type" in request.data:
                    lu_data["tenure_type"] = request.data["tenure_type"] or None
                if lu_data:
                    original_data = land_unit.__dict__.copy()
                    serializer = LA_LS_Land_Unit_Serializer(land_unit, data=lu_data, partial=True)
                    if serializer.is_valid():
                        # Use update_fields to avoid overwriting concurrently-saved columns
                        for attr, value in serializer.validated_data.items():
                            setattr(land_unit, attr, value)
                        land_unit.save(update_fields=list(serializer.validated_data.keys()))
                        self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
                    else:
                        return Response(serializer.errors, status=400)

            # --- Assessment_Model update ---
            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            if assessment_unit and "ass_div" in filtered_data:
                original_data = assessment_unit.__dict__.copy()
                serializer = Assessment_Serializer(assessment_unit, data={"ass_div": filtered_data["ass_div"]}, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=400)

            # --- LA_Spatial_Unit_Model update (parcel_status) — always allowed ---
            if "parcel_status" in request.data:
                spatial_unit = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).first()
                if spatial_unit:
                    spatial_unit.parcel_status = request.data["parcel_status"] or None
                    spatial_unit.save(update_fields=["parcel_status"])

            return Response({"detail": "Data updated successfully."}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(History_Spartialunit_Attrib_Model(
                    user_id=user_id,
                    su_id_id=su_id,
                    category=category,
                    field_name=field,
                    field_value=new_value
                ))
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)

#________________________________________________ Overview DATA (Land) View _____________________________________________________
class Lnd_Overview_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user's roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"detail": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Define permission map
            FIELD_PERMISSION_MAP = {
                "dimension_2d_3d": 13,
                "boundary_type": 13,
                "crs": 13,
                "area": 14,
                "perimeter": 14,
                "reference_coordinate": 16,
                "ext_landuse_type": 17,
                "ext_landuse_sub_type": 18,
            }

            # Step 3: Get allowed fields — one query for all IDs (avoids N+1)
            _allowed_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=FIELD_PERMISSION_MAP.values(),
                    view=True,
                ).values_list("permission_id", flat=True)
            )
            allowed_fields = [f for f, pid in FIELD_PERMISSION_MAP.items() if pid in _allowed_ids]

            # Step 4: Get land unit data (primary LADM source for spatial attrs)
            land_unit = LA_LS_Land_Unit_Model.objects.filter(su_id=su_id).first()

            # Step 5: Get Survey Rep data (fallback for area/dimension + reference_coordinate)
            survey_data = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
            survey_area = None
            survey_dim = None
            survey_ref_coord = None
            if survey_data:
                sr_serializer = Survey_Rep_DATA_Overview_Serializer(survey_data)
                sr_data = sr_serializer.data
                survey_area = sr_data.get("area")
                survey_dim = sr_data.get("dimension_2d_3d")
                survey_ref_coord = sr_data.get("reference_coordinate")

            # Prefer la_ls_land_unit values; fall back to survey_rep for backward compat
            all_data = {
                "area": (float(land_unit.area) if land_unit and land_unit.area is not None else survey_area),
                "perimeter": (float(land_unit.perimeter) if land_unit and land_unit.perimeter is not None else None),
                "dimension_2d_3d": (land_unit.dimension_2d_3d if land_unit and land_unit.dimension_2d_3d else survey_dim),
                "boundary_type": land_unit.boundary_type if land_unit else None,
                "crs": land_unit.crs if land_unit else None,
                "reference_coordinate": survey_ref_coord,
                "ext_landuse_type": land_unit.ext_landuse_type if land_unit else None,
                "ext_landuse_sub_type": land_unit.ext_landuse_sub_type if land_unit else None,
            }

            # Step 6: Filter permission-gated fields
            combined_data = {field: all_data[field] for field in allowed_fields if field in all_data}

            return Response(combined_data, status=status.HTTP_200_OK)


        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Lnd_Overview_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "LND"

            # Step 1: Get user's role IDs
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Get or create related land unit (parcels imported before auto-creation need this)
            spatial_unit_ref = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).first()
            if not spatial_unit_ref:
                return Response({"error": "Spatial unit not found for the given su_id."}, status=status.HTTP_404_NOT_FOUND)
            land_unit, _ = LA_LS_Land_Unit_Model.objects.get_or_create(su_id=spatial_unit_ref)

            # Step 3: Define permission map (edit-only)
            FIELD_PERMISSION_MAP = {
                "dimension_2d_3d": 13,
                "boundary_type": 13,
                "crs": 13,
                "area": 14,
                "perimeter": 14,
                "ext_landuse_type": 17,
                "ext_landuse_sub_type": 18,
            }

            # Step 4: Determine editable fields for the user — one query (avoids N+1)
            _edit_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=FIELD_PERMISSION_MAP.values(),
                    edit=True,
                ).values_list("permission_id", flat=True)
            )
            editable_fields = [f for f, pid in FIELD_PERMISSION_MAP.items() if pid in _edit_ids]

            # Step 5: Filter update data by editable fields
            update_data = {field: request.data[field] for field in editable_fields if field in request.data}

            # Step 6: Apply land-unit update (only if there are permitted fields to update)
            if update_data:
                original_data = land_unit.__dict__.copy()
                serializer = LA_LS_Land_Unit_Serializer(land_unit, data=update_data, partial=True)
                if serializer.is_valid():
                    # Use update_fields to avoid overwriting concurrently-saved columns
                    for attr, value in serializer.validated_data.items():
                        setattr(land_unit, attr, value)
                    land_unit.save(update_fields=list(serializer.validated_data.keys()))
                    self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Step 8: Save reference_coordinate (centroid) to survey_rep as a Point geometry (P7)
            if 'reference_coordinate' in request.data and request.data['reference_coordinate']:
                try:
                    from django.contrib.gis.geos import Point
                    lon, lat = [float(x.strip()) for x in str(request.data['reference_coordinate']).split(',')]
                    survey = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
                    if survey:
                        survey.reference_coordinate = Point(lon, lat, srid=4326)
                        survey.save(update_fields=['reference_coordinate'])
                except (ValueError, AttributeError):
                    pass  # ignore malformed coordinate strings

            return Response({"detail": "Data updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(
                    History_Spartialunit_Attrib_Model(
                        user_id=user_id,
                        su_id_id=su_id,
                        category=category,
                        field_name=field,
                        field_value=new_value
                    )
                )
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)

#________________________________________________ Zoning Info (Land) Views _______________________________________________________
class Lnd_Zoning_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    FIELD_PERMISSION_MAP = {
        "zoning_category": 48, "max_building_height": 49, "max_coverage": 50,
        "max_far": 51, "setback_front": 52, "setback_rear": 53,
        "setback_side": 54, "special_overlay": 55,
    }

    def get(self, request, su_id):
        try:
            user_roles = User_Roles_Model.objects.filter(users__contains=[request.user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            role_id = user_roles.values_list("role_id", flat=True).first()
            _allowed_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=self.FIELD_PERMISSION_MAP.values(),
                    view=True,
                ).values_list("permission_id", flat=True)
            )
            allowed_fields = [f for f, pid in self.FIELD_PERMISSION_MAP.items() if pid in _allowed_ids]
            zoning = LA_LS_Zoning_Model.objects.filter(su_id=su_id).first()
            empty = {f: None for f in allowed_fields}
            if not zoning:
                return Response(empty, status=status.HTTP_200_OK)
            data = LA_LS_Zoning_Serializer(zoning).data
            return Response({f: data.get(f) for f in allowed_fields}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Lnd_Zoning_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    FIELD_PERMISSION_MAP = {
        "zoning_category": 48, "max_building_height": 49, "max_coverage": 50,
        "max_far": 51, "setback_front": 52, "setback_rear": 53,
        "setback_side": 54, "special_overlay": 55,
    }

    def patch(self, request, su_id):
        try:
            user_roles = User_Roles_Model.objects.filter(users__contains=[request.user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            role_id = user_roles.values_list("role_id", flat=True).first()
            _edit_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=self.FIELD_PERMISSION_MAP.values(),
                    edit=True,
                ).values_list("permission_id", flat=True)
            )
            allowed_fields = [f for f, pid in self.FIELD_PERMISSION_MAP.items() if pid in _edit_ids]
            zoning, _ = LA_LS_Zoning_Model.objects.get_or_create(su_id_id=su_id)
            update_data = {k: (None if v == '' else v) for k, v in request.data.items() if k in allowed_fields}
            serializer = LA_LS_Zoning_Serializer(zoning, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"detail": "Zoning data updated successfully."}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#________________________________________________ Physical_Env_Info (Land) Views _________________________________________________
class Lnd_Physical_Env_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    FIELD_PERMISSION_MAP = {
        "elevation": 43, "slope": 44, "soil_type": 45,
        "flood_zone": 46, "vegetation_cover": 47,
    }

    def get(self, request, su_id):
        try:
            user_roles = User_Roles_Model.objects.filter(users__contains=[request.user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            role_id = user_roles.values_list("role_id", flat=True).first()
            _allowed_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=self.FIELD_PERMISSION_MAP.values(),
                    view=True,
                ).values_list("permission_id", flat=True)
            )
            allowed_fields = [f for f, pid in self.FIELD_PERMISSION_MAP.items() if pid in _allowed_ids]
            obj = LA_LS_Physical_Env_Model.objects.filter(su_id=su_id).first()
            empty = {f: None for f in allowed_fields}
            if not obj:
                return Response(empty, status=status.HTTP_200_OK)
            data = LA_LS_Physical_Env_Serializer(obj).data
            return Response({f: data.get(f) for f in allowed_fields}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Lnd_Physical_Env_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    FIELD_PERMISSION_MAP = {
        "elevation": 43, "slope": 44, "soil_type": 45,
        "flood_zone": 46, "vegetation_cover": 47,
    }

    def patch(self, request, su_id):
        try:
            user_roles = User_Roles_Model.objects.filter(users__contains=[request.user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            role_id = user_roles.values_list("role_id", flat=True).first()
            _edit_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=self.FIELD_PERMISSION_MAP.values(),
                    edit=True,
                ).values_list("permission_id", flat=True)
            )
            allowed_fields = [f for f, pid in self.FIELD_PERMISSION_MAP.items() if pid in _edit_ids]
            obj, _ = LA_LS_Physical_Env_Model.objects.get_or_create(su_id_id=su_id)
            update_data = {k: (None if v == '' else v) for k, v in request.data.items() if k in allowed_fields}
            serializer = LA_LS_Physical_Env_Serializer(obj, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"detail": "Physical/environmental data updated successfully."}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#________________________________________________ LA_BAUnit_SpatialUnit (M:M) Views _____________________________________________
class LA_BAUnit_SpatialUnit_View(APIView):
    """LADM ISO 19152 – manage the M:M associations between BA units and spatial units.

    GET  ba-unit-spatial-unit/ba_unit_id=<int>/  → list all SUs linked to this BA unit
    POST ba-unit-spatial-unit/ba_unit_id=<int>/  → add a new association  { su_id, relation_type? }
    DELETE ba-unit-spatial-unit/ba_unit_id=<int>/ → remove one association { id }
    """
    http_method_names = ['get', 'post', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, ba_unit_id):
        try:
            links = LA_BAUnit_SpatialUnit_Model.objects.filter(ba_unit_id=ba_unit_id)
            serializer = LA_BAUnit_SpatialUnit_Serializer(links, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, ba_unit_id):
        try:
            su_id = request.data.get('su_id')
            relation_type = request.data.get('relation_type', 'PRIMARY')
            if not su_id:
                return Response({"error": "su_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            if not LA_Spatial_Unit_Model.objects.filter(su_id=su_id).exists():
                return Response({"error": "Spatial unit not found."}, status=status.HTTP_404_NOT_FOUND)
            link, created = LA_BAUnit_SpatialUnit_Model.objects.get_or_create(
                ba_unit_id=ba_unit_id, su_id=su_id,
                defaults={'relation_type': relation_type}
            )
            if not created:
                link.relation_type = relation_type
                link.save()
            serializer = LA_BAUnit_SpatialUnit_Serializer(link)
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, ba_unit_id):
        try:
            link_id = request.data.get('id') or request.query_params.get('id')
            if not link_id:
                return Response({"error": "id is required."}, status=status.HTTP_400_BAD_REQUEST)
            deleted, _ = LA_BAUnit_SpatialUnit_Model.objects.filter(
                id=link_id, ba_unit_id=ba_unit_id
            ).delete()
            if deleted == 0:
                return Response({"error": "Association not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"detail": "Association removed."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────────────────────
# RRR Role-Based Permission Helpers
# ─────────────────────────────────────────────────────────────────────────────
_LAND_LAYERS    = frozenset({1, 6})
_BUILDING_LAYERS = frozenset({3, 12})
_RRR_PERM_LAND     = 59   # Land RRR section permission ID
_RRR_PERM_BUILDING = 162  # Building RRR section permission ID


def _rrr_perm_for_su(su_id):
    """Return the correct RRR permission ID (59 or 162) for a spatial unit."""
    sr = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).values('layer_id').first()
    if sr:
        if sr['layer_id'] in _LAND_LAYERS:
            return _RRR_PERM_LAND
        if sr['layer_id'] in _BUILDING_LAYERS:
            return _RRR_PERM_BUILDING
    # Fallback: if a build_unit record exists it is a building
    if LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).exists():
        return _RRR_PERM_BUILDING
    return _RRR_PERM_LAND


def _rrr_perm_for_ba(ba_unit_id):
    """Return the RRR permission ID by resolving ba_unit_id → su_id."""
    ba = SL_BA_Unit_Model.objects.filter(ba_unit_id=ba_unit_id).values('su_id_id').first()
    return _rrr_perm_for_su(ba['su_id_id']) if ba else _RRR_PERM_LAND


def _rrr_perm_for_rrr_id(rrr_id):
    """Return the RRR permission ID by resolving rrr_id → ba_unit → su_id."""
    rrr = LA_RRR_Model.objects.filter(rrr_id=rrr_id).values('ba_unit_id_id').first()
    return _rrr_perm_for_ba(rrr['ba_unit_id_id']) if rrr else _RRR_PERM_LAND


from ..utils import has_perm as _has_rrr_perm, perm_denied as _rrr_permission_denied  # noqa: E402


#________________________________________________ RRR Restriction Views __________________________________________________________
class RRR_Restriction_View(APIView):
    http_method_names = ['get', 'post', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'view'):
            return _rrr_permission_denied()
        try:
            restrictions = LA_RRR_Restriction_Model.objects.filter(rrr_id=rrr_id)
            serializer = LA_RRR_Restriction_Serializer(restrictions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'add'):
            return _rrr_permission_denied()
        try:
            allowed_fields = ['rrr_restriction_type', 'description', 'time_begin', 'time_end']
            data = {k: (None if v == '' else v) for k, v in request.data.items() if k in allowed_fields}
            data['rrr_id'] = rrr_id
            serializer = LA_RRR_Restriction_Serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()
        restriction_id = request.data.get('id') or request.query_params.get('id')
        if not restriction_id:
            return Response({"error": "id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            obj = LA_RRR_Restriction_Model.objects.get(id=restriction_id, rrr_id=rrr_id)
            obj.delete()
            return Response({"detail": "Restriction deleted."}, status=status.HTTP_200_OK)
        except LA_RRR_Restriction_Model.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#________________________________________________ RRR Responsibility Views _______________________________________________________
class RRR_Responsibility_View(APIView):
    http_method_names = ['get', 'post', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'view'):
            return _rrr_permission_denied()
        try:
            responsibilities = LA_RRR_Responsibility_Model.objects.filter(rrr_id=rrr_id)
            serializer = LA_RRR_Responsibility_Serializer(responsibilities, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'add'):
            return _rrr_permission_denied()
        try:
            allowed_fields = ['rrr_responsibility_type', 'description', 'time_begin', 'time_end']
            data = {k: (None if v == '' else v) for k, v in request.data.items() if k in allowed_fields}
            data['rrr_id'] = rrr_id
            serializer = LA_RRR_Responsibility_Serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()
        responsibility_id = request.data.get('id') or request.query_params.get('id')
        if not responsibility_id:
            return Response({"error": "id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            obj = LA_RRR_Responsibility_Model.objects.get(id=responsibility_id, rrr_id=rrr_id)
            obj.delete()
            return Response({"detail": "Responsibility deleted."}, status=status.HTTP_200_OK)
        except LA_RRR_Responsibility_Model.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#________________________________________________ Utility_Network_Info (Land) View ______________________________________________
class Lnd_Utility_Network_Info_View(ListCreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        user = request.user

        # Step 1: Get user roles
        user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
        if not user_roles.exists():
            return Response({"detail": "User has no assigned roles."}, status=403)

        # Step 2: Field to permission mapping
        FIELD_PERMISSION_MAP = {
            "electricity": 19,
            "water_supply": 20,
            "drainage_system": 21,
            "sanitation_gully": 22,
            "garbage_disposal": 23,
        }

        # Step 3: Check allowed fields
        role_id = user_roles.values_list('role_id', flat=True).first()

        _allowed_ids = set(
            Role_Permission_Model.objects.filter(
                role_id=role_id,
                permission_id__in=FIELD_PERMISSION_MAP.values(),
                view=True,
            ).values_list("permission_id", flat=True)
        )
        allowed_field_keys = [k for k, pid in FIELD_PERMISSION_MAP.items() if pid in _allowed_ids]

        # Step 4: Fetch utility network data
        utinet_data = LA_LS_Utinet_LU_Model.objects.filter(su_id=su_id).first()
        if not utinet_data:
            # Return empty nulls for all allowed fields instead of 404
            return Response({key: None for key in allowed_field_keys}, status=200)

        # Step 5: Serialize data
        raw_data = Lnd_Utinet_info_Serializer(utinet_data).data

        # Step 6: Mapping field keys to model fields
        model_field_map = {
            "electricity": "elec",
            "water_supply": "water",
            "drainage_system": "drainage",
            "sanitation_gully": "sani_gully",
            "garbage_disposal": "garbage_dispose"
        }

        # Step 7: Combine + Filter by permission
        response_data = {
            key: raw_data.get(model_field_map[key])
            for key in allowed_field_keys
        }

        return Response(response_data, status=200)

#------------------------------------------------------------------------------
class Lnd_Utility_Network_Info_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "LND"

            utinet_data = LA_LS_Utinet_LU_Model.objects.filter(su_id=su_id).first()
            if not utinet_data:
                utinet_data = LA_LS_Utinet_LU_Model.objects.create(su_id_id=su_id)

            # Permissions: Role → Permissions for editing
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list('role_id', flat=True).first()

            # Define field mapping and corresponding permission IDs
            FIELD_PERMISSION_MAP = {
                "water_supply": {"model_field": "water", "permission_id": 20},
                "electricity": {"model_field": "elec", "permission_id": 19},
                "drainage_system": {"model_field": "drainage", "permission_id": 21},
                "sanitation_gully": {"model_field": "sani_gully", "permission_id": 22},
                "garbage_disposal": {"model_field": "garbage_dispose", "permission_id": 23},
            }

            # Copy original data to compare for logging
            original_data = utinet_data.__dict__.copy()

            # Batch-fetch all edit-allowed permission IDs (avoids N+1)
            _edit_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=[v["permission_id"] for v in FIELD_PERMISSION_MAP.values()],
                    edit=True,
                ).values_list("permission_id", flat=True)
            )

            update_data = {
                info["model_field"]: request.data[input_field]
                for input_field, info in FIELD_PERMISSION_MAP.items()
                if input_field in request.data and info["permission_id"] in _edit_ids
            }

            # Apply changes
            for field, value in update_data.items():
                setattr(utinet_data, field, value)

            utinet_data.save()

            # Log updated fields
            self.log_changes(
                user_id=user_id,
                category=category,
                su_id=su_id,
                original_data=original_data,
                updated_data=update_data
            )

            return Response({"detail": "Data updated successfully."}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(
                    History_Spartialunit_Attrib_Model(
                        user_id=user_id,
                        su_id_id=su_id,
                        category=category,
                        field_name=field,
                        field_value=new_value
                    )
                )
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)
