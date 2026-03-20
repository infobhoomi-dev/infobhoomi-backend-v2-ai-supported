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

#________________________________________________ Summary (Building) View _______________________________________________________
class Bld_Summary_View(ListCreateAPIView):
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

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Field to permission mapping
            FIELD_PERMISSION_MAP = {
                "assessment_div": 108,
                "postal_ad_bld": 111,
                "bld_property_type": 113,
                "assessment_no": 131,
            }

            # Step 3: Filter fields user has permission to view
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 4: Fetch model data
            bld_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            if not bld_unit:
                return Response({"error": "Data not found for the given su_id."}, status=status.HTTP_404_NOT_FOUND)

            bld_unit_data = {
                "postal_ad_bld": bld_unit.postal_ad_build if bld_unit else None,
                "bld_property_type": bld_unit.bld_property_type if bld_unit else None,
            }

            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            if assessment_unit:
                ward_name = None
                ass_div = getattr(assessment_unit, 'ass_div', None)
                if ass_div:
                    ward = Assessment_Ward_Model.objects.filter(id=ass_div).first()
                    ward_name = ward.ward_name if ward else None
                assessment_unit_data = {
                    "assessment_div": ward_name,
                    "assessment_no": assessment_unit.assessment_no,
                }
            else:
                assessment_unit_data = {
                    "assessment_div": None,
                    "assessment_no": None,
                }

            # Step 5: Combine data and apply field-level filtering
            all_data = {**bld_unit_data, **assessment_unit_data}
            combined_data = {
                field: all_data[field] for field in allowed_fields if field in all_data
            }

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#________________________________________________ Admin_Info (Building) View ____________________________________________________
class Bld_Admin_Info_View(ListCreateAPIView):
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

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Define permission mapping
            FIELD_PERMISSION_MAP = {
                "administrative_type": 101,
                "pd": 102,
                "dist": 103,
                "dsd": 104,
                "gnd_id": 105,
                "gnd": 105,
                "eletorate": 106,
                "local_auth": 107,
                "ass_div": 108,
                "access_road": 109,
                "bld_name": 110,
                "building_name": 110,
                "postal_ad_build": 111,
                "house_hold_no": 112,
                "bld_property_type": 113,
                "no_floors": 114,
                "registration_date": 155,
                "construction_year": 156,
                "structure_type": 157,
                "condition": 158,
                "wall_type": 121,
            }

            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 3: Get survey rep record
            survey_data = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
            gnd_id = survey_data.gnd_id if survey_data else None

            # Step 4: GND details
            gnd_data = sl_gnd_10m_Model.objects.filter(gid=gnd_id).values("gnd", "dsd", "dist", "pd").first()
            gnd_info = {
                "gnd_id": gnd_id,
                "gnd": gnd_data["gnd"] if gnd_data else None,
                "dsd": gnd_data["dsd"] if gnd_data else None,
                "dist": gnd_data["dist"] if gnd_data else None,
                "pd": gnd_data["pd"] if gnd_data else None,
            }

            # Step 5: Local authority
            elect_data = SL_Elect_LocalAuth_Model.objects.filter(gnd_id=gnd_id).values("eletorate", "local_auth").first()
            gnd_info["eletorate"] = elect_data["eletorate"] if elect_data else None
            gnd_info["local_auth"] = elect_data["local_auth"] if elect_data else None

            # Step 6: Building unit
            build_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            build_unit_data = {
                "access_road": build_unit.access_road if build_unit else None,
                "bld_property_type": build_unit.bld_property_type if build_unit else None,
                "bld_name": build_unit.building_name if build_unit else None,
                "building_name": build_unit.building_name if build_unit else None,
                "postal_ad_build": build_unit.postal_ad_build if build_unit else None,
                "house_hold_no": build_unit.house_hold_no if build_unit else None,
                "no_floors": build_unit.no_floors if build_unit else None,
                "wall_type": build_unit.wall_type if build_unit else None,
                "registration_date": str(build_unit.registration_date) if build_unit and build_unit.registration_date else None,
                "construction_year": build_unit.construction_year if build_unit else None,
                "structure_type": build_unit.structure_type if build_unit else None,
                "condition": build_unit.condition if build_unit else None,
            }

            # Step 7: Assessment
            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            assessment_unit_data = {
                "ass_div": getattr(assessment_unit, 'ass_div', None) if assessment_unit else None,
            }

            # Step 8: Static field
            static_data = {
                "administrative_type": "Type01"
            }

            # Combine all
            all_data = {
                **gnd_info,
                **build_unit_data,
                **assessment_unit_data,
                **static_data
            }

            # Apply permission filter
            combined_data = {
                field: all_data[field]
                for field in allowed_fields
                if field in all_data
            }

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Bld_Admin_Info_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "BLD"

            # Define editable field-permission mapping
            FIELD_PERMISSION_MAP = {
                "administrative_type": 101,
                "gnd_id": 105,
                "ass_div": 108,
                "access_road": 109,
                "building_name": 110,
                "postal_ad_build": 111,
                "house_hold_no": 112,
                "bld_property_type": 113,
                "no_floors": 114,
                "wall_type": 121,
                "registration_date": 155,
                "construction_year": 156,
                "structure_type": 157,
                "condition": 158,
            }

            # Step 1: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Get allowed fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 3: Filter request data to only editable fields
            filtered_data = {
                key: value for key, value in request.data.items()
                if key in allowed_fields
            }

            if not filtered_data:
                return Response({"detail": "Nothing to update."}, status=status.HTTP_200_OK)

            # 4. Update LA_LS_Build_Unit_Model (permission-gated fields)
            build_fields = {"building_name", "access_road", "postal_ad_build", "house_hold_no", "bld_property_type",
                            "no_floors", "wall_type", "registration_date", "construction_year", "structure_type", "condition"}
            build_update_data = {k: v for k, v in filtered_data.items() if k in build_fields}

            build_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            if build_unit and build_update_data:
                original = build_unit.__dict__.copy()
                serializer = LA_LS_Build_Unit_Serializer(build_unit, data=build_update_data, partial=True)
                if serializer.is_valid():
                    for attr, value in serializer.validated_data.items():
                        setattr(build_unit, attr, value)
                    build_unit.save(update_fields=list(serializer.validated_data.keys()))
                    self.log_changes(user_id, category, su_id, original, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 5. Update Assessment_Model
            if "ass_div" in filtered_data:
                assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
                if assessment_unit:
                    original = assessment_unit.__dict__.copy()
                    serializer = Assessment_Serializer(assessment_unit, data={"ass_div": filtered_data["ass_div"]}, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        self.log_changes(user_id, category, su_id, original, serializer.validated_data)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 6. Update Survey_Rep_DATA_Model
            if "gnd_id" in filtered_data:
                survey_unit = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
                if survey_unit:
                    original = survey_unit.__dict__.copy()
                    serializer = Survey_Rep_DATA_Serializer(survey_unit, data={"gnd_id": filtered_data["gnd_id"]}, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        self.log_changes(user_id, category, su_id, original, serializer.validated_data)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Data updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        """Log changes to History_Spartialunit_Attrib_Model."""
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)

            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:  # Check if the field value has changed
                changes.append(
                    History_Spartialunit_Attrib_Model(
                        user_id=user_id,
                        su_id_id=su_id,
                        category=category,
                        field_name=field,
                        field_value=new_value
                    )
                )
        # Bulk create all changes
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)

#________________________________________________ Overview DATA (Building) View _________________________________________________
class Bld_Overview_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user's roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Define field-permission mapping
            FIELD_PERMISSION_MAP = {
                "dimension_2d_3d": 115,
                "reference_coordinate": 116,
                "area": 117,
                "ext_builduse_type": 118,
                "ext_builduse_sub_type": 119,
                "roof_type": 120,
                "wall_type": 121
            }

            # Step 3: Get allowed fields based on view permissions
            allowed_fields = [
                key for key, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 4: Get Survey Rep data
            survey_instance = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
            survey_data_dict = {
                "dimension_2d_3d": None,
                "area": None,
                "reference_coordinate": None
            }

            if survey_instance:
                serializer = Survey_Rep_DATA_Overview_Serializer(survey_instance)
                survey_data_dict.update(serializer.data)

            # Step 5: Get Building Unit data
            build_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            build_unit_data = {
                "ext_builduse_type": build_unit.ext_builduse_type if build_unit else None,
                "ext_builduse_sub_type": build_unit.ext_builduse_sub_type if build_unit else None,
                "roof_type": build_unit.roof_type if build_unit else None,
                "wall_type": build_unit.wall_type if build_unit else None,
            }

            # Step 6: Combine and filter data based on permissions
            all_data = {**survey_data_dict, **build_unit_data}
            combined_data = {
                field: all_data[field]
                for field in allowed_fields
                if field in all_data
            }

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Bld_Overview_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "BLD"

            # Step 1: Get user's role IDs
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Get related build unit
            build_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()

            # Step 3: Define permission map (edit-only)
            FIELD_PERMISSION_MAP = {
                "area": 117,
                "ext_builduse_type": 118,
                "ext_builduse_sub_type": 119,
                "roof_type": 120,
                "wall_type": 121,
            }

            # Step 4: Determine editable fields for the user
            editable_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 5: Filter update data by editable fields
            update_data = {field: request.data[field] for field in editable_fields if field in request.data}

            # Step 6: Apply build_unit update (area goes to survey_rep below)
            build_unit_fields = {"ext_builduse_type", "ext_builduse_sub_type", "roof_type", "wall_type"}
            build_update = {k: v for k, v in update_data.items() if k in build_unit_fields}
            if build_unit and build_update:
                original_data = build_unit.__dict__.copy()
                serializer = LA_LS_Build_Unit_Serializer(build_unit, data=build_update, partial=True)
                if serializer.is_valid():
                    for attr, value in serializer.validated_data.items():
                        setattr(build_unit, attr, value)
                    build_unit.save(update_fields=list(serializer.validated_data.keys()))
                    self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Step 7: Save area to Survey_Rep_DATA_Model if permitted
            if "area" in update_data and update_data["area"] not in (None, ""):
                survey_unit = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
                if survey_unit:
                    try:
                        survey_unit.area = update_data["area"]
                        survey_unit.save(update_fields=["area"])
                    except Exception:
                        pass

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

#________________________________________________ Utility_Network_Info (Building) View __________________________________________
class Bld_Utility_Network_Info_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user
            user_id = user.id

            # Step 1: Permission map
            FIELD_PERMISSION_MAP = {
                "elec": 122,
                "tele": 123,
                "internet": 124,
                "water_drink": 125,
                "water": 126,
                "drainage": 127,
                "sani_sewer": 128,
                "sani_gully": 129,
                "garbage_dispose": 130,
            }

            # Step 2: Get user role IDs
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 3: Get allowed fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id, permission_id=perm_id, view=True
                ).exists()
            ]

            # Step 4: Get a single utility record
            data = LA_LS_Utinet_BU_Model.objects.filter(su_id=su_id).first()
            if not data:
                return Response({}, status=status.HTTP_200_OK)

            serializer = Bld_Utinet_info_Serializer(data)
            return Response(
                {k: v for k, v in serializer.data.items() if k in allowed_fields},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Bld_Utility_Network_Info_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "BLD"

            # Step 1: Permission map
            FIELD_PERMISSION_MAP = {
                "elec": 122,
                "tele": 123,
                "internet": 124,
                "water_drink": 125,
                "water": 126,
                "drainage": 127,
                "sani_sewer": 128,
                "sani_gully": 129,
                "garbage_dispose": 130,
            }

            # Step 2: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 3: Determine editable fields
            editable_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 4: Filter incoming data by editable fields
            update_data = {
                field: request.data[field]
                for field in editable_fields
                if field in request.data and request.data[field] not in (None, "")
            }
            if not update_data:
                return Response({"detail": "Nothing to update."}, status=200)

            # Step 5: Get utility network record
            instance = LA_LS_Utinet_BU_Model.objects.filter(su_id=su_id).first()
            if not instance:
                return Response({"error": "No data found for the given su_id."}, status=status.HTTP_404_NOT_FOUND)

            # Step 6: Update utility data
            original_data = instance.__dict__.copy()
            serializer = Bld_Utinet_info_Serializer(instance, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Data updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        """Log changes to History_Spartialunit_Attrib_Model."""
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


#________________________________________________ Tax_Assessment DATA View (Common for Land and Building) _______________________
class Tax_Assessment_View(ListCreateAPIView):
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
                # Assessment_Model fields
                "assessment_no": 24,
                "assessment_name": 25,
                "assessment_annual_value": 26,
                "assessment_percentage": 27,
                "ass_out_balance": 29,
                "date_of_valuation": 30,
                "year_of_assessment": 31,
                "property_type": 32,
                # Tax_Info_Model fields
                "tax_annual_value": 33,
                "tax_percentage": 34,
                "tax_date": 36,
                "tax_type": 37,
            }

            # Step 3: Determine allowed fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 4: Fetch assessment data
            ass_data = Assessment_Model.objects.filter(su_id=su_id).first()
            assessment_data = {
                "assessment_no": None,
                "assessment_name": None,
                "assessment_annual_value": None,
                "assessment_percentage": None,
                "ass_out_balance": None,
                "date_of_valuation": None,
                "year_of_assessment": None,
                "property_type": None,
            }
            if ass_data:
                assessment_data.update(Assessment_Info_Serializer(ass_data).data)

            # Step 5: Fetch tax info data
            tax_data = Tax_Info_Model.objects.filter(su_id=su_id).first()
            tax_info_data = {
                "tax_annual_value": None,
                "tax_percentage": None,
                "tax_date": None,
                "tax_type": None,
            }
            if tax_data:
                tax_info_data.update(Tax_Info_Serializer(tax_data).data)

            # Step 6: Construct combined response using loop
            combined_data = {}

            for field in allowed_fields:
                if field in assessment_data:
                    combined_data[field] = assessment_data[field]
                elif field in tax_info_data:
                    combined_data[field] = tax_info_data[field]

            # Always return new valuation fields (bypass permission gate)
            combined_data["land_value"]    = ass_data.land_value    if ass_data else None
            combined_data["market_value"]  = ass_data.market_value  if ass_data else None
            combined_data["tax_status"]    = ass_data.tax_status    if ass_data else None

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Tax_Assessment_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "Tax-Assess"

            # Step 1: Get roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 2: Define permission mapping
            FIELD_PERMISSION_MAP = {
                "assessment_no": 24,
                "assessment_name": 25,
                "assessment_annual_value": 26,
                "assessment_percentage": 27,
                "ass_out_balance": 29,
                "date_of_valuation": 30,
                "year_of_assessment": 31,
                "property_type": 32,
                "tax_annual_value": 33,
                "tax_percentage": 34,
                "tax_date": 36,
                "tax_type": 37,
                "land_value": 56,
                "market_value": 57,
                "tax_status": 58,
            }

            # Step 3: Determine allowed update fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 4: Filter request data by allowed fields
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

            # Step 5: Update Assessment_Model (create if not exists)
            ass_data = Assessment_Model.objects.filter(su_id=su_id).first()
            if not ass_data:
                ass_data = Assessment_Model(su_id_id=su_id)
                ass_data.save()

            original_assessment_data = ass_data.__dict__.copy()
            assessment_update = {k: v for k, v in update_data.items() if k in Assessment_Info_Serializer.Meta.fields}
            assessment_serializer = Assessment_Info_Serializer(ass_data, data=assessment_update, partial=True)

            if assessment_serializer.is_valid():
                assessment_serializer.save()
                self.log_changes(user_id, category, su_id, original_assessment_data, assessment_serializer.validated_data)
            else:
                return Response(assessment_serializer.errors, status=400)

            # Step 6: Update Tax_Info_Model (create if needed, when tax fields are provided)
            tax_update = {k: v for k, v in update_data.items() if k in Tax_Info_Serializer.Meta.fields}
            tax_info = Tax_Info_Model.objects.filter(su_id=su_id).first()
            if not tax_info and tax_update:
                tax_info = Tax_Info_Model(su_id_id=su_id)
                tax_info.save()
            if tax_info and tax_update:
                original_tax_data = tax_info.__dict__.copy()
                tax_serializer = Tax_Info_Serializer(tax_info, data=tax_update, partial=True)

                if tax_serializer.is_valid():
                    tax_serializer.save()
                    self.log_changes(user_id, category, su_id, original_tax_data, tax_serializer.validated_data)
                else:
                    return Response(tax_serializer.errors, status=400)

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
