"""
Migration 0426: Enforce NOT NULL on geom columns to match Django model definitions.

The following geometry columns were manually altered directly in the database to
allow NULLs, bypassing the Django model constraint (null=False). This migration
restores the NOT NULL constraint at the DB level to align with the models.

Affected tables (all confirmed to have 0 existing NULL rows):
  - survey_rep.geom
  - sl_org_area_parent_bndry.geom
  - sl_org_area_child_bndry.geom

Uses SeparateDatabaseAndState: the state operations are no-ops (models already
say null=False); only the database DDL runs to enforce the constraint.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0425_alter_assessment_model_assessment_no'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE survey_rep ALTER COLUMN geom SET NOT NULL;
                        ALTER TABLE sl_org_area_parent_bndry ALTER COLUMN geom SET NOT NULL;
                        ALTER TABLE sl_org_area_child_bndry ALTER COLUMN geom SET NOT NULL;
                    """,
                    reverse_sql="""
                        ALTER TABLE survey_rep ALTER COLUMN geom DROP NOT NULL;
                        ALTER TABLE sl_org_area_parent_bndry ALTER COLUMN geom DROP NOT NULL;
                        ALTER TABLE sl_org_area_child_bndry ALTER COLUMN geom DROP NOT NULL;
                    """,
                ),
            ],
            # No state changes needed — models already declare null=False
            state_operations=[],
        ),
    ]
