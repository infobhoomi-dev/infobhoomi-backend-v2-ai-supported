"""Backfill Role_Permission rows for the 3D Cadastre permissions (254-263)
for super_admin-type roles.

Bug: migration 0017 backfilled the 254-263 grants for every existing role,
but its condition was `role.role_type in ("admin", "user")` — it silently
skipped role_type == "super_admin". Super_Admin_Role (role_id=1) therefore
never received these grants, so `_has_3d_perm()` (which requires an explicit
Role_Permission row once a user has any role at all — see user/views/
geo_utils.py) hard-blocks every 3D-cadastre endpoint for super_admin-role
accounts: import, single/city 3D view, search, and the Unit Composition
picker (`bld-3d/units/`, permission_id 259) used by the frontend's Unit
Composition dialog. That is the 403 behind "building units fail to display
in the Unit Composition tab" for a super_admin-role account such as
test.user.

This migration repeats 0017's idempotent backfill, scoped to role_type ==
"super_admin" only, so it is safe to run even if 0017 is re-applied later.
"""
from django.db import migrations


NEW_PERM_IDS = list(range(254, 264))  # 254..263


def backfill(apps, schema_editor):
    Permission = apps.get_model("user", "Permission_List_Model")
    Role = apps.get_model("user", "User_Roles_Model")
    RolePerm = apps.get_model("user", "Role_Permission_Model")

    perms = list(Permission.objects.filter(permission_id__in=NEW_PERM_IDS))
    if not perms:
        return  # 0016 not applied / rows missing — nothing to do

    to_create = []
    for role in Role.objects.filter(role_type="super_admin"):
        existing = set(
            RolePerm.objects.filter(
                role_id=role, permission_id__in=NEW_PERM_IDS
            ).values_list("permission_id", flat=True)
        )
        for p in perms:
            if p.type == 3 and p.permission_id not in existing:
                to_create.append(RolePerm(
                    role_id=role,
                    permission_id=p,
                    view=p.view,
                    add=p.add,
                    edit=p.edit,
                    delete=p.delete,
                ))

    if to_create:
        RolePerm.objects.bulk_create(to_create, ignore_conflicts=True)


def unbackfill(apps, schema_editor):
    RolePerm = apps.get_model("user", "Role_Permission_Model")
    Role = apps.get_model("user", "User_Roles_Model")
    super_admin_role_ids = Role.objects.filter(role_type="super_admin").values_list("role_id", flat=True)
    RolePerm.objects.filter(
        permission_id__in=NEW_PERM_IDS, role_id__in=super_admin_role_ids,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("user", "0019_lsbu_far_coverage")]
    operations = [migrations.RunPython(backfill, unbackfill)]
