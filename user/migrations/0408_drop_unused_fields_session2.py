"""
Migration 0408 — Drop unused columns (Session 2 audit)
=======================================================
Tables cleaned:
  la_ls_land_unit  — 3 dead columns (boundary_type, crs, perimeter)
  sl_organization  — 3 dead columns (org_parent_type, org_group_type, org_overview)
  sl_party         — 5 dead demographic columns (edu, religion, race, married_status, health_status)

All dropped columns were 100% NULL with no serializer/view references
(or serializer-only with confirmed zero usage).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0407_drop_unused_fields_session1'),
    ]

    operations = [

        # ── la_ls_land_unit ─────────────────────────────────────────────────
        migrations.RemoveField(model_name='la_ls_land_unit_model', name='boundary_type'),
        migrations.RemoveField(model_name='la_ls_land_unit_model', name='crs'),
        migrations.RemoveField(model_name='la_ls_land_unit_model', name='perimeter'),

        # ── sl_organization ──────────────────────────────────────────────────
        migrations.RemoveField(model_name='sl_organization_model', name='org_parent_type'),
        migrations.RemoveField(model_name='sl_organization_model', name='org_group_type'),
        migrations.RemoveField(model_name='sl_organization_model', name='org_overview'),

        # ── sl_party (registered in migrations as 'party_model') ─────────────
        migrations.RemoveField(model_name='party_model', name='edu'),
        migrations.RemoveField(model_name='party_model', name='religion'),
        migrations.RemoveField(model_name='party_model', name='race'),
        migrations.RemoveField(model_name='party_model', name='married_status'),
        migrations.RemoveField(model_name='party_model', name='health_status'),
    ]
