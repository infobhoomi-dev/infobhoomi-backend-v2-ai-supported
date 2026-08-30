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
    sr = Survey_Rep_DATA_Model.objects.filter(id=su_id).values('layer_id').first()
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


from ..utils import (
    has_perm as _has_rrr_perm,
    perm_denied as _rrr_permission_denied,
    record_history as _record_history,
)  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Issue #8: RRR Audit Helper
# ─────────────────────────────────────────────────────────────────────────────
def _normal_history_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return None if cleaned.lower() in ('', 'none', 'null', 'undefined') else cleaned
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def _snapshot_changes(before, after, prefix=''):
    changed = []
    before = before or {}
    after = after or {}
    for key in sorted(set(before.keys()) | set(after.keys())):
        old = before.get(key)
        new = after.get(key)
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(old, dict) or isinstance(new, dict):
            changed.extend(_snapshot_changes(old or {}, new or {}, path))
        elif _normal_history_value(old) != _normal_history_value(new):
            changed.append(path)
    return changed


def _rrr_document_snapshot(ba_unit):
    if not ba_unit:
        return []

    docs = []
    primary_ids = set()
    for rrr in LA_RRR_Model.objects.filter(ba_unit_id=ba_unit).select_related('admin_source_id'):
        admin_source = rrr.admin_source_id
        if not admin_source or not admin_source.status:
            continue
        primary_ids.add(admin_source.admin_source_id)
        docs.append({
            'source': 'primary',
            'rrr_id': rrr.rrr_id,
            'admin_source_id': admin_source.admin_source_id,
            'admin_source_type': admin_source.admin_source_type,
            'file_name': os.path.basename(admin_source.file_path.name) if admin_source.file_path else None,
            'active': True,
        })

    for doc_link in LA_RRR_Document_Model.objects.filter(ba_unit=ba_unit).select_related('admin_source'):
        admin_source = doc_link.admin_source
        if not admin_source or not admin_source.status:
            continue
        if admin_source.admin_source_id in primary_ids:
            continue
        docs.append({
            'source': 'extra',
            'doc_link_id': doc_link.id,
            'admin_source_id': admin_source.admin_source_id,
            'admin_source_type': admin_source.admin_source_type,
            'file_name': os.path.basename(admin_source.file_path.name) if admin_source.file_path else None,
            'active': True,
        })
    return docs


def _build_rrr_snapshot(rrr):
    parties = [
        {
            'pid_id': p['pid_id'],
            'party_role_type': p['party_role_type'],
            'share': _normal_history_value(p['share']),
            'share_type': p['share_type'],
        }
        for p in Party_Roles_Model.objects.filter(rrr_id=rrr).values(
            'pid_id', 'party_role_type', 'share', 'share_type'
        )
    ]
    mortgage_snap = None
    try:
        m = rrr.mortgage
        mortgage_snap = {
            'amount': _normal_history_value(m.amount),
            'interest': _normal_history_value(m.interest),
            'ranking': m.ranking,
            'mortgage_type': m.mortgage_type,
            'mortgage_ref_id': m.mortgage_ref_id,
            'mortgagee': m.mortgagee,
        }
    except LA_Mortgage_Model.DoesNotExist:
        pass
    return {
        'rrr_type': rrr.rrr_type,
        'time_begin': str(rrr.time_begin) if rrr.time_begin else None,
        'time_end': str(rrr.time_end) if rrr.time_end else None,
        'description': rrr.description,
        'status': rrr.status,
        'parties': parties,
        'mortgage': mortgage_snap,
        'documents': _rrr_document_snapshot(rrr.ba_unit_id),
    }


