from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..models import *
from ..utils import record_history


ATTRIBUTE_FIELD_MODELS = (
    LA_LS_Land_Unit_Model,
    LA_LS_Build_Unit_Model,
    Assessment_Model,
    Tax_Info_Model,
    LA_LS_Zoning_Model,
    LA_LS_Physical_Env_Model,
    LA_LS_Utinet_LU_Model,
    LA_LS_Utinet_BU_Model,
    LA_Spatial_Unit_Model,
    Survey_Rep_DATA_Model,
)


def _as_text(value):
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if hasattr(value, 'wkt'):
        return value.wkt
    return str(value)


def _history_row(row):
    data = {
        'id': row.id,
        'date': row.changed_at,
        'user': row.changed_by_name,
        'changed_by': row.changed_by,
        'record_type': row.record_type,
        'action': row.action,
        'category': row.category,
        'field_name': row.field_name,
        'old_value': row.old_value,
        'new_value': row.new_value,
        'change_made': row.change_summary,
        'can_restore': row.can_restore,
    }
    event = Parcel_Event_Model.objects.filter(source_history_id=row.id).first()
    if event:
        latest_active = _latest_active_event(row.su_id)
        can_rectify_now = bool(
            row.can_restore
            and event.can_rectify
            and event.status in (
                Parcel_Event_Model.STATUS_ACTIVE,
                Parcel_Event_Model.STATUS_REAPPLIED,
            )
            and latest_active
            and latest_active.id == event.id
        )
        data.update({
            'source': 'parcel_history',
            'event_id': event.id,
            'source_history_id': row.id,
            'status_label': event.status,
            'can_restore': can_rectify_now,
            'can_rectify_now': can_rectify_now,
        })
    return data


def _has_value(value):
    if value is None:
        return False
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return str(value).strip() not in ('', 'none', 'null', '[]')


def _relationship_value(value):
    if isinstance(value, (list, tuple, set)):
        return ', '.join(str(v) for v in value if _has_value(v)) or None
    return value


def _relationship_row(*, su_id, date, changed_by, field_name, value, label):
    value = _relationship_value(value)
    return {
        'id': f"current-rel-{field_name}-{su_id}",
        'date': date,
        'user': None,
        'changed_by': changed_by,
        'record_type': 'relationship',
        'action': 'current',
        'category': 'RELATIONSHIP',
        'field_name': field_name,
        'old_value': None,
        'new_value': value,
        'change_made': f"{label}: {value}",
        'can_restore': False,
    }


def _is_active_status(value):
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', 't', '1', 'yes')


def _parcel_status_row(row):
    if not row:
        return None
    return {
        'su_id': row.id,
        'layer_id': row.layer_id,
        'status': row.status,
        'is_active': _is_active_status(row.status),
        'parent_id': row.parent_id,
        'ref_id': row.ref_id,
        'date_created': row.date_created,
        'date_modified': row.date_modified,
    }


def _affected_parcels(su_id):
    survey = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
    parent_ids = survey.parent_id if survey and survey.parent_id else []
    if not isinstance(parent_ids, list):
        parent_ids = []

    child_rows = list(Survey_Rep_DATA_Model.objects.filter(parent_id__contains=[su_id]))
    ref_child_rows = list(Survey_Rep_DATA_Model.objects.filter(ref_id=su_id))
    child_by_id = {row.id: row for row in [*child_rows, *ref_child_rows]}

    parent_rows = list(Survey_Rep_DATA_Model.objects.filter(id__in=parent_ids)) if parent_ids else []

    return {
        'selected': _parcel_status_row(survey),
        'parents': [_parcel_status_row(row) for row in parent_rows],
        'children': [_parcel_status_row(row) for row in child_by_id.values()],
    }


def _geojson(geom):
    try:
        return geom.geojson if geom else None
    except Exception:
        return None


