"""
Migration 0456 — Rename any "gndid*" column (with trailing space/NBSP) to "gndid".

0455 ran but its IF EXISTS checks silently skipped because information_schema
encodes non-standard whitespace differently. This migration uses pg_attribute
directly and matches any column starting with 'gndid' that is not exactly 'gndid'.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0455_fix_survey_rep_gndid_trailing_space'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $block$
                DECLARE
                    col_name TEXT;
                BEGIN
                    SELECT attname INTO col_name
                    FROM   pg_attribute a
                    JOIN   pg_class     c ON c.oid = a.attrelid
                    WHERE  c.relname       = 'survey_rep'
                      AND  a.attname      LIKE 'gndid%'
                      AND  a.attname      != 'gndid'
                      AND  NOT a.attisdropped
                    LIMIT 1;

                    IF col_name IS NOT NULL THEN
                        EXECUTE format(
                            'ALTER TABLE survey_rep RENAME COLUMN %I TO gndid',
                            col_name
                        );
                        RAISE NOTICE 'survey_rep: renamed column "%" to gndid', col_name;
                    ELSE
                        RAISE NOTICE 'survey_rep: no stale gndid variant found, nothing to rename';
                    END IF;
                END $block$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
