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
            survey_data = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
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

            build_unit, _ = LA_LS_Build_Unit_Model.objects.get_or_create(su_id_id=su_id)
            if build_update_data:
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
                assessment_unit, _ = Assessment_Model.objects.get_or_create(su_id_id=su_id)
                original = assessment_unit.__dict__.copy()
                serializer = Assessment_Serializer(assessment_unit, data={"ass_div": filtered_data["ass_div"]}, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    self.log_changes(user_id, category, su_id, original, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 6. Update Survey_Rep_DATA_Model
            if "gnd_id" in filtered_data:
                survey_unit = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
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
            survey_instance = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
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

            # Step 2: Get or create related build unit
            build_unit, _ = LA_LS_Build_Unit_Model.objects.get_or_create(su_id_id=su_id)

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
            if build_update:
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
                survey_unit = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
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

            # Step 5: Get or create utility network record
            instance, _ = LA_LS_Utinet_BU_Model.objects.get_or_create(su_id_id=su_id)

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
            _edit_ids = set(
                Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id__in=FIELD_PERMISSION_MAP.values(),
                    edit=True,
                ).values_list('permission_id', flat=True)
            )
            allowed_fields = [f for f, pid in FIELD_PERMISSION_MAP.items() if pid in _edit_ids]

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


# =============================================================================
# Building Units (Strata / Apartment Units — layer_id = 12)
# =============================================================================
#
# Each apartment unit is a proper LADM LA_SpatialUnit stored as a survey_rep
# record with layer_id=12 and parent_id=[<parent_building_su_id>].
# Its attribute data lives in la_ls_build_unit and la_ls_utinet_bu, the same
# tables used for parent buildings, but with the unit's own su_id.
#
# The geom_3d column on la_ls_build_unit holds the PolyhedralSurface / solid
# geometry shared with the sister 3D Cadastre project for cross-platform
# visualisation.
# =============================================================================

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_role(user):
    """Return (role_id, error_response) for a given user.
    Returns (None, Response) on failure."""
    user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
    if not user_roles.exists():
        return None, Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
    return user_roles.values_list("role_id", flat=True).first(), None


def _allowed_fields(role_id, field_map, mode="view"):
    """Return the list of field names the role has 'view' or 'edit' permission for."""
    perm_ids = list(field_map.values())
    has_perm = set(
        Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id__in=perm_ids,
            **{mode: True},
        ).values_list("permission_id", flat=True)
    )
    return [f for f, pid in field_map.items() if pid in has_perm]


# Permission map for unit admin fields (reuses building permission IDs + adds unit-specific ones)
UNIT_ADMIN_FIELD_PERM = {
    "apt_name":            110,   # reuse building_name perm
    "floor_no":            114,   # reuse no_floors perm
    "floor_area":          117,   # reuse area perm
    "postal_ad_build":     111,
    "house_hold_no":       112,
    "bld_property_type":   113,
    "access_road":         109,
    "wall_type":           121,
    "registration_date":   155,
    "construction_year":   156,
    "structure_type":      157,
    "condition":           158,
    "ext_builduse_type":   118,
    "ext_builduse_sub_type": 119,
    "roof_type":           120,
    "hight":               117,   # share area perm for height
    "surface_relation":    114,
}

UNIT_UTIL_FIELD_PERM = {
    "water":          126,
    "water_drink":    125,
    "elec":           122,
    "tele":           123,
    "internet":       124,
    "drainage":       127,
    "sani_sewer":     128,
    "sani_gully":     129,
    "garbage_dispose": 130,
}


