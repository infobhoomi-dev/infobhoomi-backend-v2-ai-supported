"""Backfill Role_Permission rows for the 3D Cadastre permissions (254-263).

Problem: migration 0016 seeded the permission CATALOG (permission_list), but
the role editor lists a role's permissions from ROLE_PERMISSION (per-role rows).
Roles that already existed before 0016 have no role_permission rows for the new
ids, so the "3D Cadastre" actions don't appear / have no CRUD checkboxes for
those roles. Role creation seeds role_permission by copying view/add/edit/delete
from the catalog (type=3 → for both admin & user roles); we replicate that here
for every existing role, idempotently.
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
    for role in Role.objects.all():
        # which of the new perms this role already has (idempotent re-run)
        existing = set(
            RolePerm.objects.filter(
                role_id=role, permission_id__in=NEW_PERM_IDS
            ).values_list("permission_id", flat=True)
        )
        for p in perms:
            # type=3 applies to both admin and user roles (mirrors role-create logic)
            if p.type == 3 and role.role_type in ("admin", "user") and p.permission_id not in existing:
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
    RolePerm.objects.filter(permission_id__in=NEW_PERM_IDS).delete()


class Migration(migrations.Migration):
    dependencies = [("user", "0016_3d_cadastre_permissions")]
    operations = [migrations.RunPython(backfill, unbackfill)]
