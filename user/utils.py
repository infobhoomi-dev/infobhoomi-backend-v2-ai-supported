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

from rest_framework.response import Response
from rest_framework import status

from .models import User_Roles_Model, Role_Permission_Model


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
