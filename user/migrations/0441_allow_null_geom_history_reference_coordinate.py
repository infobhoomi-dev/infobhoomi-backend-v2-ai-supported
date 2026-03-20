"""
Migration 0441 — Allow NULL in survey_rep_geom_history.reference_coordinate.

The Django model (Survey_Rep_Geom_History_Model) declares reference_coordinate
as CharField(max_length=50, null=True), but the live DB column still has a
NOT NULL constraint from before migration 0438 converted it to varchar(50).
This causes INSERT failures when no CRS string is provided.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0440_cleanup_survey_rep_duplicate_columns'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE survey_rep_geom_history
                    ALTER COLUMN reference_coordinate DROP NOT NULL;
            """,
            reverse_sql="""
                UPDATE survey_rep_geom_history
                SET reference_coordinate = 'EPSG:4326'
                WHERE reference_coordinate IS NULL;

                ALTER TABLE survey_rep_geom_history
                    ALTER COLUMN reference_coordinate SET NOT NULL;
            """,
        ),
    ]
