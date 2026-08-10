"""
Shared utilities for InfoBhoomi views.

Permission helpers
─────────────────
All views use the same two-step pattern:
  1. Resolve the user's role_id from User_Roles_Model
  2. Check Role_Permission_Model for a specific permission + action

Use these helpers instead of copy-pasting that logic.

Issue #9 fix
────────────
`has_perm` was previously two serial DB queries:
  query 1 → get role_id from user_roles
  query 2 → check role_permission

It is now a single SQL statement (subquery):
  SELECT EXISTS(
      SELECT 1 FROM role_permission
      WHERE role_id IN (SELECT role_id FROM user_roles WHERE users @> [user_id])
        AND permission_id = X
        AND <action> = true
  )

This halves the permission-check overhead on every protected endpoint.
"""

from decimal import Decimal, InvalidOperation

from rest_framework.response import Response
from rest_framework import status

from .models import User_Roles_Model, Role_Permission_Model, Parcel_History_Model, Parcel_Event_Model


def get_user_role_id(user_id):
    """
    Return the role_id for *user_id*, or None if the user has no role.

    Prefer has_perm() for simple allow/deny checks — it uses a single query.
    Use this only when you need the raw role_id for other purposes.
    """
    row = User_Roles_Model.objects.filter(
        users__contains=[user_id]
    ).values('role_id').first()
    return row['role_id'] if row else None


def has_perm(user_id, permission_id, action):
    """
    Return True if the user's role grants *action* on *permission_id*.

    *action* must be one of: 'view', 'add', 'edit', 'delete'.

    Issue #9 fix: executes as a single SQL round trip instead of two.
    Django evaluates `role_id__in=<queryset>` as a subquery, so the DB
    sees one statement: EXISTS(... IN (SELECT role_id FROM user_roles ...)).

    Usage:
        if not has_perm(request.user.id, 201, 'add'):
            return perm_denied()
    """
    user_role_ids = User_Roles_Model.objects.filter(
        users__contains=[user_id]
    ).values('role_id')

    return Role_Permission_Model.objects.filter(
        role_id__in=user_role_ids,
        permission_id=permission_id,
        **{action: True}
    ).exists()


def perm_denied(message=None):
    """Return a standard 403 Response."""
    return Response(
        {"error": message or "You do not have permission to perform this action."},
        status=status.HTTP_403_FORBIDDEN
    )


def no_role_response():
    """Return a standard 403 Response for users with no role assigned."""
    return Response(
        {"error": "User has no assigned roles."},
        status=status.HTTP_403_FORBIDDEN
    )


def _history_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.lower() in ('', 'none', 'null', 'undefined'):
            return None
        return cleaned
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if hasattr(value, 'wkt'):
        return value.wkt
    if isinstance(value, (list, tuple)):
        return [_history_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _history_value(val) for key, val in value.items()}
    return str(value)


def _history_values_equal(old_value, new_value):
    old_normal = _history_value(old_value)
    new_normal = _history_value(new_value)

    if old_normal == new_normal:
        return True

    try:
        old_decimal = Decimal(str(old_normal))
        new_decimal = Decimal(str(new_normal))
        return old_decimal == new_decimal
    except (InvalidOperation, TypeError, ValueError):
        pass

    bool_values = {
        'true': True,
        'false': False,
        'yes': True,
        'no': False,
        '1': True,
        '0': False,
    }
    old_bool = bool_values.get(str(old_normal).strip().lower())
    new_bool = bool_values.get(str(new_normal).strip().lower())
    if old_bool is not None and new_bool is not None:
        return old_bool == new_bool

    return False


def history_user_name(user):
    if not user:
        return ''
    full_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    return full_name or getattr(user, 'email', None) or getattr(user, 'username', '')


def record_history(
    *,
    su_id,
    record_type,
    action,
    user=None,
    category=None,
    field_name=None,
    old_value=None,
    new_value=None,
    change_summary=None,
    snapshot=None,
    can_restore=False,
):
    old_text = _history_value(old_value)
    new_text = _history_value(new_value)
    if change_summary is None:
        if field_name:
            change_summary = f"{field_name} changed from {old_text or 'empty'} to {new_text or 'empty'}"
        else:
            change_summary = f"{record_type} {action}"

    row = Parcel_History_Model.objects.create(
        su_id=su_id,
        record_type=record_type,
        action=action,
        category=category,
        field_name=field_name,
        old_value=old_text,
        new_value=new_text,
        change_summary=change_summary,
        changed_by=getattr(user, 'id', None),
        changed_by_name=history_user_name(user),
        snapshot=snapshot,
        can_restore=can_restore,
    )

    event_type = (snapshot or {}).get('event_type') or record_type
    affected = (snapshot or {}).get('affected_parcels') or [su_id]
    if not isinstance(affected, list):
        affected = [su_id]
    audit_event_types = {'geometry_restore', 'attribute_restore', 'rrr_restore', 'undo_rectification'}
    is_audit_event = action in {
        Parcel_History_Model.ACTION_RESTORE,
        'undo_rectification',
    } or event_type in audit_event_types
    Parcel_Event_Model.objects.create(
        primary_su_id=su_id,
        event_type=event_type,
        summary=change_summary,
        status=Parcel_Event_Model.STATUS_RECORDED if is_audit_event else Parcel_Event_Model.STATUS_ACTIVE,
        affected_parcel_ids=affected,
        source_history_id=row.id,
        before_snapshot={
            'field_name': field_name,
            'old_value': old_text,
        },
        after_snapshot={
            'field_name': field_name,
            'new_value': new_text,
            'snapshot': snapshot,
        },
        created_by=getattr(user, 'id', None),
        created_by_name=history_user_name(user),
        can_rectify=bool(can_restore) and not is_audit_event,
    )
    return row


def record_model_changes(*, su_id, category, original_data, updated_data, user, record_type='attribute'):
    records = []
    for field, new_value in updated_data.items():
        old_value = original_data.get(field)
        if _history_values_equal(old_value, new_value):
            continue
        records.append(record_history(
            su_id=su_id,
            record_type=record_type,
            action=Parcel_History_Model.ACTION_UPDATE,
            user=user,
            category=category,
            field_name=field,
            old_value=old_value,
            new_value=new_value,
            snapshot={
                'category': category,
                'field_name': field,
                'old_value': _history_value(old_value),
                'new_value': _history_value(new_value),
            },
            can_restore=True,
        ))
    return records
