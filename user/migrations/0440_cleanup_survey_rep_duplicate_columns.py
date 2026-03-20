"""
Migration 0440 — Drop duplicate/corrupted columns from survey_rep.

Live DB has three problems discovered via information_schema inspection:

1. 'su_id\u00a0' (su_id + U+00A0 non-breaking space) — corrupted duplicate of
   the clean 'su_id' column added by migration 0439. Same root cause as the
   old 'gnd_id\u00a0' bug fixed in migration 0430.

2. 'gndid' (no underscore) — corrupted duplicate of the correct 'gnd_id'
   column. Values are copied to 'gnd_id' before dropping.

3. 'gnd_id' is nullable (YES) but the model declares null=False. After
   merging data from 'gndid' and dropping it, NOT NULL is enforced (with
   gid=1 fallback for any truly unresolvable NULLs).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0439_restore_survey_rep_su_id_column'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- ── 1. Drop corrupted su_id + U+00A0 column ─────────────────────────
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name  = 'survey_rep'
                          AND column_name = 'su_id\u00a0'
                    ) THEN
                        EXECUTE 'ALTER TABLE survey_rep DROP COLUMN "su_id\u00a0"';
                        RAISE NOTICE 'survey_rep: dropped corrupted "su_id<NBSP>" column.';
                    ELSE
                        RAISE NOTICE 'survey_rep: "su_id<NBSP>" not present, nothing to drop.';
                    END IF;
                END $$;

                -- ── 2. Merge gndid → gnd_id, then drop gndid ─────────────────────────
                DO $$
                BEGIN
                    -- Only act if the corrupted column still exists
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name  = 'survey_rep'
                          AND column_name = 'gndid'
                    ) THEN
                        -- Copy non-null values into the clean column where it is still NULL
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name  = 'survey_rep'
                              AND column_name = 'gnd_id'
                        ) THEN
                            UPDATE survey_rep
                            SET    gnd_id = gndid
                            WHERE  gnd_id IS NULL
                              AND  gndid  IS NOT NULL;
                        END IF;

                        EXECUTE 'ALTER TABLE survey_rep DROP COLUMN gndid';
                        RAISE NOTICE 'survey_rep: dropped corrupted "gndid" column.';
                    ELSE
                        RAISE NOTICE 'survey_rep: "gndid" not present, nothing to drop.';
                    END IF;
                END $$;

                -- ── 3. Enforce NOT NULL on gnd_id ─────────────────────────────────────
                -- Fallback: any remaining NULLs (no matching GND polygon) → gid = 1
                UPDATE survey_rep SET gnd_id = 1 WHERE gnd_id IS NULL;

                ALTER TABLE survey_rep ALTER COLUMN gnd_id SET NOT NULL;
            """,
            reverse_sql="""
                ALTER TABLE survey_rep ALTER COLUMN gnd_id DROP NOT NULL;
            """,
        ),
    ]
