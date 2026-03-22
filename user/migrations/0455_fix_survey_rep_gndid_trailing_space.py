"""
Migration 0455 — Rename "gndid " (trailing space) → "gndid" in survey_rep.

Root cause: the column was created with a trailing space/NBSP in its name,
so Django's db_column='gndid' cannot find it at runtime.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0454_convert_survey_rep_geom_to_geometry'),
    ]

    operations = [
        # Handle trailing regular space: "gndid "
        migrations.RunSQL(
            sql="""
                DO $block$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'survey_rep'
                          AND column_name = 'gndid '
                    ) THEN
                        ALTER TABLE survey_rep RENAME COLUMN "gndid " TO gndid;
                        RAISE NOTICE 'survey_rep: renamed gndid(space) to gndid';
                    ELSE
                        RAISE NOTICE 'survey_rep: no trailing-space gndid column found';
                    END IF;
                END $block$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Handle trailing non-breaking space (chr(160)): "gndid\xa0"
        migrations.RunSQL(
            sql="""
                DO $block$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'survey_rep'
                          AND column_name = 'gndid' || chr(160)
                    ) THEN
                        EXECUTE format(
                            'ALTER TABLE survey_rep RENAME COLUMN %I TO gndid',
                            'gndid' || chr(160)
                        );
                        RAISE NOTICE 'survey_rep: renamed gndid(NBSP) to gndid';
                    ELSE
                        RAISE NOTICE 'survey_rep: no NBSP gndid column found';
                    END IF;
                END $block$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
