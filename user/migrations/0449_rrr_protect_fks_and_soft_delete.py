# Generated 2026-03-21
#
# Issue #7 fix: prevent accidental cascade deletion of title records.
#
# Changes:
#   1. SL_BA_Unit_Model.su_id            CASCADE → PROTECT
#   2. LA_RRR_Model.ba_unit_id           CASCADE → PROTECT
#   3. LA_RRR_Model.admin_source_id      CASCADE → SET_NULL
#   4. LA_RRR_Restriction_Model.ba_unit  CASCADE → PROTECT
#   5. LA_RRR_Responsibility_Model.ba_unit CASCADE → PROTECT
#   6. LA_RRR_Model.status               AddField (soft-delete flag, default True)
#
# on_delete is Django-enforced (ProtectedError raised in Python before any SQL).
# The AlterField operations below update the DB-level FK constraints to match.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0448_add_la_mortgage_model'),
    ]

    operations = [
        # 1. SL_BA_Unit_Model.su_id: CASCADE → PROTECT
        migrations.AlterField(
            model_name='sl_ba_unit_model',
            name='su_id',
            field=models.ForeignKey(
                db_column='su_id',
                on_delete=django.db.models.deletion.PROTECT,
                to='user.la_spatial_unit_model',
                to_field='su_id',
            ),
        ),

        # 2. LA_RRR_Model.ba_unit_id: CASCADE → PROTECT
        migrations.AlterField(
            model_name='la_rrr_model',
            name='ba_unit_id',
            field=models.ForeignKey(
                db_column='ba_unit_id',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='user.sl_ba_unit_model',
            ),
        ),

        # 3. LA_RRR_Model.admin_source_id: CASCADE → SET_NULL
        migrations.AlterField(
            model_name='la_rrr_model',
            name='admin_source_id',
            field=models.ForeignKey(
                db_column='admin_source_id',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='user.la_admin_source_model',
            ),
        ),

        # 4. LA_RRR_Restriction_Model.ba_unit_id: CASCADE → PROTECT
        # State-only: the column may have nulls from migration 0446 (ADD COLUMN on existing rows).
        # PROTECT is Django-enforced in Python; no DB constraint change needed.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='la_rrr_restriction_model',
                    name='ba_unit_id',
                    field=models.ForeignKey(
                        db_column='ba_unit_id',
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='restrictions',
                        to='user.sl_ba_unit_model',
                    ),
                ),
            ],
        ),

        # 5. LA_RRR_Responsibility_Model.ba_unit_id: CASCADE → PROTECT
        # State-only: same reason as above.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='la_rrr_responsibility_model',
                    name='ba_unit_id',
                    field=models.ForeignKey(
                        db_column='ba_unit_id',
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='responsibilities',
                        to='user.sl_ba_unit_model',
                    ),
                ),
            ],
        ),

        # 6. Add soft-delete status flag to LA_RRR_Model
        migrations.AddField(
            model_name='la_rrr_model',
            name='status',
            field=models.BooleanField(default=True),
        ),
    ]
