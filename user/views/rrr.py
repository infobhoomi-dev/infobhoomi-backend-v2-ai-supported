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

# ─────────────────────────────────────────────────────────────────────────────
# RRR Role-Based Permission Helpers (re-imported here for local use)
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


#________________________________________________ RRR Data Save View ____________________________________________________________
class RRR_Data_Save_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            user_obj = request.user
            user_id = user_obj.id

            data = request.data.copy()
            file = request.FILES.get('file')

            # Permission gate
            su_id = data.get('su_id')
            if su_id:
                perm_id = _rrr_perm_for_su(su_id)
                if not _has_rrr_perm(user_id, perm_id, 'add'):
                    return _rrr_permission_denied()

            # Parse "parties" JSON string if needed
            parties = data.get('parties', [])
            if isinstance(parties, str):
                try:
                    parties = json.loads(parties)
                except json.JSONDecodeError:
                    return Response(
                        {"error": "Invalid JSON format for 'parties' field"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 1 Create BA Unit
            ba_unit = SL_BA_Unit_Model.objects.create(
                su_id_id=data['su_id'],
                sl_ba_unit_name=data['sl_ba_unit_name'],
                sl_ba_unit_type=data['sl_ba_unit_type'],
            )

            # 2 Create Admin Source (file later)
            admin_source = LA_Admin_Source_Model.objects.create(
                admin_source_type=data['admin_source_type'],
                done_by=user_id,
                user_id=user_id,
                file_path=None
            )

            # 3 Save File with Renaming
            if file:
                folder_path = 'documents/admin_source'
                _, ext = os.path.splitext(file.name)
                new_filename = f"{admin_source.admin_source_id}{ext or '.bin'}"
                full_path = os.path.join(folder_path, new_filename)

                # Assign string directly — do NOT use .file_path.name = ...
                # (file_path was created as None; FieldFile.name assignment is unreliable)
                saved_path = default_storage.save(full_path, ContentFile(file.read()))
                admin_source.file_path = saved_path
                admin_source.save()

            # 4 Create RRR + Party Roles
            created_rrrs = []
            for party in parties:
                rrr = LA_RRR_Model.objects.create(
                    ba_unit_id=ba_unit,
                    admin_source_id=admin_source,
                    pid_id=party['pid'],
                    rrr_type=party.get('rrr_type'),
                    time_begin=party.get('time_begin') or None,
                    time_end=party.get('time_end') or None,
                    description=party.get('description'),
                )
                created_rrrs.append(rrr.rrr_id)

                Party_Roles_Model.objects.create(
                    pid_id=party['pid'],
                    rrr_id=rrr,
                    party_role_type=party['party_role_type'],
                    share_type=party.get('share_type'),
                    share=party.get('share'),
                    done_by=user_id
                )

            return Response({
                "message": "BA Unit data saved successfully",
                "ba_unit_id": ba_unit.ba_unit_id,
                "admin_source_id": admin_source.admin_source_id,
                "created_rrr_ids": created_rrrs,
                "file_saved_as": admin_source.file_path.name if admin_source.file_path else None
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#_______________________________________________ RRR Add/Remove Extra Document Views ___________________________________________________
class RRR_Add_Document_View(APIView):
    """POST /api/user/rrr-add-document/ba_unit_id=<int>/ — upload an extra document to an existing BA unit."""
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, ba_unit_id):
        perm_id = _rrr_perm_for_ba(ba_unit_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()
        try:
            ba_unit = SL_BA_Unit_Model.objects.get(ba_unit_id=ba_unit_id)
        except SL_BA_Unit_Model.DoesNotExist:
            return Response({"error": "BA Unit not found"}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get('file')
        admin_source_type = request.data.get('admin_source_type', 'Document')

        admin_source = LA_Admin_Source_Model.objects.create(
            admin_source_type=admin_source_type,
            done_by=request.user.id,
            user_id=request.user.id,
            file_path=None,
        )

        if file:
            folder_path = 'documents/admin_source'
            _, ext = os.path.splitext(file.name)
            new_filename = f"{admin_source.admin_source_id}{ext or '.bin'}"
            saved_path = default_storage.save(
                os.path.join(folder_path, new_filename), ContentFile(file.read())
            )
            admin_source.file_path = saved_path
            admin_source.save()

        doc_link = LA_RRR_Document_Model.objects.create(
            ba_unit=ba_unit,
            admin_source=admin_source,
        )

        file_url = request.build_absolute_uri(
            f"/api/user/admin-source/file/{admin_source.admin_source_id}/"
        ) if admin_source.file_path else None

        return Response({
            "doc_link_id": doc_link.id,
            "admin_source_id": admin_source.admin_source_id,
            "admin_source_type": admin_source.admin_source_type,
            "file_url": file_url,
        }, status=status.HTTP_201_CREATED)


class RRR_Remove_Document_View(APIView):
    """DELETE /api/user/rrr-remove-document/<id>/ — remove an extra document link and its admin source."""
    http_method_names = ['delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, doc_link_id):
        try:
            doc_link = LA_RRR_Document_Model.objects.select_related('admin_source', 'ba_unit').get(id=doc_link_id)
        except LA_RRR_Document_Model.DoesNotExist:
            return Response({"error": "Document link not found"}, status=status.HTTP_404_NOT_FOUND)

        perm_id = _rrr_perm_for_ba(doc_link.ba_unit_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()

        admin_source = doc_link.admin_source
        doc_link.delete()
        if admin_source:
            if admin_source.file_path:
                default_storage.delete(admin_source.file_path.name)
            admin_source.delete()

        return Response({"message": "Document removed successfully"}, status=status.HTTP_200_OK)


#------------------------------------------------------------------------------
class RRR_Data_get_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        su_id = request.query_params.get('su_id')
        if not su_id:
            return Response({"error": "su_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Permission gate
        perm_id = _rrr_perm_for_su(su_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'view'):
            return _rrr_permission_denied()

        # get parent_id from Survey_Rep_DATA_Model
        survey_data = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).values("parent_id").first()
        parent_id_value = survey_data["parent_id"] if survey_data else None


        try:
            ba_units = SL_BA_Unit_Model.objects.filter(su_id_id=su_id, status=True).order_by('-ba_unit_id')
            response_data = []

            for ba_unit in ba_units:
                rrrs = LA_RRR_Model.objects.filter(ba_unit_id=ba_unit).select_related('admin_source_id', 'pid')

                admin_sources = []
                seen_admin_source_ids = set()
                rrr_list = []

                for rrr in rrrs:
                    # Primary doc (from LA_RRR_Model.admin_source_id)
                    admin_source = rrr.admin_source_id
                    if admin_source and admin_source.admin_source_id not in seen_admin_source_ids:
                        seen_admin_source_ids.add(admin_source.admin_source_id)
                        file_url = request.build_absolute_uri(
                            f"/api/user/admin-source/file/{admin_source.admin_source_id}/"
                        ) if admin_source.file_path else None
                        admin_sources.append({
                            "admin_source_id": admin_source.admin_source_id,
                            "admin_source_type": admin_source.admin_source_type,
                            "file_url": file_url,
                            "doc_link_id": None,  # primary doc has no link id
                        })

                    # Build rrr_list entry here (inside for rrr loop, NOT inside for doc_link loop)
                    party_role = Party_Roles_Model.objects.filter(rrr_id=rrr).first()
                    party_role_type = party_role.party_role_type if party_role else None

                    restrictions = LA_RRR_Restriction_Model.objects.filter(rrr_id=rrr).values(
                        'id', 'rrr_restriction_type', 'description', 'time_begin', 'time_end'
                    )
                    responsibilities = LA_RRR_Responsibility_Model.objects.filter(rrr_id=rrr).values(
                        'id', 'rrr_responsibility_type', 'description', 'time_begin', 'time_end'
                    )

                    rrr_list.append({
                        "rrr_id": rrr.rrr_id,
                        "pid": rrr.pid_id,
                        "party_name": rrr.pid.party_full_name if rrr.pid else None,
                        "share_type": party_role.share_type if party_role else None,
                        "share": float(party_role.share) if party_role and party_role.share is not None else None,
                        "party_role_type": party_role_type,
                        "rrr_type": rrr.rrr_type,
                        "time_begin": str(rrr.time_begin) if rrr.time_begin else None,
                        "time_end": str(rrr.time_end) if rrr.time_end else None,
                        "description": rrr.description,
                        "restrictions": [
                            {**r, "time_begin": str(r["time_begin"]) if r["time_begin"] else None,
                                  "time_end": str(r["time_end"]) if r["time_end"] else None}
                            for r in restrictions
                        ],
                        "responsibilities": [
                            {**r, "time_begin": str(r["time_begin"]) if r["time_begin"] else None,
                                  "time_end": str(r["time_end"]) if r["time_end"] else None}
                            for r in responsibilities
                        ],
                    })

                # Additional docs (from LA_RRR_Document_Model linked to this BA unit)
                for doc_link in LA_RRR_Document_Model.objects.filter(ba_unit=ba_unit).select_related('admin_source'):
                    as2 = doc_link.admin_source
                    if as2.admin_source_id not in seen_admin_source_ids:
                        seen_admin_source_ids.add(as2.admin_source_id)
                        file_url2 = request.build_absolute_uri(
                            f"/api/user/admin-source/file/{as2.admin_source_id}/"
                        ) if as2.file_path else None
                        admin_sources.append({
                            "admin_source_id": as2.admin_source_id,
                            "admin_source_type": as2.admin_source_type,
                            "file_url": file_url2,
                            "doc_link_id": doc_link.id,
                        })

                response_data.append({
                    "ba_unit_id": ba_unit.ba_unit_id,
                    "sl_ba_unit_name": ba_unit.sl_ba_unit_name,
                    "sl_ba_unit_type": ba_unit.sl_ba_unit_type,
                    "admin_sources": admin_sources,
                    "rrrs": rrr_list
                })

            # return Response(result, status=status.HTTP_200_OK)
            return Response({
                "history_su_id": parent_id_value,
                "records": response_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#________________________________________________ SL_BA_Unit update View ________________________________________________________
class SL_BA_Unit_Update_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch']

    def patch(self, request, ba_unit_id):
        # Permission gate
        perm_id = _rrr_perm_for_ba(ba_unit_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()

        try:
            ba_unit = SL_BA_Unit_Model.objects.get(ba_unit_id=ba_unit_id)
        except SL_BA_Unit_Model.DoesNotExist:
            return Response({"error": "BA Unit not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = SL_BA_Unit_Serializer(ba_unit, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#________________________________________________ RRR Update View (PATCH existing entry) _______________________________________
class RRR_Update_View(APIView):
    """PATCH /api/user/rrr/update/<ba_unit_id>/
    Updates an existing LADM RRR entry:
      - SL_BA_Unit_Model (name, type)
      - LA_RRR_Model (time_begin, time_end, description, rrr_type)
      - Party_Roles_Model (share, share_type, party_role_type)
      - LA_Admin_Source_Model (admin_source_type; optional file replacement)
    """
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, ba_unit_id):
        # Permission gate
        perm_id = _rrr_perm_for_ba(ba_unit_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()

        try:
            ba_unit = SL_BA_Unit_Model.objects.get(ba_unit_id=ba_unit_id)
        except SL_BA_Unit_Model.DoesNotExist:
            return Response({"error": "BA Unit not found"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data

        # --- Update BA Unit ---
        ba_fields = {}
        if 'sl_ba_unit_name' in data:
            ba_fields['sl_ba_unit_name'] = data['sl_ba_unit_name']
        if 'sl_ba_unit_type' in data:
            ba_fields['sl_ba_unit_type'] = data['sl_ba_unit_type']
        if ba_fields:
            for k, v in ba_fields.items():
                setattr(ba_unit, k, v)
            ba_unit.save()

        # --- Update primary RRR record ---
        rrr = LA_RRR_Model.objects.filter(ba_unit_id=ba_unit).first()
        if rrr:
            rrr_fields = {}
            if 'time_begin' in data:
                rrr_fields['time_begin'] = data['time_begin'] or None
            if 'time_end' in data:
                rrr_fields['time_end'] = data['time_end'] or None
            if 'description' in data:
                rrr_fields['description'] = data['description'] or None
            if 'rrr_type' in data:
                rrr_fields['rrr_type'] = data['rrr_type']
            if rrr_fields:
                for k, v in rrr_fields.items():
                    setattr(rrr, k, v)
                rrr.save()

            # --- Update party role ---
            party_role = Party_Roles_Model.objects.filter(rrr_id=rrr).first()
            if party_role:
                pr_fields = {}
                if 'share' in data:
                    pr_fields['share'] = data['share']
                if 'share_type' in data:
                    pr_fields['share_type'] = data['share_type']
                if 'party_role_type' in data:
                    pr_fields['party_role_type'] = data['party_role_type']
                if pr_fields:
                    for k, v in pr_fields.items():
                        setattr(party_role, k, v)
                    party_role.save()

            # --- Update admin source type / replace file ---
            admin_source = rrr.admin_source_id
            if admin_source:
                if 'admin_source_type' in data:
                    admin_source.admin_source_type = data['admin_source_type']
                    admin_source.save()

                file = request.FILES.get('file')
                if file:
                    if admin_source.file_path:
                        try:
                            default_storage.delete(admin_source.file_path.name)
                        except Exception:
                            pass
                    folder_path = 'documents/admin_source'
                    _, ext = os.path.splitext(file.name)
                    new_filename = f"{admin_source.admin_source_id}{ext or '.bin'}"
                    saved_path = default_storage.save(
                        os.path.join(folder_path, new_filename), ContentFile(file.read())
                    )
                    admin_source.file_path = saved_path
                    admin_source.save()

        return Response({"message": "RRR entry updated successfully"}, status=status.HTTP_200_OK)