def _shape_lineage(su_id, max_per_parcel=20):
    """
    Previous shapes of the selected parcel and its parents/children, so the
    history Report tab can render shape thumbnails for the whole lineage.

    In this schema a spatial unit's su_id equals its survey_rep id, so child /
    parent survey_rep ids double as su_ids for geometry-history lookups.
    Returns a flat list ordered newest-first within each related parcel:
      {su_id, relation, label, kind, date, area, status, geom}  (geom = GeoJSON)
    """
    survey = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
    parent_ids = (survey.parent_id if survey and isinstance(survey.parent_id, list) else []) or []

    child_rows = list(Survey_Rep_DATA_Model.objects.filter(parent_id__contains=[su_id]))
    ref_child_rows = list(Survey_Rep_DATA_Model.objects.filter(ref_id=su_id))
    child_ids = sorted({row.id for row in [*child_rows, *ref_child_rows]})

    relation_by_id = {su_id: 'self'}
    for pid in parent_ids:
        relation_by_id.setdefault(pid, 'parent')
    for cid in child_ids:
        relation_by_id.setdefault(cid, 'child')

    def _geom_signature(geom):
        # Stable signature so identical shapes aren't shown twice (current vs an
        # unchanged history snapshot). WKB is exact and cheap; fall back to WKT.
        if not geom:
            return None
        try:
            return geom.ewkb if hasattr(geom, 'ewkb') else geom.wkb
        except Exception:
            try:
                return geom.wkt
            except Exception:
                return None

    lineage = []
    for related_id, relation in relation_by_id.items():
        seen_geoms = set()  # dedupe identical shapes within this parcel
        current = Survey_Rep_DATA_Model.objects.filter(id=related_id).first()
        label = None
        if current:
            su_attr = LA_LS_Build_Unit_Model.objects.filter(su_id__su_id=related_id).first()
            label = (su_attr.building_name if su_attr else None) or f"su_id {related_id}"
            sig = _geom_signature(current.geom)
            if sig is not None:
                seen_geoms.add(sig)
            lineage.append({
                'su_id': related_id,
                'relation': relation,
                'label': label,
                'kind': 'current' if _is_active_status(current.status) else 'last-known',
                'date': current.date_modified or current.date_created,
                'area': float(current.calculated_area) if current.calculated_area is not None else None,
                'status': _is_active_status(current.status),
                'geom': _geojson(current.geom),
            })

        history_rows = (
            Survey_Rep_Geom_History_Model.objects
            .filter(su_id=related_id)
            .order_by('-date_created')[:max_per_parcel]
        )
        for h in history_rows:
            sig = _geom_signature(h.geom)
            if sig is not None and sig in seen_geoms:
                continue  # same shape as current or an earlier snapshot — skip duplicate
            if sig is not None:
                seen_geoms.add(sig)
            lineage.append({
                'su_id': related_id,
                'relation': relation,
                'label': label or f"su_id {related_id}",
                'kind': 'previous',
                'date': h.date_created,
                'area': float(h.calculated_area) if h.calculated_area is not None else None,
                'status': _is_active_status(h.status),
                'geom': _geojson(h.geom),
            })

    return lineage


def _timeline_row(row, source='parcel_history'):
    data = _history_row(row)
    data['source'] = source
    data['event_type'] = (row.snapshot or {}).get('event_type') or row.record_type
    data['affected_parcels'] = (row.snapshot or {}).get('affected_parcels') or []
    data['status_label'] = 'Restorable' if row.can_restore else 'Recorded'
    data['source_history_id'] = row.id
    data['source_event_id'] = None
    return data


def _event_row(event):
    return {
        'id': f"event-{event.id}",
        'event_id': event.id,
        'source_history_id': event.source_history_id,
        'source_event_id': event.source_event_id,
        'date': event.created_at,
        'rectified_at': event.rectified_at,
        'user': event.created_by_name,
        'changed_by': event.created_by,
        'record_type': event.event_type,
        'action': event.status,
        'category': event.event_type.upper(),
        'field_name': None,
        'old_value': event.before_snapshot,
        'new_value': event.after_snapshot,
        'change_made': event.summary,
        'can_restore': event.can_rectify,
        'source': 'parcel_event',
        'event_type': event.event_type,
        'affected_parcels': event.affected_parcel_ids or [event.primary_su_id],
        'status_label': event.status,
        'can_rectify_now': False,
        'can_undo_now': False,
    }


def _legacy_event_rows(su_id):
    existing_history_ids = set(
        Parcel_Event_Model.objects
        .filter(primary_su_id=su_id, source_history_id__isnull=False)
        .values_list('source_history_id', flat=True)
    )
    return [
        _timeline_row(row)
        for row in Parcel_History_Model.objects.filter(su_id=su_id)
        if row.id not in existing_history_ids
    ]


def _get_event_theme(category, record_type, event_type):
    cat = str(category or record_type or event_type or '').upper()
    if 'GEOM' in cat:
        return 'GEOMETRY'
    if 'RRR' in cat:
        return 'RRR'
    return 'ATTRIBUTE'


def _apply_stack_permissions(rows):
    # Group active events by theme
    active_by_theme = {}
    for row in rows:
        if (
            row.get('source') == 'parcel_event'
            and row.get('status_label') in ('active', 'reapplied')
            and row.get('can_restore')
        ):
            theme = _get_event_theme(row.get('category'), row.get('record_type'), row.get('event_type'))
            active_by_theme.setdefault(theme, []).append(row)

    # Group rectified events by theme
    rectified_by_theme = {}
    for row in rows:
        if row.get('source') == 'parcel_event' and row.get('status_label') == 'rectified':
            theme = _get_event_theme(row.get('category'), row.get('record_type'), row.get('event_type'))
            rectified_by_theme.setdefault(theme, []).append(row)

    # Apply LIFO within each theme for active events
    for theme, active_list in active_by_theme.items():
        if active_list:
            latest = sorted(active_list, key=lambda item: item.get('date') or timezone.now(), reverse=True)[0]
            latest['can_rectify_now'] = bool(latest.get('can_restore'))
            for row in active_list:
                if row is not latest:
                    row['status_label'] = 'blocked by newer event'
                    row['can_rectify_now'] = False

    # Apply LIFO within each theme for rectified events
    for theme, rectified_list in rectified_by_theme.items():
        if rectified_list:
            latest_rectified = sorted(
                rectified_list,
                key=lambda item: item.get('rectified_at') or item.get('date') or timezone.now(),
                reverse=True,
            )[0]
            latest_rectified['can_undo_now'] = True
            for row in rectified_list:
                if row is not latest_rectified:
                    row['can_undo_now'] = False

    return rows


