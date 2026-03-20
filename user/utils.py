"""
Shared utilities for InfoBhoomi views.

Permission helpers
─────────────────
All views use the same two-step pattern:
  1. Resolve the user's role_id from User_Roles_Model
  2. Check Role_Permission_Model for a specific permission + action

Use these helpers instead of copy-pasting that logic.
"""

from rest_framework.response import Response
from rest_framework import status

from .models import User_Roles_Model, Role_Permission_Model


def get_user_role_id(user_id):
    """
    Return the role_id for *user_id*, or None if the user has no role.

    Usage:
        role_id = get_user_role_id(request.user.id)
        if role_id is None:
            return Response({"error": "User has no assigned roles."}, status=403)
    """
    row = User_Roles_Model.objects.filter(
        users__contains=[user_id]
    ).values('role_id').first()
    return row['role_id'] if row else None


def has_perm(user_id, permission_id, action):
    """
    Return True if the user's role grants *action* on *permission_id*.

    *action* must be one of: 'view', 'add', 'edit', 'delete'.

    Usage:
        if not has_perm(request.user.id, 201, 'add'):
            return perm_denied()
    """
    role_id = get_user_role_id(user_id)
    if role_id is None:
        return False
    return Role_Permission_Model.objects.filter(
        role_id=role_id,
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