def _unit_to_dict(su_id, survey_row, admin_row, util_row):
    """Merge survey_rep + la_ls_build_unit + la_ls_utinet_bu into a unit dict."""
    geom_3d_wkt = None
    if admin_row and admin_row.geom_3d:
        try:
            geom_3d_wkt = admin_row.geom_3d.wkt
        except Exception:
            pass

    return {
        "su_id":               su_id,
        "apt_name":            admin_row.apt_name            if admin_row else None,
        "floor_no":            admin_row.floor_no            if admin_row else None,
        "floor_area":          float(admin_row.floor_area)   if (admin_row and admin_row.floor_area is not None) else None,
        "postal_ad_build":     admin_row.postal_ad_build     if admin_row else None,
        "house_hold_no":       admin_row.house_hold_no       if admin_row else None,
        "bld_property_type":   admin_row.bld_property_type   if admin_row else None,
        "access_road":         admin_row.access_road         if admin_row else None,
        "wall_type":           admin_row.wall_type           if admin_row else None,
        "roof_type":           admin_row.roof_type           if admin_row else None,
        "hight":               float(admin_row.hight)        if (admin_row and admin_row.hight is not None) else None,
        "surface_relation":    admin_row.surface_relation    if admin_row else None,
        "registration_date":   str(admin_row.registration_date) if (admin_row and admin_row.registration_date) else None,
        "construction_year":   admin_row.construction_year   if admin_row else None,
        "structure_type":      admin_row.structure_type      if admin_row else None,
        "condition":           admin_row.condition           if admin_row else None,
        "ext_builduse_type":   admin_row.ext_builduse_type   if admin_row else None,
        "ext_builduse_sub_type": admin_row.ext_builduse_sub_type if admin_row else None,
        "geom_3d_wkt":         geom_3d_wkt,
        # Utility
        "utility": {
            "water":          util_row.water          if util_row else None,
            "water_drink":    util_row.water_drink    if util_row else None,
            "elec":           util_row.elec           if util_row else None,
            "tele":           util_row.tele           if util_row else None,
            "internet":       util_row.internet       if util_row else None,
            "drainage":       util_row.drainage       if util_row else None,
            "sani_sewer":     util_row.sani_sewer     if util_row else None,
            "sani_gully":     util_row.sani_gully     if util_row else None,
            "garbage_dispose": util_row.garbage_dispose if util_row else None,
        } if util_row else {},
    }


