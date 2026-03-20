"""
Migration 0439 — Restore missing su_id column in survey_rep table.

Root cause: The su_id column (FK to la_spatial_unit.su_id) is defined in the
Django model (Survey_Rep_DATA_Model) but is absent from the live database,
causing INSERT failures with:
  column "su_id" of relation "survey_rep" does not exist

The column existed in the 2026-03-13 backup as 'su_id integer' (nullable).
It was likely dropped manually or the DB was restored from an older snapshot.
This migration adds it back idempotently.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0438_alter_survey_rep_data_model_reference_coordinate_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE survey_rep
                    ADD COLUMN IF NOT EXISTS su_id integer;
            """,
            reverse_sql="""
                ALTER TABLE survey_rep
                    DROP COLUMN IF EXISTS su_id;
            """,
        ),
    ]
