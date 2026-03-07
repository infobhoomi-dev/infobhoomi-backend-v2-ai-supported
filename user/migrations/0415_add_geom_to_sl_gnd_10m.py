"""
Migration 0415 — Add geom column to sl_gnd_10m
===============================================
The sl_gnd_10m table is managed=False (populated externally).
Its geom column was never persisted to the local DB.
This migration adds the column so the GND boundary layer can be served.
Data is loaded separately via the load_gnd_geom management command.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0414_restore_survey_rep_gnd_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE sl_gnd_10m
                ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326);
            """,
            reverse_sql="""
                ALTER TABLE sl_gnd_10m
                DROP COLUMN IF EXISTS geom;
            """,
        ),
    ]
