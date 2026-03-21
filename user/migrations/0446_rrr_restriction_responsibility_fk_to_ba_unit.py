# Generated 2026-03-21
#
# Issue #3 fix: Restrictions and Responsibilities now link to sl_ba_unit
# (the property) instead of la_rrr (a specific right).
# Uses IF EXISTS / IF NOT EXISTS so the migration is safe regardless of
# whether rrr_id was previously added to the DB.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0445_remove_la_rrr_model_pid'),
    ]

    operations = [
        # ── la_rrr_restriction ──────────────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE la_rrr_restriction
                            DROP COLUMN IF EXISTS rrr_id,
                            ADD COLUMN IF NOT EXISTS ba_unit_id INTEGER
                                REFERENCES sl_ba_unit(ba_unit_id)
                                ON DELETE CASCADE;
                    """,
                    reverse_sql="""
                        ALTER TABLE la_rrr_restriction
                            DROP COLUMN IF EXISTS ba_unit_id,
                            ADD COLUMN IF NOT EXISTS rrr_id INTEGER
                                REFERENCES la_rrr(rrr_id)
                                ON DELETE CASCADE;
                    """,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name='la_rrr_restriction_model',
                    name='rrr_id',
                ),
                migrations.AddField(
                    model_name='la_rrr_restriction_model',
                    name='ba_unit_id',
                    field=models.ForeignKey(
                        db_column='ba_unit_id',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='restrictions',
                        to='user.sl_ba_unit_model',
                    ),
                ),
            ],
        ),

        # ── la_rrr_responsibility ───────────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE la_rrr_responsibility
                            DROP COLUMN IF EXISTS rrr_id,
                            ADD COLUMN IF NOT EXISTS ba_unit_id INTEGER
                                REFERENCES sl_ba_unit(ba_unit_id)
                                ON DELETE CASCADE;
                    """,
                    reverse_sql="""
                        ALTER TABLE la_rrr_responsibility
                            DROP COLUMN IF EXISTS ba_unit_id,
                            ADD COLUMN IF NOT EXISTS rrr_id INTEGER
                                REFERENCES la_rrr(rrr_id)
                                ON DELETE CASCADE;
                    """,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name='la_rrr_responsibility_model',
                    name='rrr_id',
                ),
                migrations.AddField(
                    model_name='la_rrr_responsibility_model',
                    name='ba_unit_id',
                    field=models.ForeignKey(
                        db_column='ba_unit_id',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='responsibilities',
                        to='user.sl_ba_unit_model',
                    ),
                ),
            ],
        ),
    ]
