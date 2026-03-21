# Generated 2026-03-21
#
# Issue #10 fix: remove null=True from FKs and fields that must always have a value.
#
# Fields changed (state-only — DB columns stay nullable until a data-cleanup
# confirms no null rows exist, at which point a follow-up migration can add
# the NOT NULL constraint via RunSQL ALTER COLUMN … SET NOT NULL):
#
#   LA_RRR_Model.ba_unit_id    null=True → not null
#   LA_RRR_Model.rrr_type      null=True → not null
#   Party_Roles_Model.pid      null=True → not null
#   Party_Roles_Model.rrr_id   null=True → not null
#
# admin_source_id is intentionally left nullable (SET_NULL on doc removal).

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0450_add_la_rrr_audit'),
    ]

    operations = [
        # ── LA_RRR_Model ─────────────────────────────────────────────────────────

        # ba_unit_id: remove null=True (state only — DB column stays nullable)
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='la_rrr_model',
                    name='ba_unit_id',
                    field=models.ForeignKey(
                        db_column='ba_unit_id',
                        on_delete=django.db.models.deletion.PROTECT,
                        to='user.sl_ba_unit_model',
                    ),
                ),
            ],
        ),

        # rrr_type: remove null=True (state only)
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='la_rrr_model',
                    name='rrr_type',
                    field=models.CharField(max_length=50),
                ),
            ],
        ),

        # ── Party_Roles_Model ─────────────────────────────────────────────────────

        # pid: remove null=True (state only)
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='party_roles_model',
                    name='pid',
                    field=models.ForeignKey(
                        db_column='pid',
                        on_delete=django.db.models.deletion.CASCADE,
                        to='user.party_model',
                    ),
                ),
            ],
        ),

        # rrr_id: remove null=True (state only)
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='party_roles_model',
                    name='rrr_id',
                    field=models.ForeignKey(
                        db_column='rrr_id',
                        on_delete=django.db.models.deletion.CASCADE,
                        to='user.la_rrr_model',
                    ),
                ),
            ],
        ),
    ]
