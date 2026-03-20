"""
Migration 0429 — Backfill calculated_area for all survey_rep rows.

Root cause: The calculated_area column (formerly 'area') was populated by the
frontend sending 0 or no value. The backend auto-calculation was added later,
so all existing records retained 0.0000.

Fix: Use PostGIS ST_Area (projected to EPSG:5235 Sri Lanka Grid) to recompute
the area in square metres for every polygon, and ST_Length for every linestring.
Only rows with NULL or zero calculated_area are updated — rows with valid
existing values are left untouched.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0428_fix_user_roles_org_id_drift'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Polygons / MultiPolygons → area in sq.m via Sri Lanka Grid projection
                UPDATE survey_rep
                SET calculated_area = ROUND(
                    CAST(ST_Area(ST_Transform(geom::geometry, 5235)) AS numeric), 4
                )
                WHERE geom IS NOT NULL
                  AND geom_type IN ('polygon', 'multipolygon')
                  AND (calculated_area IS NULL OR calculated_area = 0);

                -- LineStrings / MultiLineStrings → length in metres
                UPDATE survey_rep
                SET calculated_area = ROUND(
                    CAST(ST_Length(ST_Transform(geom::geometry, 5235)) AS numeric), 4
                )
                WHERE geom IS NOT NULL
                  AND geom_type IN ('linestring', 'multilinestring')
                  AND (calculated_area IS NULL OR calculated_area = 0);
            """,
            reverse_sql="""
                -- Cannot recover original zeros vs genuinely zero areas; no-op reverse.
                SELECT 1;
            """,
        ),
    ]