def _rectification_controls(timeline):
    next_rectifiable = next((row for row in timeline if row.get('can_rectify_now')), None)
    last_rectified = next((row for row in timeline if row.get('can_undo_now')), None)
    return {
        'next_rectifiable_event': next_rectifiable,
        'last_rectified_event': last_rectified,
        'can_rectify_previous': bool(next_rectifiable),
        'can_undo_last': bool(last_rectified),
    }


def _build_timeline(*groups):
    rows = []
    for group in groups:
        rows.extend(group)
    rows = sorted(rows, key=lambda item: item.get('date') or timezone.now(), reverse=True)
    return _apply_stack_permissions(rows)


def _ensure_event_for_history(row):
    event = Parcel_Event_Model.objects.filter(source_history_id=row.id).first()
    if event:
        return event
    event_type = (row.snapshot or {}).get('event_type') or row.record_type
    affected = (row.snapshot or {}).get('affected_parcels') or [row.su_id]
    if not isinstance(affected, list):
        affected = [row.su_id]
    is_audit_event = row.action in {
        Parcel_History_Model.ACTION_RESTORE,
        'undo_rectification',
    } or event_type in {
        'geometry_restore',
        'attribute_restore',
        'rrr_restore',
        'undo_rectification',
    }
    return Parcel_Event_Model.objects.create(
        primary_su_id=row.su_id,
        event_type=event_type,
        summary=row.change_summary,
        status=Parcel_Event_Model.STATUS_RECORDED if is_audit_event else Parcel_Event_Model.STATUS_ACTIVE,
        affected_parcel_ids=affected,
        source_history_id=row.id,
        before_snapshot={'field_name': row.field_name, 'old_value': row.old_value},
        after_snapshot={'field_name': row.field_name, 'new_value': row.new_value, 'snapshot': row.snapshot},
        created_by=row.changed_by,
        created_by_name=row.changed_by_name,
        can_rectify=row.can_restore and not is_audit_event,
    )


def _parse_geom(value):
    if not value:
        return None
    geom = GEOSGeometry(value)
    if not geom.srid:
        geom.srid = 4326
    return geom


def _match_geometry_srid(geom, target_geom):
    if not geom or not target_geom:
        return geom
    target_srid = target_geom.srid
    if not target_srid:
        return geom
    if not geom.srid:
        geom.srid = target_srid
    elif geom.srid != target_srid:
        geom = geom.transform(target_srid, clone=True)
    return geom


def _recalculate_area(instance):
    if not instance.geom:
        instance.calculated_area = 0
        return
    crs = instance.reference_coordinate or "EPSG:4326"
    try:
        srid = int(str(crs).split(":")[-1])
    except (ValueError, AttributeError):
        srid = 4326
    projected = instance.geom.transform(5235, clone=True) if srid in [4326, 4269, 4230] else instance.geom.transform(srid, clone=True)
    if instance.geom_type in ["polygon", "multipolygon"]:
        instance.calculated_area = round(projected.area, 4)
    elif instance.geom_type in ["linestring", "multilinestring"]:
        instance.calculated_area = round(projected.length, 4)
    else:
        instance.calculated_area = 0


def _find_attribute_target(row):
    for model in ATTRIBUTE_FIELD_MODELS:
        field_map = {f.name: f for f in model._meta.fields}
        field = field_map.get(row.field_name)
        if not field:
            continue
        if model is Survey_Rep_DATA_Model:
            target = model.objects.select_for_update().filter(id=row.su_id).first()
        else:
            target = model.objects.select_for_update().filter(su_id=row.su_id).first()
        if target:
            return target, field
    return None, None


def _coerce_field_value(field, value):
    if value in ('', 'None', 'none', 'null'):
        value = None
    if value is None:
        return None
    try:
        return field.to_python(value)
    except (ValidationError, TypeError, ValueError):
        return value


def _restore_attribute_from_history(row, *, user, reason, use_old_value):
    target, field = _find_attribute_target(row)
    if not target:
        return None, Response({'error': 'No target record found for restore.'}, status=status.HTTP_400_BAD_REQUEST)

    current_value = getattr(target, row.field_name)
    restored_value = _coerce_field_value(field, row.old_value if use_old_value else row.new_value)
    setattr(target, row.field_name, restored_value)
    target.save(update_fields=[row.field_name])

    record_history(
        su_id=row.su_id,
        record_type=Parcel_History_Model.RECORD_ATTRIBUTE,
        action=Parcel_History_Model.ACTION_RESTORE if use_old_value else 'undo_rectification',
        user=user,
        category=row.category,
        field_name=row.field_name,
        old_value=current_value,
        new_value=restored_value,
        change_summary=(
            f"Restored {row.field_name} to {row.old_value or 'empty'}"
            if use_old_value else
            f"Reapplied {row.field_name} to {row.new_value or 'empty'}"
        ),
        snapshot={
            'event_type': 'attribute_restore' if use_old_value else 'undo_rectification',
            'reason': reason,
            'source_history_id': row.id,
            'field_name': row.field_name,
            'affected_parcels': [row.su_id],
        },
        can_restore=False,
    )
    return restored_value, None


