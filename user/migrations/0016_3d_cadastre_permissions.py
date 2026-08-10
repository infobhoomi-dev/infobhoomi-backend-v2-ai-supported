"""Seed the '3D Cadastre' permission category (ids 254+).

These rows make the new 3D-cadastre actions appear in the Admin Panel role
editor (which renders from permission_list) and give the backend stable
permission_ids to gate the new endpoints via Role_Permission_Model.

type=3 = standard feature permission (same as Building/Land/Map Area rows).
The view/add/edit/delete booleans here are template defaults (which flags
apply to the row); the actual per-role grants live in role_permission.
"""
from django.db import migrations


CATEGORY = "3D Cadastre"
TYPE = 3

# (permission_id, sub_category, permission_name, view, add, edit, delete)
ROWS = [
    # — Import / lifecycle —
    (254, "Import",      "Import 3D Object (IFC/CityJSON)", True, True,  False, False),
    (255, "Import",      "Delete 3D Building",              True, False, False, True),
    # — Viewing —
    (256, "Viewer",      "View Building in 3D",             True, False, False, False),
    (257, "Viewer",      "City 3D View (admin area)",       True, False, False, False),
    (258, "Viewer",      "Search 3D Objects",               True, False, False, False),
    # — Legal Space / apartment composition —
    (259, "Composition", "Open Unit Composition",           True, False, False, False),
    (260, "Composition", "Compose Legal Space Building Unit", True, True, True,  False),
    (261, "Composition", "Edit Legal Space Type",           True, False, True,  False),
    (262, "Composition", "Edit Cadastral ID",               True, False, True,  False),
    (263, "Composition", "Reassign / Unassign Units",       True, False, True,  False),
]


def seed(apps, schema_editor):
    P = apps.get_model("user", "Permission_List_Model")
    for pid, sub, name, v, a, e, d in ROWS:
        P.objects.update_or_create(
            permission_id=pid,
            defaults=dict(
                category=CATEGORY, sub_category=sub, permission_name=name,
                view=v, add=a, edit=e, delete=d, status=True, type=TYPE,
                remark="3D Cadastre (auto-seeded)",
            ),
        )


def unseed(apps, schema_editor):
    P = apps.get_model("user", "Permission_List_Model")
    P.objects.filter(permission_id__in=[r[0] for r in ROWS]).delete()


class Migration(migrations.Migration):
    dependencies = [("user", "0015_lsbu_composition_fields")]
    operations = [migrations.RunPython(seed, unseed)]
