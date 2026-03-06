"""
Migration 0407 — Drop unused columns (Session 1 audit)
=======================================================
Tables cleaned:
  survey_rep        — 6 dead columns (original_* x5, infobhoomi_id)
  tax_info          — 5 dead columns (external_tax_id, tax_no, date_valuation, tax_name, tax_out_balance)
  la_spatial_unit   — 6 dead columns + UniqueConstraint (reference_id, ladm_value, util_obj_id,
                      util_obj_code, level_id FK, parcel_status)
  la_sp_fire_rescue — 3 dead columns (officer, issued_date, expired_date)
  la_spatial_source — 2 dead columns (date_expire, surveyor_tp)

All dropped columns were 100% NULL (or >98% NULL with zero serializer/view references).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0406_assessment_ensure_user_id'),
    ]

    operations = [

        # ── survey_rep ──────────────────────────────────────────────────────
        migrations.RemoveField(model_name='Survey_Rep_DATA_Model', name='infobhoomi_id'),
        migrations.RemoveField(model_name='Survey_Rep_DATA_Model', name='original_point_id'),
        migrations.RemoveField(model_name='Survey_Rep_DATA_Model', name='original_x_coord'),
        migrations.RemoveField(model_name='Survey_Rep_DATA_Model', name='original_y_coord'),
        migrations.RemoveField(model_name='Survey_Rep_DATA_Model', name='original_z_coord'),
        migrations.RemoveField(model_name='Survey_Rep_DATA_Model', name='original_code'),

        # ── tax_info ────────────────────────────────────────────────────────
        migrations.RemoveField(model_name='Tax_Info_Model', name='external_tax_id'),
        migrations.RemoveField(model_name='Tax_Info_Model', name='tax_no'),
        migrations.RemoveField(model_name='Tax_Info_Model', name='date_valuation'),
        migrations.RemoveField(model_name='Tax_Info_Model', name='tax_name'),
        migrations.RemoveField(model_name='Tax_Info_Model', name='tax_out_balance'),

        # ── la_spatial_unit — remove constraint before dropping columns ──────
        migrations.RemoveConstraint(
            model_name='LA_Spatial_Unit_Model',
            name='util_obj_id_util_obj_code',
        ),
        migrations.RemoveField(model_name='LA_Spatial_Unit_Model', name='reference_id'),
        migrations.RemoveField(model_name='LA_Spatial_Unit_Model', name='ladm_value'),
        migrations.RemoveField(model_name='LA_Spatial_Unit_Model', name='util_obj_id'),
        migrations.RemoveField(model_name='LA_Spatial_Unit_Model', name='util_obj_code'),
        migrations.RemoveField(model_name='LA_Spatial_Unit_Model', name='level'),
        migrations.RemoveField(model_name='LA_Spatial_Unit_Model', name='parcel_status'),

        # ── la_sp_fire_rescue ────────────────────────────────────────────────
        migrations.RemoveField(model_name='LA_SP_Fire_Rescue_Model', name='officer'),
        migrations.RemoveField(model_name='LA_SP_Fire_Rescue_Model', name='issued_date'),
        migrations.RemoveField(model_name='LA_SP_Fire_Rescue_Model', name='expired_date'),

        # ── la_spatial_source ────────────────────────────────────────────────
        migrations.RemoveField(model_name='LA_Spatial_Source_Model', name='date_expire'),
        migrations.RemoveField(model_name='LA_Spatial_Source_Model', name='surveyor_tp'),
    ]