def _write_rrr_audit(rrr, action, user_id, user_name='', su_id=None, before_snapshot=None, changed_fields=None):
    """Write one row to la_rrr_audit capturing the full RRR state at this moment."""
    # Snapshot parties — convert Decimal share to str for JSON serialization
    parties = [
        {
            'pid_id':          p['pid_id'],
            'party_role_type': p['party_role_type'],
            'share':           _normal_history_value(p['share']),
            'share_type':      p['share_type'],
        }
        for p in Party_Roles_Model.objects.filter(rrr_id=rrr).values(
            'pid_id', 'party_role_type', 'share', 'share_type'
        )
    ]
    # Snapshot mortgage (if any)
    mortgage_snap = None
    try:
        m = rrr.mortgage
        mortgage_snap = {
            'amount':          _normal_history_value(m.amount),
            'interest':        _normal_history_value(m.interest),
            'ranking':         m.ranking,
            'mortgage_type':   m.mortgage_type,
            'mortgage_ref_id': m.mortgage_ref_id,
            'mortgagee':       m.mortgagee,
        }
    except LA_Mortgage_Model.DoesNotExist:
        pass

    # Resolve su_id if not provided
    if su_id is None:
        try:
            su_id = rrr.ba_unit_id.su_id_id
        except Exception:
            su_id = None

    snapshot = {
        'rrr_type':    rrr.rrr_type,
        'time_begin':  str(rrr.time_begin) if rrr.time_begin else None,
        'time_end':    str(rrr.time_end) if rrr.time_end else None,
        'description': rrr.description,
        'status':      rrr.status,
        'parties':     parties,
        'mortgage':    mortgage_snap,
        'documents':   _rrr_document_snapshot(rrr.ba_unit_id),
    }
    changed_fields = changed_fields if changed_fields is not None else _snapshot_changes(before_snapshot, snapshot)

    # ─── Determine Event Type and Change Summary ───
    primary_pr = Party_Roles_Model.objects.select_related('pid').filter(rrr_id=rrr).first()
    holder_name = (primary_pr.pid.party_full_name or primary_pr.pid.party_name) if (primary_pr and primary_pr.pid) else "Unknown"

    if action == LA_RRR_Audit_Model.CREATE:
        event_type = "rrr_created"
        change_summary = f"Right holder added: {holder_name} (Right Type: {rrr.rrr_type}, Share: {primary_pr.share if primary_pr else 0}%)"
    elif action == LA_RRR_Audit_Model.TERMINATE:
        event_type = "rrr_terminated"
        change_summary = f"Right terminated: {holder_name} ({rrr.rrr_type})"
    else: # UPDATE
        event_type = "rrr_modified"
        document_field = next(
            (
                field for field in changed_fields
                if str(field).startswith('document added:') or str(field).startswith('document removed:')
            ),
            None,
        )
        if document_field:
            document_text = str(document_field)
            event_type = 'rrr_document_added' if document_text.startswith('document added:') else 'rrr_document_removed'
            change_summary = document_text[0].upper() + document_text[1:]
            snapshot['document_event'] = document_text
        else:
            changes = []
            if before_snapshot:
                if before_snapshot.get('rrr_type') != snapshot.get('rrr_type'):
                    changes.append(f"Right type changed to {snapshot.get('rrr_type')}")
                if before_snapshot.get('time_begin') != snapshot.get('time_begin') or before_snapshot.get('time_end') != snapshot.get('time_end'):
                    from_date = snapshot.get('time_begin') or 'N/A'
                    to_date = snapshot.get('time_end') or 'lifetime'
                    changes.append(f"Validity period updated ({from_date} to {to_date})")
                if before_snapshot.get('description') != snapshot.get('description'):
                    changes.append("Description updated")

                # Party share compare
                before_parties = before_snapshot.get('parties') or []
                after_parties = snapshot.get('parties') or []
                if before_parties and after_parties:
                    old_share = before_parties[0].get('share')
                    new_share = after_parties[0].get('share')
                    if old_share != new_share:
                        changes.append(f"Share updated to {new_share}%")

                # Mortgage compare
                before_mortgage = before_snapshot.get('mortgage') or {}
                after_mortgage = snapshot.get('mortgage') or {}
                if before_mortgage != after_mortgage:
                    changes.append("Mortgage details updated")

            if changes:
                change_summary = f"RRR updated: {', '.join(changes)}"
            else:
                change_summary = f"RRR {rrr.rrr_id} updated"

    # Inject event_type into snapshot
    snapshot['event_type'] = event_type

    audit = LA_RRR_Audit_Model.objects.create(
        rrr_id=rrr.rrr_id,
        ba_unit_id=rrr.ba_unit_id_id,
        su_id=su_id,
        action=action,
        changed_by=user_id,
        changed_by_name=user_name,
        snapshot=snapshot,
    )
    if su_id:
        _record_history(
            su_id=su_id,
            record_type=Parcel_History_Model.RECORD_RRR,
            action=action.lower(),
            user=User.objects.filter(id=user_id).first(),
            category='RRR',
            field_name='rrr',
            old_value=before_snapshot,
            new_value=snapshot,
            change_summary=change_summary,
            snapshot={
                'audit_id': audit.id,
                'rrr_id': rrr.rrr_id,
                'ba_unit_id': rrr.ba_unit_id_id,
                'action': action,
                'event_type': event_type,
                'snapshot': snapshot,
                'before_snapshot': before_snapshot,
                'changed_fields': changed_fields,
                'parties': parties,
                'mortgage': mortgage_snap,
            },
            can_restore=(action in {
                LA_RRR_Audit_Model.CREATE,
                LA_RRR_Audit_Model.UPDATE,
                LA_RRR_Audit_Model.TERMINATE,
            }),
        )


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

            # Frontend sends the party list under "rights" (not "parties").
            # Parse it — it may arrive as a JSON string when sent via FormData.
            rights = data.get('rights', [])
            if isinstance(rights, str):
                try:
                    rights = json.loads(rights)
                except json.JSONDecodeError:
                    return Response(
                        {"error": "Invalid JSON format for 'rights' field"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if not rights:
                return Response(
                    {"error": "'rights' must contain at least one party."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 1 Resolve BA Unit (Issue #5 fix — Option A)
            # Each title transaction gets its own BA unit (ownership deed, mortgage, etc.).
            # If the frontend sends an existing ba_unit_id, reuse it (same transaction,
            # e.g. adding another party to an existing deed). This also prevents accidental
            # duplicates when the user clicks Save twice — the second request carries the
            # ba_unit_id returned by the first and hits the existing record.
            # If ba_unit_id is absent or null → new transaction → create a new BA unit.
            existing_ba_unit_id = data.get('ba_unit_id')
            if existing_ba_unit_id:
                try:
                    ba_unit = SL_BA_Unit_Model.objects.get(
                        ba_unit_id=existing_ba_unit_id, status=True
                    )
                except SL_BA_Unit_Model.DoesNotExist:
                    return Response(
                        {"error": f"BA unit {existing_ba_unit_id} not found or inactive."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Frontend sends: code → sl_ba_unit_name, la_ba_unit_type → sl_ba_unit_type
                ba_unit = SL_BA_Unit_Model.objects.create(
                    su_id_id=data['su_id'],
                    sl_ba_unit_name=data.get('code', ''),
                    sl_ba_unit_type=data.get('la_ba_unit_type', 'basicPropertyUnit'),
                )

            # 2 Create Admin Source (file attached later)
            admin_source = LA_Admin_Source_Model.objects.create(
                admin_source_type=data['admin_source_type'],
                reference_no=data.get('reference_no') or None,
                acceptance_date=data.get('acceptance_date') or None,
                exte_arch_ref=data.get('exte_arch_ref') or None,
                source_description=data.get('source_description') or None,
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

            # 4 Create ONE la_rrr for this right (Issue #2 fix).
            # RRR-level fields (right_type, dates, description) are shared across all
            # parties in one transaction — take them from the first entry.
            # Frontend field mapping: right_type → rrr_type, date_start → time_begin,
            #                         date_end → time_end
            first = rights[0]
            rrr = LA_RRR_Model.objects.create(
                ba_unit_id=ba_unit,
                admin_source_id=admin_source,
                rrr_type=first.get('right_type'),
                time_begin=first.get('date_start') or None,
                time_end=first.get('date_end') or None,
                description=first.get('description'),
            )

            # 4b Create LA_Mortgage_Model record if this is a mortgage right (Issue #6 fix).
            mortgage_data = data.get('mortgage')
            if mortgage_data and (first.get('right_type') or '').lower() == 'mortgage':
                LA_Mortgage_Model.objects.create(
                    rrr_id=rrr,
                    amount=mortgage_data.get('amount') or None,
                    interest=mortgage_data.get('interest') or None,
                    ranking=mortgage_data.get('ranking') or None,
                    mortgage_type=mortgage_data.get('mortgage_type') or None,
                    mortgage_ref_id=mortgage_data.get('mortgage_ref_id') or None,
                    mortgagee=mortgage_data.get('mortgagee') or None,
                )

            # 5 Create one Party_Roles row per party, all linked to the same RRR.
            # Frontend field mapping: party → pid_id, right_type used as party_role_type.
            for right in rights:
                Party_Roles_Model.objects.create(
                    pid_id=right['party'],
                    rrr_id=rrr,
                    party_role_type=right.get('right_type', ''),
                    share_type=right.get('share_type'),
                    share=right.get('share'),
                    done_by=user_id
                )

            # 6 Write audit record (Issue #8)
            user_name = f"{user_obj.first_name} {user_obj.last_name}".strip() or user_obj.username
            _write_rrr_audit(rrr, LA_RRR_Audit_Model.CREATE, user_id, user_name, su_id=data.get('su_id'))

            return Response({
                "message": "BA Unit data saved successfully",
                "ba_unit_id": ba_unit.ba_unit_id,
                "admin_source_id": admin_source.admin_source_id,
                "rrr_id": rrr.rrr_id,
                "created_rrr_ids": [rrr.rrr_id],
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

        rrr = LA_RRR_Model.objects.filter(ba_unit_id=ba_unit).order_by('rrr_id').first()
        before_snapshot = _build_rrr_snapshot(rrr) if rrr else None
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

        if rrr:
            user = request.user
            user_name = f"{user.first_name} {user.last_name}".strip() or user.username
            doc_name = file.name if file else admin_source_type
            _write_rrr_audit(
                rrr,
                LA_RRR_Audit_Model.UPDATE,
                user.id,
                user_name,
                su_id=ba_unit.su_id_id,
                before_snapshot=before_snapshot,
                changed_fields=[f"document added: {doc_name}"],
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

        rrr = LA_RRR_Model.objects.filter(ba_unit_id=doc_link.ba_unit).order_by('rrr_id').first()
        before_snapshot = _build_rrr_snapshot(rrr) if rrr else None
        admin_source = doc_link.admin_source
        doc_name = None
        if admin_source:
            doc_name = os.path.basename(admin_source.file_path.name) if admin_source.file_path else admin_source.admin_source_type
            admin_source.status = False
            admin_source.save(update_fields=['status'])

        if rrr:
            user = request.user
            user_name = f"{user.first_name} {user.last_name}".strip() or user.username
            _write_rrr_audit(
                rrr,
                LA_RRR_Audit_Model.UPDATE,
                user.id,
                user_name,
                su_id=doc_link.ba_unit.su_id_id,
                before_snapshot=before_snapshot,
                changed_fields=[f"document removed: {doc_name or doc_link_id}"],
            )

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
        survey_data = Survey_Rep_DATA_Model.objects.filter(id=su_id).values("parent_id").first()
        parent_id_value = survey_data["parent_id"] if survey_data else None


        try:
            ba_units = SL_BA_Unit_Model.objects.filter(su_id_id=su_id, status=True).order_by('-ba_unit_id')
            response_data = []

            for ba_unit in ba_units:
                rrrs = LA_RRR_Model.objects.filter(ba_unit_id=ba_unit, status=True).select_related('admin_source_id')

                admin_sources = []
                seen_admin_source_ids = set()
                rrr_list = []

                for rrr in rrrs:
                    # Primary doc (from LA_RRR_Model.admin_source_id)
                    admin_source = rrr.admin_source_id
                    if (
                        admin_source
                        and admin_source.status
                        and admin_source.file_path
                        and admin_source.admin_source_id not in seen_admin_source_ids
                    ):
                        seen_admin_source_ids.add(admin_source.admin_source_id)
                        file_url = request.build_absolute_uri(
                            f"/api/user/admin-source/file/{admin_source.admin_source_id}/"
                        ) if admin_source.file_path else None
                        admin_sources.append({
                            "admin_source_id": admin_source.admin_source_id,
                            "admin_source_type": admin_source.admin_source_type,
                            "reference_no": admin_source.reference_no,
                            "acceptance_date": str(admin_source.acceptance_date) if admin_source.acceptance_date else None,
                            "exte_arch_ref": admin_source.exte_arch_ref,
                            "source_description": admin_source.source_description,
                            "file_url": file_url,
                            "doc_link_id": None,  # primary doc has no link id
                        })

                    # All party roles for this RRR (Issue #2: one rrr, many parties)
                    party_roles = Party_Roles_Model.objects.select_related('pid').filter(rrr_id=rrr)
                    parties_list = [
                        {
                            "pid": pr.pid_id,
                            "party_name": pr.pid.party_full_name if pr.pid else None,
                            "share_type": pr.share_type,
                            "share": float(pr.share) if pr.share is not None else None,
                            "party_role_type": pr.party_role_type,
                        }
                        for pr in party_roles
                    ]

                    # Issue #6: include mortgage details when present
                    mortgage_obj = None
                    try:
                        m = rrr.mortgage  # OneToOne reverse accessor
                        mortgage_obj = {
                            "amount": float(m.amount) if m.amount is not None else None,
                            "interest": float(m.interest) if m.interest is not None else None,
                            "ranking": m.ranking,
                            "mortgage_type": m.mortgage_type,
                            "mortgage_ref_id": m.mortgage_ref_id,
                            "mortgagee": m.mortgagee,
                        }
                    except LA_Mortgage_Model.DoesNotExist:
                        pass

                    rrr_list.append({
                        "rrr_id": rrr.rrr_id,
                        "rrr_type": rrr.rrr_type,
                        "time_begin": str(rrr.time_begin) if rrr.time_begin else None,
                        "time_end": str(rrr.time_end) if rrr.time_end else None,
                        "description": rrr.description,
                        "status": rrr.status,
                        "parties": parties_list,
                        "mortgage": mortgage_obj,
                    })

                # Additional docs (from LA_RRR_Document_Model linked to this BA unit)
                for doc_link in LA_RRR_Document_Model.objects.filter(
                    ba_unit=ba_unit,
                    admin_source__status=True,
                ).select_related('admin_source'):
                    as2 = doc_link.admin_source
                    if as2.file_path and as2.admin_source_id not in seen_admin_source_ids:
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

                # Restrictions and responsibilities are per-property (BA unit), not per-right.
                ba_restrictions = LA_RRR_Restriction_Model.objects.filter(ba_unit_id=ba_unit).values(
                    'id', 'rrr_restriction_type', 'description', 'time_begin', 'time_end'
                )
                ba_responsibilities = LA_RRR_Responsibility_Model.objects.filter(ba_unit_id=ba_unit).values(
                    'id', 'rrr_responsibility_type', 'description', 'time_begin', 'time_end'
                )

                response_data.append({
                    "ba_unit_id": ba_unit.ba_unit_id,
                    "sl_ba_unit_name": ba_unit.sl_ba_unit_name,
                    "sl_ba_unit_type": ba_unit.sl_ba_unit_type,
                    "admin_sources": admin_sources,
                    "rrrs": rrr_list,
                    "restrictions": [
                        {**r, "time_begin": str(r["time_begin"]) if r["time_begin"] else None,
                              "time_end": str(r["time_end"]) if r["time_end"] else None}
                        for r in ba_restrictions
                    ],
                    "responsibilities": [
                        {**r, "time_begin": str(r["time_begin"]) if r["time_begin"] else None,
                              "time_end": str(r["time_end"]) if r["time_end"] else None}
                        for r in ba_responsibilities
                    ],
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
            before_snapshot = _build_rrr_snapshot(rrr)
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
                as_fields = {}
                for field in ('admin_source_type', 'reference_no', 'exte_arch_ref', 'source_description'):
                    if field in data:
                        as_fields[field] = data[field] or None
                if 'acceptance_date' in data:
                    as_fields['acceptance_date'] = data['acceptance_date'] or None
                if as_fields:
                    for k, v in as_fields.items():
                        setattr(admin_source, k, v)
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

            after_snapshot = _build_rrr_snapshot(rrr)
            changed_fields = _snapshot_changes(before_snapshot, after_snapshot)
            if changed_fields:
                user = request.user
                user_name = f"{user.first_name} {user.last_name}".strip() or user.username
                _write_rrr_audit(
                    rrr,
                    LA_RRR_Audit_Model.UPDATE,
                    user.id,
                    user_name,
                    su_id=ba_unit.su_id_id,
                    before_snapshot=before_snapshot,
                    changed_fields=changed_fields,
                )

        return Response({"message": "RRR entry updated successfully"}, status=status.HTTP_200_OK)


#________________________________________________ RRR Terminate View (Issue #8) ________________________________________________
class RRR_Terminate_View(APIView):
    """PATCH /api/user/rrr-terminate/<rrr_id>/ — soft-delete a right and write an audit record."""
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, rrr_id):
        try:
            rrr = LA_RRR_Model.objects.select_related('ba_unit_id').get(rrr_id=rrr_id)
        except LA_RRR_Model.DoesNotExist:
            return Response({"error": "RRR not found."}, status=status.HTTP_404_NOT_FOUND)

        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()

        if not rrr.status:
            return Response({"error": "RRR is already terminated."}, status=status.HTTP_400_BAD_REQUEST)

        rrr.status = False
        rrr.save()

        user = request.user
        user_name = f"{user.first_name} {user.last_name}".strip() or user.username
        su_id = rrr.ba_unit_id.su_id_id if rrr.ba_unit_id else None
        _write_rrr_audit(rrr, LA_RRR_Audit_Model.TERMINATE, user.id, user_name, su_id=su_id)

        return Response({"message": "RRR terminated successfully."}, status=status.HTTP_200_OK)


#________________________________________________ RRR Audit History View (Issue #8) ____________________________________________
class RRR_Audit_History_View(APIView):
    """GET /api/user/rrr-history/?su_id=<n> — return the full audit log for a parcel."""
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        su_id = request.query_params.get('su_id')
        if not su_id:
            return Response({"error": "su_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        perm_id = _rrr_perm_for_su(su_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'view'):
            return _rrr_permission_denied()

        records = list(
            LA_RRR_Audit_Model.objects.filter(su_id=su_id).values(
                'id', 'rrr_id', 'ba_unit_id', 'action',
                'changed_by', 'changed_by_name', 'changed_at', 'snapshot'
            )
        )
        return Response(records, status=status.HTTP_200_OK)


#________________________________________________ Activity Log — Rights / Responsibilities / Mortgages ________________
# Tier 3 of the Activity Log chip audit: these three chips have no data of their
# own — they're views over la_rrr_audit (the same table RRR_Audit_History_View
# already reads), narrowed to "my" changes and flattened to the flat row shape
# the frontend table expects. One shared helper avoids writing the same
# party-name resolution and su_id/rrr_id/action query three times.

def _rrr_activity_rows(user_id, snapshot_filter=None):
    """CREATE/UPDATE audit rows the given user made, newest first, with party
    pids already resolved to display names."""
    qs = LA_RRR_Audit_Model.objects.filter(
        changed_by=user_id,
        action__in=[LA_RRR_Audit_Model.CREATE, LA_RRR_Audit_Model.UPDATE],
    )
    if snapshot_filter:
        qs = qs.filter(**snapshot_filter)
    rows = list(qs.order_by('-changed_at').values(
        'su_id', 'rrr_id', 'action', 'changed_at', 'snapshot'
    ))

    party_ids = {
        p.get('pid_id')
        for r in rows
        for p in (r['snapshot'] or {}).get('parties') or []
        if p.get('pid_id') is not None
    }
    party_names = dict(
        Party_Model.objects.filter(pid__in=party_ids).values_list(
            'pid', 'party_full_name'
        )
    ) if party_ids else {}

    for r in rows:
        snap = r.pop('snapshot') or {}
        parties = snap.get('parties') or []
        r['party'] = ', '.join(
            party_names.get(p.get('pid_id'), f"pid {p.get('pid_id')}") for p in parties
        ) or None
        r['share'] = parties[0].get('share') if parties else None
        time_begin = snap.get('time_begin')
        time_end = snap.get('time_end')
        r['time_spec'] = f"{time_begin or 'N/A'} to {time_end or 'ongoing'}"
        r['date_created'] = r.pop('changed_at')
        r['_mortgage'] = snap.get('mortgage')  # consumed + stripped by the Mortgages view only
    return rows


class RRR_Rights_Activity_View(APIView):
    """GET /api/user/sl-rights-activity/ — Activity Log "Rights" chip."""
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = _rrr_activity_rows(request.user.id, {'snapshot__rrr_type': 'RIGHT'})
        for r in rows:
            r.pop('_mortgage', None)
            r['right_type'] = 'RIGHT'
        return Response(rows, status=status.HTTP_200_OK)


class RRR_Responsibility_Activity_View(APIView):
    """GET /api/user/la-responsibility-activity/ — Activity Log "Responsibilities" chip."""
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = _rrr_activity_rows(request.user.id, {'snapshot__rrr_type': 'RESPONSIBILITY'})
        for r in rows:
            r.pop('_mortgage', None)
            r['responsibility_type'] = 'RESPONSIBILITY'
        return Response(rows, status=status.HTTP_200_OK)


class RRR_Admin_Restriction_Activity_View(APIView):
    """GET /api/user/sl-admin-restrict-activity/ — Activity Log "Admin_Restriction" chip.
    RESTRICTION is the third first-class rrr_type alongside RIGHT/RESPONSIBILITY
    (see LA_RRR_Model.rrr_type) — same pattern as the two views above. The old
    dead SL_Admin_Restrict_Model also carried a legal-space/legal-provision
    reference and a separate "governing party"; the unified schema doesn't keep
    those as distinct fields, so those two columns come back null rather than
    being guessed at.
    """
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = _rrr_activity_rows(request.user.id, {'snapshot__rrr_type': 'RESTRICTION'})
        for r in rows:
            r.pop('_mortgage', None)
            r['sl_adm_res_type'] = 'RESTRICTION'
            r['adm_res_legal_space'] = None
            r['adm_res_legal_prov'] = None
            r['gov_party'] = r.get('party')
        return Response(rows, status=status.HTTP_200_OK)


class RRR_Mortgage_Activity_View(APIView):
    """GET /api/user/la-mortgage-activity/ — Activity Log "Mortgages" chip.
    Mortgage is an attachment on any RRR (see _write_rrr_audit), not an
    rrr_type value, so this filters on snapshot.mortgage being present."""
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = _rrr_activity_rows(request.user.id, {'snapshot__mortgage__isnull': False})
        for r in rows:
            m = r.pop('_mortgage', None) or {}
            r['sl_mortgage_type'] = m.get('mortgage_type')
            r['amount'] = m.get('amount')
            r['int_rate'] = m.get('interest')
            r['ranking'] = m.get('ranking')
            r['mort_id'] = m.get('mortgage_ref_id')
            r['mortgagor'] = r.get('party')
            r['mortgagee'] = m.get('mortgagee')
        return Response(rows, status=status.HTTP_200_OK)
