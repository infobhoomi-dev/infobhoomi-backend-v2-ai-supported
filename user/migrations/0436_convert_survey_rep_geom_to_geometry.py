"""
Migration 0436 — Convert survey_rep.geom from geography to geometry type.

The survey_rep table's geom column was created as geography instead of the
geometry type expected by the Django model (gismodels.GeometryField).

geography and geometry both store WGS84 coordinates (SRID 4326), so the cast
is lossless.  ALTER COLUMN TYPE ... USING geom::geometry converts in-place
without touching any other columns or data.

Also converts reference_coordinate for the same reason if needed.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0435_force_drop_gnd_geography_column'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Convert geom column if it is currently geography type
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM   pg_catalog.pg_attribute  a
                        JOIN   pg_catalog.pg_class       c ON c.oid = a.attrelid
                        JOIN   pg_catalog.pg_type        t ON t.oid = a.atttypid
                        WHERE  c.relname  = 'survey_rep'
                          AND  a.attname  = 'geom'
                          AND  t.typname  = 'geography'
                          AND  NOT a.attisdropped
                    ) THEN
                        RAISE NOTICE 'survey_rep.geom is geography — converting to geometry(Geometry,4326)';
                        ALTER TABLE survey_rep
                            ALTER COLUMN geom TYPE geometry(Geometry, 4326)
                            USING geom::geometry;
                        RAISE NOTICE 'survey_rep.geom converted successfully.';
                    ELSE
                        RAISE NOTICE 'survey_rep.geom is already geometry — no change needed.';
                    END IF;
                END $$;

                -- Convert reference_coordinate column if it is currently geography type
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM   pg_catalog.pg_attribute  a
                        JOIN   pg_catalog.pg_class       c ON c.oid = a.attrelid
                        JOIN   pg_catalog.pg_type        t ON t.oid = a.atttypid
                        WHERE  c.relname  = 'survey_rep'
                          AND  a.attname  = 'reference_coordinate'
                          AND  t.typname  = 'geography'
                          AND  NOT a.attisdropped
                    ) THEN
                        RAISE NOTICE 'survey_rep.reference_coordinate is geography — converting to geometry(Geometry,4326)';
                        ALTER TABLE survey_rep
                            ALTER COLUMN reference_coordinate TYPE geometry(Geometry, 4326)
                            USING reference_coordinate::geometry;
                        RAISE NOTICE 'survey_rep.reference_coordinate converted successfully.';
                    ELSE
                        RAISE NOTICE 'survey_rep.reference_coordinate is already geometry — no change needed.';
                    END IF;
                END $$;

                -- Re-create spatial indexes after type change
                CREATE INDEX IF NOT EXISTS survey_rep_geom_gist_idx
                    ON survey_rep USING GIST (geom);

                CREATE INDEX IF NOT EXISTS survey_rep_ref_coord_gist_idx
                    ON survey_rep USING GIST (reference_coordinate)
                    WHERE reference_coordinate IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