def _rrr_snapshot_for_history(row):
    snap = row.snapshot or {}
    if snap.get('snapshot'):
        return snap.get('snapshot')
    audit_id = snap.get('audit_id')
    if audit_id:
        audit = LA_RRR_Audit_Model.objects.filter(id=audit_id).first()
        if audit:
            return audit.snapshot
    return None


def _previous_rrr_snapshot(row):
    snap = row.snapshot or {}
    if 'before_snapshot' in snap:
        return snap.get('before_snapshot')
    rrr_id = snap.get('rrr_id')
    if not rrr_id:
        return None
    audit_qs = LA_RRR_Audit_Model.objects.filter(rrr_id=rrr_id)
    audit_id = snap.get('audit_id')
    if audit_id:
        audit_qs = audit_qs.filter(id__lt=audit_id)
    return (audit_qs.order_by('-changed_at', '-id').values_list('snapshot', flat=True).first())


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ('true', 't', '1', 'yes')


def _apply_rrr_snapshot(rrr, snapshot):
    if snapshot is None:
        rrr.status = False
        rrr.save(update_fields=['status'])
        if rrr.ba_unit_id_id:
            for doc_link in LA_RRR_Document_Model.objects.filter(ba_unit_id=rrr.ba_unit_id_id).select_related('admin_source'):
                if doc_link.admin_source:
                    doc_link.admin_source.status = False
                    doc_link.admin_source.save(update_fields=['status'])
        return

    rrr.rrr_type = snapshot.get('rrr_type') or rrr.rrr_type
    rrr.time_begin = snapshot.get('time_begin') or None
    rrr.time_end = snapshot.get('time_end') or None
    rrr.description = snapshot.get('description')
    rrr.status = _as_bool(snapshot.get('status'))
    rrr.save(update_fields=['rrr_type', 'time_begin', 'time_end', 'description', 'status'])

    Party_Roles_Model.objects.filter(rrr_id=rrr).delete()
    for party in snapshot.get('parties') or []:
        if not party.get('pid_id'):
            continue
        Party_Roles_Model.objects.create(
            pid_id=party.get('pid_id'),
            rrr_id=rrr,
            party_role_type=party.get('party_role_type') or rrr.rrr_type,
            share_type=party.get('share_type'),
            share=party.get('share'),
            done_by=getattr(rrr, '_history_user_id', None) or 0,
        )

    mortgage_snapshot = snapshot.get('mortgage')
    if mortgage_snapshot:
        mortgage, _ = LA_Mortgage_Model.objects.get_or_create(rrr_id=rrr)
        for field in ('amount', 'interest', 'ranking', 'mortgage_type', 'mortgage_ref_id', 'mortgagee'):
            setattr(mortgage, field, mortgage_snapshot.get(field))
        mortgage.save()
    else:
        LA_Mortgage_Model.objects.filter(rrr_id=rrr).delete()

    snapshot_doc_source_ids = {
        doc.get('admin_source_id')
        for doc in (snapshot.get('documents') or [])
        if doc.get('admin_source_id')
    }
    if rrr.admin_source_id_id:
        snapshot_doc_source_ids.add(rrr.admin_source_id_id)
    for doc_link in LA_RRR_Document_Model.objects.filter(ba_unit_id=rrr.ba_unit_id_id).select_related('admin_source'):
        admin_source = doc_link.admin_source
        if not admin_source:
            continue
        should_be_active = admin_source.admin_source_id in snapshot_doc_source_ids
        if admin_source.status != should_be_active:
            admin_source.status = should_be_active
            admin_source.save(update_fields=['status'])


def _restore_rrr_from_history(row, *, user, reason, use_before_snapshot):
    snap = row.snapshot or {}
    rrr_id = snap.get('rrr_id')
    if not rrr_id:
        return None, Response({'error': 'RRR history row has no RRR id.'}, status=status.HTTP_400_BAD_REQUEST)
    rrr = LA_RRR_Model.objects.select_for_update().filter(rrr_id=rrr_id).first()
    if not rrr:
        return None, Response({'error': 'RRR record not found.'}, status=status.HTTP_404_NOT_FOUND)

    current_snapshot = _rrr_snapshot_for_history(row)
    target_snapshot = _previous_rrr_snapshot(row) if use_before_snapshot else current_snapshot
    rrr._history_user_id = user.id
    _apply_rrr_snapshot(rrr, target_snapshot)

    record_history(
        su_id=row.su_id,
        record_type=Parcel_History_Model.RECORD_RRR,
        action=Parcel_History_Model.ACTION_RESTORE if use_before_snapshot else 'undo_rectification',
        user=user,
        category='RRR',
        field_name='rrr',
        old_value=current_snapshot,
        new_value=target_snapshot,
        change_summary=(
            f"RRR {rrr_id} restored from history row {row.id}"
            if use_before_snapshot else
            f"RRR {rrr_id} rectification undone for history row {row.id}"
        ),
        snapshot={
            'event_type': 'rrr_restore' if use_before_snapshot else 'undo_rectification',
            'reason': reason,
            'source_history_id': row.id,
            'rrr_id': rrr_id,
            'affected_parcels': [row.su_id],
        },
        can_restore=False,
    )
    return rrr, None


