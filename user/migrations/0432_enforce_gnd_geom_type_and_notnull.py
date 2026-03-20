"""
Migration 0432 — Copy GND data from "geom " (geography) into geom (geometry),
drop the stale geography column, and enforce NOT NULL.

Migration 0431's dynamic detection silently skipped the copy.  This migration
uses a direct hardcoded UPDATE inside an exception-safe block so the copy always
runs if the column exists, regardless of pg_attribute encoding quirks.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0431_fix_gnd_geom_from_geography_column'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Step 1: Copy "geom " (geography) → geom (geometry)
                -- The inner BEGIN/EXCEPTION block catches "undefined_column"
                -- gracefully if "geom " was already dropped by a previous run.
                DO $$
                DECLARE
                    row_count INT;
                BEGIN
                    BEGIN
                        UPDATE sl_gnd_10m
                        SET    geom = "geom "::geometry
                        WHERE  "geom " IS NOT NULL;

                        GET DIAGNOSTICS row_count = ROW_COUNT;
                        RAISE NOTICE 'sl_gnd_10m: copied % rows from "geom " into geom.', row_count;

                    EXCEPTION WHEN undefined_column THEN
                        RAISE NOTICE 'sl_gnd_10m: "geom " column not found — already dropped, skipping copy.';
                    END;
                END $$;

                -- Step 2: Drop the stale "geom " (geography) column
                DO $$
                BEGIN
                    BEGIN
                        ALTER TABLE sl_gnd_10m DROP COLUMN "geom ";
                        RAISE NOTICE 'sl_gnd_10m: dropped "geom " (geography) column.';
                    EXCEPTION WHEN undefined_column THEN
                        RAISE NOTICE 'sl_gnd_10m: "geom " already dropped, skipping.';
                    END;
                END $$;

                -- Step 3: Verify all rows have geom before enforcing NOT NULL
                DO $$
                DECLARE
                    null_count INT;
                BEGIN
                    SELECT COUNT(*) INTO null_count FROM sl_gnd_10m WHERE geom IS NULL;
                    IF null_count > 0 THEN
                        RAISE EXCEPTION
                            'sl_gnd_10m still has % rows with NULL geom. '
                            'Check that "geom " (geography) column had data before running this migration.',
                            null_count;
                    END IF;
                END $$;

                -- Step 4: Enforce NOT NULL to match Django model (null=False)
                ALTER TABLE sl_gnd_10m
                    ALTER COLUMN geom SET NOT NULL;

                -- Step 5: Ensure spatial index exists
                CREATE INDEX IF NOT EXISTS sl_gnd_10m_geom_gist_idx
                    ON sl_gnd_10m USING GIST (geom);
            """,
            reverse_sql="""
                ALTER TABLE sl_gnd_10m ALTER COLUMN geom DROP NOT NULL;
                DROP INDEX IF EXISTS sl_gnd_10m_geom_gist_idx;
            """,
        ),
    ]