# ─────────────────────────────────────────────────────────────────────────────
#  GET /bld-units/?parent_su_id=<int>  — list all apartment units of a building
# ─────────────────────────────────────────────────────────────────────────────
class Bld_Units_List_View(APIView):
    """Return all layer_id=12 child spatial units for a given parent building su_id.

    Query param:
        parent_su_id  — the su_id of the parent building (required)
    """
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            parent_su_id = request.query_params.get("parent_su_id")
            if not parent_su_id:
                return Response({"error": "parent_su_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                parent_su_id = int(parent_su_id)
            except (ValueError, TypeError):
                return Response({"error": "parent_su_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

            user = request.user
            role_id, err = _get_user_role(user)
            if err:
                return err

            # Query child units: layer_id=12 and parent_id array contains parent_su_id
            child_rows = Survey_Rep_DATA_Model.objects.filter(
                layer_id=12,
                parent_id__contains=[parent_su_id],
            ).values_list("id", flat=True)

            units = []
            for su_id in child_rows:
                admin_row = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
                util_row  = LA_LS_Utinet_BU_Model.objects.filter(su_id=su_id).first()
                units.append(_unit_to_dict(su_id, None, admin_row, util_row))

            return Response({"count": len(units), "units": units}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────────────────────
#  GET /bld-unit/su_id=<int>/  — retrieve a single apartment unit
# ─────────────────────────────────────────────────────────────────────────────
class Bld_Unit_Detail_View(APIView):
    """Return full attribute data for a single apartment unit (layer_id=12)."""
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user
            role_id, err = _get_user_role(user)
            if err:
                return err

            survey_row = Survey_Rep_DATA_Model.objects.filter(id=su_id, layer_id=12).first()
            if not survey_row:
                return Response({"error": "Apartment unit not found."}, status=status.HTTP_404_NOT_FOUND)

            admin_row = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            util_row  = LA_LS_Utinet_BU_Model.objects.filter(su_id=su_id).first()

            return Response(_unit_to_dict(su_id, survey_row, admin_row, util_row), status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /bld-unit/update/su_id=<int>/  — update apartment unit attributes
# ─────────────────────────────────────────────────────────────────────────────
class Bld_Unit_Update_View(APIView):
    """Update admin and/or utility attributes for an apartment unit (layer_id=12).

    Accepts a flat JSON body; fields are permission-gated per UNIT_ADMIN_FIELD_PERM /
    UNIT_UTIL_FIELD_PERM.  A nested ``utility`` sub-object is also accepted and
    will be merged transparently.
    """
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            category = "UNIT"

            role_id, err = _get_user_role(user)
            if err:
                return err

            # Verify this is actually a unit (layer_id=12)
            survey_row = Survey_Rep_DATA_Model.objects.filter(id=su_id, layer_id=12).first()
            if not survey_row:
                return Response({"error": "Apartment unit not found."}, status=status.HTTP_404_NOT_FOUND)

            # Flatten a nested utility block if provided
            flat_data = dict(request.data)
            if "utility" in flat_data and isinstance(flat_data["utility"], dict):
                flat_data.update(flat_data.pop("utility"))

            # ── Admin fields ──────────────────────────────────────────────
            editable_admin = _allowed_fields(role_id, UNIT_ADMIN_FIELD_PERM, mode="edit")
            admin_update = {k: v for k, v in flat_data.items() if k in editable_admin and v not in (None, "")}

            if admin_update:
                admin_row, _ = LA_LS_Build_Unit_Model.objects.get_or_create(su_id_id=su_id)
                original = admin_row.__dict__.copy()
                serializer = LA_LS_Build_Unit_Serializer(admin_row, data=admin_update, partial=True)
                if serializer.is_valid():
                    for attr, value in serializer.validated_data.items():
                        setattr(admin_row, attr, value)
                    admin_row.save(update_fields=list(serializer.validated_data.keys()))
                    self._log(user.id, category, su_id, original, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # ── geom_3d (raw WKT / WKB) ───────────────────────────────────
            if "geom_3d_wkt" in flat_data and flat_data["geom_3d_wkt"]:
                try:
                    geom = GEOSGeometry(flat_data["geom_3d_wkt"], srid=4326)
                    admin_row2, _ = LA_LS_Build_Unit_Model.objects.get_or_create(su_id_id=su_id)
                    admin_row2.geom_3d = geom
                    admin_row2.save(update_fields=["geom_3d"])
                except Exception as geo_err:
                    return Response({"error": f"Invalid geom_3d_wkt: {geo_err}"}, status=status.HTTP_400_BAD_REQUEST)

            # ── Utility fields ────────────────────────────────────────────
            editable_util = _allowed_fields(role_id, UNIT_UTIL_FIELD_PERM, mode="edit")
            util_update = {k: v for k, v in flat_data.items() if k in editable_util and v not in (None, "")}

            if util_update:
                util_row, _ = LA_LS_Utinet_BU_Model.objects.get_or_create(su_id_id=su_id)
                original = util_row.__dict__.copy()
                serializer = Bld_Utinet_info_Serializer(util_row, data=util_update, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    self._log(user.id, category, su_id, original, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Unit data updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _log(self, user_id, category, su_id, original, updated):
        changes = []
        for field, new_value in updated.items():
            old_value = original.get(field)
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
                    field_value=str(new_value),
                ))
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)


# ─────────────────────────────────────────────────────────────────────────────
#  POST /bld-unit/create/  — create a new apartment unit
# ─────────────────────────────────────────────────────────────────────────────
class Bld_Unit_Create_View(APIView):
    """Create a new apartment unit (layer_id=12) as a child of a building.

    Expected JSON body:
        parent_su_id   : int      — su_id of the parent building (required)
        apt_name       : str      — unit label e.g. "3B" (required)
        floor_no       : int      — floor number (required)
        floor_area     : float    — floor area m² (optional)
        geom_3d_wkt    : str      — WKT of 3D solid geometry (optional)
        <any la_ls_build_unit fields>
        utility        : dict     — optional utility fields
    """
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            parent_su_id = data.get("parent_su_id")
            if not parent_su_id:
                return Response({"error": "parent_su_id is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                parent_su_id = int(parent_su_id)
            except (ValueError, TypeError):
                return Response({"error": "parent_su_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

            # Verify parent building exists as layer_id=3
            parent_survey = Survey_Rep_DATA_Model.objects.filter(id=parent_su_id, layer_id=3).first()
            if not parent_survey:
                return Response({"error": f"Parent building su_id={parent_su_id} not found."}, status=status.HTTP_404_NOT_FOUND)

            # ── Create survey_rep record for the new unit ─────────────────
            with transaction.atomic():
                # Inherit gnd_id, geometry and metadata from parent building
                parent_geom_type = (
                    parent_survey.geom.geom_type if parent_survey.geom else "Polygon"
                )
                new_survey = Survey_Rep_DATA_Model(
                    layer_id=12,
                    parent_id=[parent_su_id],
                    gnd_id=parent_survey.gnd_id,
                    org_id=parent_survey.org_id,
                    geom=parent_survey.geom,        # 2D: share parent polygon for now
                    geom_type=parent_geom_type,
                    user_id=request.user.id,
                    status=True,
                )
                new_survey.save()
                new_su_id = new_survey.id

                # ── Ensure la_spatial_unit row exists ─────────────────────
                LA_Spatial_Unit_Model.objects.get_or_create(
                    su_id=new_su_id,
                    defaults={"status": True, "label": data.get("apt_name", ""), "parcel_status": "Active"},
                )

                # ── Create la_ls_build_unit admin row ────────────────────
                admin_fields = {
                    "su_id_id":          new_su_id,
                    "apt_name":          data.get("apt_name"),
                    "floor_no":          data.get("floor_no"),
                    "floor_area":        data.get("floor_area"),
                    "postal_ad_build":   data.get("postal_ad_build"),
                    "house_hold_no":     data.get("house_hold_no"),
                    "bld_property_type": data.get("bld_property_type"),
                    "access_road":       data.get("access_road"),
                    "wall_type":         data.get("wall_type"),
                    "roof_type":         data.get("roof_type"),
                    "hight":             data.get("hight"),
                    "surface_relation":  data.get("surface_relation"),
                    "registration_date": data.get("registration_date"),
                    "construction_year": data.get("construction_year"),
                    "structure_type":    data.get("structure_type"),
                    "condition":         data.get("condition"),
                    "ext_builduse_type": data.get("ext_builduse_type"),
                    "ext_builduse_sub_type": data.get("ext_builduse_sub_type"),
                    "status":            True,
                }
                # 3D geometry
                geom_3d_wkt = data.get("geom_3d_wkt")
                if geom_3d_wkt:
                    try:
                        admin_fields["geom_3d"] = GEOSGeometry(geom_3d_wkt, srid=4326)
                    except Exception:
                        pass  # non-fatal; can be set via PATCH later

                admin_row = LA_LS_Build_Unit_Model(**{k: v for k, v in admin_fields.items() if v is not None})
                admin_row.save()

                # ── Create la_ls_utinet_bu row if utility provided ────────
                utility = data.get("utility", {})
                if utility:
                    util_row = LA_LS_Utinet_BU_Model(
                        su_id_id=new_su_id,
                        water=utility.get("water"),
                        water_drink=utility.get("water_drink"),
                        elec=utility.get("elec"),
                        tele=utility.get("tele"),
                        internet=utility.get("internet"),
                        drainage=utility.get("drainage"),
                        sani_sewer=utility.get("sani_sewer"),
                        sani_gully=utility.get("sani_gully"),
                        garbage_dispose=utility.get("garbage_dispose"),
                        status=True,
                    )
                    util_row.save()

            return Response(
                {"su_id": new_su_id, "parent_su_id": parent_su_id, "detail": "Apartment unit created successfully."},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
