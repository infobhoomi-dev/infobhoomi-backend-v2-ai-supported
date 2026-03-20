"""
Migration 0430 — Fix corrupted gnd_id column name in survey_rep.

Root cause: A previous migration or raw SQL created the column with a trailing
non-breaking space (U+00A0), making the actual DB column name 'gnd_id\xa0'
instead of 'gnd_id'. Django ORM writes to 'gnd_id' which does not exist in the
DB, so all rows read back as NULL even when values were written.

Migration 0421 ('ensure_survey_rep_gnd_id') used ADD COLUMN IF NOT EXISTS which
silently passed because 'gnd_id\xa0' and 'gnd_id' are different names — leaving
the corrupted column intact.

Fix steps:
  1. Rename 'gnd_id\xa0' → 'gnd_id' (idempotent: only if the bad column exists
     and the clean column does not).
  2. Backfill NULL gnd_id values for all rows using PostGIS spatial intersection
     against sl_gnd_10m (same logic as migration 0397 but covers all layer_ids).
  3. Fall back to gid=1 for any rows where no GND polygon intersects.
  4. Enforce NOT NULL to match the intended model constraint.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0429_backfill_calculated_area'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Step 1: Rename corrupted column only if it exists and the
                --         clean column does not yet exist.
                DO $$
                BEGIN
                    -- Rename 'gnd_id<NBSP>' to 'gnd_id' if present
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'survey_rep'
                          AND column_name = 'gnd_id\u00a0'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'survey_rep'
                          AND column_name = 'gnd_id'
                    ) THEN
                        EXECUTE 'ALTER TABLE survey_rep RENAME COLUMN "gnd_id\u00a0" TO gnd_id';
                    END IF;

                    -- If both exist (clean was added by migration 0421), copy
                    -- non-null values from corrupted into clean, then drop bad.
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'survey_rep'
                          AND column_name = 'gnd_id\u00a0'
                    ) AND EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'survey_rep'
                          AND column_name = 'gnd_id'
                    ) THEN
                        EXECUTE $q$
                            UPDATE survey_rep
                            SET gnd_id = sr_bad."gnd_id\u00a0"
                            FROM survey_rep sr_bad
                            WHERE survey_rep.id = sr_bad.id
                              AND survey_rep.gnd_id IS NULL
                              AND sr_bad."gnd_id\u00a0" IS NOT NULL
                        $q$;
                        EXECUTE 'ALTER TABLE survey_rep DROP COLUMN "gnd_id\u00a0"';
                    END IF;
                END $$;

                -- Step 2: Backfill NULL gnd_id for all rows using spatial
                --         intersection against the GND boundary table.
                UPDATE survey_rep sr
                SET gnd_id = (
                    SELECT g.gid
                    FROM sl_gnd_10m g
                    WHERE ST_Intersects(sr.geom, g.geom)
                    ORDER BY ST_Area(ST_Intersection(sr.geom::geometry, g.geom::geometry)) DESC
                    LIMIT 1
                )
                WHERE sr.gnd_id IS NULL
                  AND sr.geom IS NOT NULL;

                -- Step 3: Fallback — any remaining NULLs get gnd_id = 1
                UPDATE survey_rep
                SET gnd_id = 1
                WHERE gnd_id IS NULL;

                -- Step 4: Enforce NOT NULL
                ALTER TABLE survey_rep
                    ALTER COLUMN gnd_id SET NOT NULL;
            """,
            reverse_sql="""
                ALTER TABLE survey_rep ALTER COLUMN gnd_id DROP NOT NULL;
            """,
        ),
    ]