def _latest_active_event(primary_su_id):
    return (
        Parcel_Event_Model.objects
        .filter(primary_su_id=primary_su_id, status__in=[
            Parcel_Event_Model.STATUS_ACTIVE,
            Parcel_Event_Model.STATUS_REAPPLIED,
        ], can_rectify=True)
        .order_by('-created_at', '-id')
        .first()
    )


def _latest_rectified_event(primary_su_id):
    return (
        Parcel_Event_Model.objects
        .filter(primary_su_id=primary_su_id, status=Parcel_Event_Model.STATUS_RECTIFIED)
        .order_by('-rectified_at', '-id')
        .first()
    )


class Parcel_History_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        attributes = [
            _history_row(row)
            for row in Parcel_History_Model.objects.filter(
                su_id=su_id,
                record_type=Parcel_History_Model.RECORD_ATTRIBUTE,
            )
        ]

        rrr_history = [
            _history_row(row)
            for row in Parcel_History_Model.objects.filter(
                su_id=su_id,
                record_type=Parcel_History_Model.RECORD_RRR,
            )
        ]
        known_rrr_audit_ids = {
            (row.snapshot or {}).get('audit_id')
            for row in Parcel_History_Model.objects.filter(
                su_id=su_id,
                record_type=Parcel_History_Model.RECORD_RRR,
            )
        }
        rrr_history.extend([
            {
                'id': f"rrr-audit-{row.id}",
                'date': row.changed_at,
                'user': row.changed_by_name,
                'changed_by': row.changed_by,
                'record_type': 'rrr',
                'action': row.action,
                'category': 'RRR',
                'field_name': 'rrr',
                'old_value': None,
                'new_value': row.snapshot,
                'change_made': f"RRR {row.rrr_id} {row.action.lower()}",
                'can_restore': False,
                'status_label': 'Recorded',
            }
            for row in LA_RRR_Audit_Model.objects.filter(su_id=su_id)
            if row.id not in known_rrr_audit_ids
        ])

        geometry_history = [
            _history_row(row)
            for row in Parcel_History_Model.objects.filter(
                su_id=su_id,
                record_type=Parcel_History_Model.RECORD_GEOMETRY,
            )
        ]
        if not geometry_history:
            geometry_history = [
                {
                    'id': f"geom-{row.id}",
                    'date': row.date_created,
                    'user': None,
                    'changed_by': row.user_id,
                    'record_type': 'geometry',
                    'action': 'delete' if not row.status else 'update',
                    'category': 'GEOMETRY',
                    'field_name': 'geom',
                    'old_value': None,
                    'new_value': row.geom.geojson if row.geom else None,
                    'change_made': 'Geometry deleted' if not row.status else 'Geometry snapshot recorded',
                    'can_restore': False,
                }
                for row in Survey_Rep_Geom_History_Model.objects.filter(su_id=su_id).order_by('-date_created')
            ]

        relationship_history = [
            _history_row(row)
            for row in Parcel_History_Model.objects.filter(
                su_id=su_id,
                record_type=Parcel_History_Model.RECORD_RELATIONSHIP,
            )
        ]

        survey = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
        if survey:
            relation_date = survey.date_modified or survey.date_created
            current_rows = []

            if _has_value(survey.parent_id):
                current_rows.append(_relationship_row(
                    su_id=su_id,
                    date=relation_date,
                    changed_by=survey.user_id,
                    field_name='parent_id',
                    value=survey.parent_id,
                    label='Parent ID',
                ))
            if _has_value(survey.ref_id):
                current_rows.append(_relationship_row(
                    su_id=su_id,
                    date=relation_date,
                    changed_by=survey.user_id,
                    field_name='ref_id',
                    value=survey.ref_id,
                    label='Reference parcel',
                ))

            computed_child_ids = [
                row.id
                for row in Survey_Rep_DATA_Model.objects.filter(parent_id__contains=[su_id]).only('id', 'status')
                if _is_active_status(row.status)
            ]
            ref_child_ids = [
                row.id
                for row in Survey_Rep_DATA_Model.objects.filter(ref_id=su_id).only('id', 'status')
                if _is_active_status(row.status)
            ]
            child_ids = sorted({*computed_child_ids, *ref_child_ids})
            if child_ids:
                current_rows.append(_relationship_row(
                    su_id=su_id,
                    date=relation_date,
                    changed_by=survey.user_id,
                    field_name='child_ids',
                    value=child_ids,
                    label='Child IDs',
                ))

            land_unit = LA_LS_Land_Unit_Model.objects.filter(su_id__su_id=su_id).first()
            if land_unit:
                if _has_value(land_unit.adjacent_parcels):
                    current_rows.append(_relationship_row(
                        su_id=su_id,
                        date=relation_date,
                        changed_by=survey.user_id,
                        field_name='adjacent_parcels',
                        value=land_unit.adjacent_parcels,
                        label='Adjacent land parcels',
                    ))
                if _has_value(land_unit.parent_parcel):
                    current_rows.append(_relationship_row(
                        su_id=su_id,
                        date=relation_date,
                        changed_by=survey.user_id,
                        field_name='parent_parcel',
                        value=land_unit.parent_parcel,
                        label='Parent parcel',
                    ))
                if _has_value(land_unit.child_parcels):
                    current_rows.append(_relationship_row(
                        su_id=su_id,
                        date=relation_date,
                        changed_by=survey.user_id,
                        field_name='child_parcels',
                        value=land_unit.child_parcels,
                        label='Child parcels',
                    ))
                if _has_value(land_unit.part_of_estate):
                    current_rows.append(_relationship_row(
                        su_id=su_id,
                        date=relation_date,
                        changed_by=survey.user_id,
                        field_name='part_of_estate',
                        value=land_unit.part_of_estate,
                        label='Part of estate',
                    ))

            relationship_history.extend(current_rows)

        for row in Parcel_History_Model.objects.filter(su_id=su_id, can_restore=True):
            _ensure_event_for_history(row)

        timeline = _build_timeline(
            [_event_row(row) for row in Parcel_Event_Model.objects.filter(primary_su_id=su_id)],
            _legacy_event_rows(su_id),
            [
                {
                    'id': f"rrr-audit-{row.id}",
                    'date': row.changed_at,
                    'user': row.changed_by_name,
                    'changed_by': row.changed_by,
                    'record_type': 'rrr',
                    'action': row.action,
                    'category': 'RRR',
                    'field_name': 'rrr',
                    'old_value': None,
                    'new_value': row.snapshot,
                    'change_made': f"RRR {row.rrr_id} {row.action.lower()}",
                    'can_restore': False,
                    'source': 'rrr_audit',
                    'event_type': 'rrr',
                    'affected_parcels': [su_id],
                    'status_label': 'Recorded',
                }
                for row in LA_RRR_Audit_Model.objects.filter(su_id=su_id)
                if row.id not in known_rrr_audit_ids
            ],
        )

        legal_spaces = [
            _history_row(row)
            for row in Parcel_History_Model.objects.filter(
                su_id=su_id,
                record_type=Parcel_History_Model.RECORD_LEGAL_SPACE,
            )
        ]

        return Response({
            'timeline': timeline,
            'rectification_controls': _rectification_controls(timeline),
            'attributes': attributes,
            'rrr': rrr_history,
            'geometry': geometry_history,
            'relationships': relationship_history,
            'legal_spaces': legal_spaces,
            'shape_lineage': _shape_lineage(su_id),
            'affected_parcels': _affected_parcels(su_id),
        }, status=status.HTTP_200_OK)


class Deleted_Parcel_Search_View(APIView):
    """
    Find soft-deleted land parcels so their history can be opened even though
    they are no longer drawn on the map.

    GET /api/user/deleted-parcels/?q=<su_id-or-label>
    Matches survey_rep land features (layer 1/6) with status=False by exact
    su_id or label icontains, enriched with deleted_at/deleted_by from the
    parcel_delete_archive.  Returns newest-first, capped at 50.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response({'results': []}, status=status.HTTP_200_OK)

        from django.db.models import Q as _Q

        qs = Survey_Rep_DATA_Model.objects.filter(status=False, layer_id__in=[1, 6])

        # Label match on the spatial unit (su_id label lives there)
        spatial_ids = list(
            LA_Spatial_Unit_Model.objects
            .filter(label__icontains=q)
            .values_list('su_id', flat=True)[:200]
        )

        cond = _Q(pk__in=[])  # empty by default
        if q.isdigit():
            cond = cond | _Q(id=int(q)) | _Q(su_id_id=int(q))
        if spatial_ids:
            cond = cond | _Q(su_id_id__in=spatial_ids)

        rows = list(qs.filter(cond).order_by('-id')[:50]) if (q.isdigit() or spatial_ids) else []

        archive_by_su = {
            a.su_id: a
            for a in Parcel_Delete_Archive_Model.objects.filter(
                su_id__in=[r.su_id_id for r in rows if r.su_id_id]
            )
        }
        spatial_by_su = {
            s.su_id: s
            for s in LA_Spatial_Unit_Model.objects.filter(
                su_id__in=[r.su_id_id for r in rows if r.su_id_id]
            )
        }

        results = []
        for r in rows:
            archive = archive_by_su.get(r.su_id_id)
            spatial = spatial_by_su.get(r.su_id_id)
            results.append({
                'su_id': r.su_id_id or r.id,
                'label': (spatial.label if spatial else None) or f"Parcel {r.su_id_id or r.id}",
                'deleted_at': archive.deleted_at if archive else None,
                'deleted_by': archive.deleted_by if archive else None,
                'calculated_area': float(r.calculated_area) if r.calculated_area is not None else None,
            })

        return Response({'results': results}, status=status.HTTP_200_OK)


class Parcel_History_Restore_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, history_id):
        reason = (request.data or {}).get('reason')
        if not reason:
            return Response({'error': 'Restore reason is required.'}, status=status.HTTP_400_BAD_REQUEST)

        row = Parcel_History_Model.objects.filter(
            id=history_id,
            record_type=Parcel_History_Model.RECORD_ATTRIBUTE,
            can_restore=True,
        ).first()
        if not row:
            return Response({'error': 'Restorable history row not found.'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            event = _ensure_event_for_history(row)
            latest_event = _latest_active_event(row.su_id)
            if latest_event and latest_event.id != event.id:
                return Response(
                    {'error': 'Only the latest active parcel event can be rectified. Rectify newer events first.'},
                    status=status.HTTP_409_CONFLICT,
                )
            _, error = _restore_attribute_from_history(
                row,
                user=request.user,
                reason=reason,
                use_old_value=True,
            )
            if error:
                return error
            event.status = Parcel_Event_Model.STATUS_RECTIFIED
            event.rectification_reason = reason
            event.rectified_by = request.user.id
            event.rectified_at = timezone.now()
            event.can_rectify = False
            event.save(update_fields=[
                'status', 'rectification_reason', 'rectified_by', 'rectified_at', 'can_rectify',
            ])

        return Response({'detail': 'Change restored.'}, status=status.HTTP_200_OK)


class Parcel_RRR_Restore_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, history_id):
        reason = (request.data or {}).get('reason')
        if not reason:
            return Response({'error': 'Restore reason is required.'}, status=status.HTTP_400_BAD_REQUEST)

        row = Parcel_History_Model.objects.filter(
            id=history_id,
            record_type=Parcel_History_Model.RECORD_RRR,
            can_restore=True,
        ).first()
        if not row:
            return Response({'error': 'Restorable RRR history row not found.'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            event = _ensure_event_for_history(row)
            latest_event = _latest_active_event(row.su_id)
            if latest_event and latest_event.id != event.id:
                return Response(
                    {'error': 'Only the latest active parcel event can be rectified. Rectify newer events first.'},
                    status=status.HTTP_409_CONFLICT,
                )
            _, error = _restore_rrr_from_history(
                row,
                user=request.user,
                reason=reason,
                use_before_snapshot=True,
            )
            if error:
                return error
            event.status = Parcel_Event_Model.STATUS_RECTIFIED
            event.rectification_reason = reason
            event.rectified_by = request.user.id
            event.rectified_at = timezone.now()
            event.can_rectify = False
            event.save(update_fields=[
                'status', 'rectification_reason', 'rectified_by', 'rectified_at', 'can_rectify',
            ])

        return Response({'detail': 'RRR restored.'}, status=status.HTTP_200_OK)


class Parcel_Geometry_Restore_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, history_id):
        reason = (request.data or {}).get('reason')
        cancel_children = bool((request.data or {}).get('cancel_children', False))
        if not reason:
            return Response({'error': 'Restore reason is required.'}, status=status.HTTP_400_BAD_REQUEST)

        row = Parcel_History_Model.objects.filter(
            id=history_id,
            record_type=Parcel_History_Model.RECORD_GEOMETRY,
            can_restore=True,
        ).first()
        if not row:
            return Response({'error': 'Restorable geometry history row not found.'}, status=status.HTTP_404_NOT_FOUND)

        old_geom = _parse_geom(row.old_value)
        if old_geom is None:
            return Response({'error': 'This geometry row has no previous geometry to restore.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            event = _ensure_event_for_history(row)
            latest_event = _latest_active_event(row.su_id)
            if latest_event and latest_event.id != event.id:
                return Response(
                    {'error': 'Only the latest active parcel event can be rectified. Rectify newer events first.'},
                    status=status.HTTP_409_CONFLICT,
                )

            survey = Survey_Rep_DATA_Model.objects.select_for_update().filter(id=row.su_id).first()
            if not survey:
                return Response({'error': 'Parcel geometry record not found.'}, status=status.HTTP_404_NOT_FOUND)

            current_geom = survey.geom
            old_geom = _match_geometry_srid(old_geom, current_geom)
            survey.geom = old_geom
            update_fields = ['geom', 'date_modified', 'calculated_area']
            if cancel_children:
                survey.status = True
                update_fields.append('status')
            survey.date_modified = timezone.now()
            _recalculate_area(survey)
            survey.save(update_fields=update_fields)

            cancelled_children = []
            if cancel_children:
                child_qs = Survey_Rep_DATA_Model.objects.filter(parent_id__contains=[row.su_id])
                for child in child_qs:
                    child.status = False
                    child.date_modified = timezone.now()
                    child.save(update_fields=['status', 'date_modified'])
                    cancelled_children.append(child.id)

            record_history(
                su_id=row.su_id,
                record_type=Parcel_History_Model.RECORD_GEOMETRY,
                action=Parcel_History_Model.ACTION_RESTORE,
                user=request.user,
                category='GEOMETRY',
                field_name='geom',
                old_value=current_geom,
                new_value=old_geom,
                change_summary=f"Geometry restored from history row {history_id}",
                snapshot={
                    'event_type': 'geometry_restore',
                    'reason': reason,
                    'source_history_id': history_id,
                    'cancelled_children': cancelled_children,
                    'affected_parcels': [row.su_id, *cancelled_children],
                },
                can_restore=False,
            )
            event.status = Parcel_Event_Model.STATUS_RECTIFIED
            event.rectification_reason = reason
            event.rectified_by = request.user.id
            event.rectified_at = timezone.now()
            event.can_rectify = False
            event.after_snapshot = {
                **(event.after_snapshot or {}),
                'rectification': {
                    'cancelled_children': cancelled_children,
                    'reason': reason,
                },
            }
            event.save(update_fields=[
                'status', 'rectification_reason', 'rectified_by', 'rectified_at', 'can_rectify',
                'after_snapshot',
            ])

        return Response({
            'detail': 'Geometry restored.',
            'cancelled_children': cancelled_children,
        }, status=status.HTTP_200_OK)


class Parcel_Event_Undo_Rectification_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        reason = (request.data or {}).get('reason')
        if not reason:
            return Response({'error': 'Undo reason is required.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            event = Parcel_Event_Model.objects.select_for_update().filter(id=event_id).first()
            if not event:
                return Response({'error': 'Event not found.'}, status=status.HTTP_404_NOT_FOUND)
            latest_rectified = _latest_rectified_event(event.primary_su_id)
            if not latest_rectified or latest_rectified.id != event.id:
                return Response(
                    {'error': 'Only the most recent rectification can be undone.'},
                    status=status.HTTP_409_CONFLICT,
                )
            history = Parcel_History_Model.objects.filter(id=event.source_history_id).first()
            if not history:
                return Response({'error': 'Source history row not found.'}, status=status.HTTP_400_BAD_REQUEST)

            if history.record_type == Parcel_History_Model.RECORD_GEOMETRY:
                after_geom = _parse_geom(history.new_value)
                if after_geom is None:
                    return Response({'error': 'This event has no geometry to reapply.'}, status=status.HTTP_400_BAD_REQUEST)

                survey = Survey_Rep_DATA_Model.objects.select_for_update().filter(id=event.primary_su_id).first()
                if not survey:
                    return Response({'error': 'Parcel geometry record not found.'}, status=status.HTTP_404_NOT_FOUND)

                current_geom = survey.geom
                after_geom = _match_geometry_srid(after_geom, current_geom)
                survey.geom = after_geom
                survey.status = True
                survey.date_modified = timezone.now()
                _recalculate_area(survey)
                survey.save(update_fields=['geom', 'status', 'date_modified', 'calculated_area'])

                cancelled_children = (event.after_snapshot or {}).get('rectification', {}).get('cancelled_children') or []
                for child_id in cancelled_children:
                    child = Survey_Rep_DATA_Model.objects.filter(id=child_id).first()
                    if child:
                        child.status = True
                        child.date_modified = timezone.now()
                        child.save(update_fields=['status', 'date_modified'])

                record_history(
                    su_id=event.primary_su_id,
                    record_type=Parcel_History_Model.RECORD_GEOMETRY,
                    action='undo_rectification',
                    user=request.user,
                    category='GEOMETRY',
                    field_name='geom',
                    old_value=current_geom,
                    new_value=after_geom,
                    change_summary=f"Rectification undone for event {event.id}",
                    snapshot={
                        'event_type': 'undo_rectification',
                        'reason': reason,
                        'source_event_id': event.id,
                        'affected_parcels': event.affected_parcel_ids or [event.primary_su_id],
                    },
                    can_restore=False,
                )
            elif history.record_type == Parcel_History_Model.RECORD_ATTRIBUTE:
                _, error = _restore_attribute_from_history(
                    history,
                    user=request.user,
                    reason=reason,
                    use_old_value=False,
                )
                if error:
                    return error
            elif history.record_type == Parcel_History_Model.RECORD_RRR:
                _, error = _restore_rrr_from_history(
                    history,
                    user=request.user,
                    reason=reason,
                    use_before_snapshot=False,
                )
                if error:
                    return error
            else:
                return Response({'error': 'Undo is not available for this event type.'}, status=status.HTTP_400_BAD_REQUEST)
            event.status = Parcel_Event_Model.STATUS_REAPPLIED
            event.can_rectify = True
            event.save(update_fields=['status', 'can_rectify'])

        return Response({'detail': 'Rectification undone.'}, status=status.HTTP_200_OK)
