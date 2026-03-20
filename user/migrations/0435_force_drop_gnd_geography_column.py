"""
Migration 0435 — Force-drop any geography-typed column from sl_gnd_10m.

The column name contains a non-printable/non-breaking space character making
it impossible to reference by a hardcoded string literal.  This migration
detects and drops it by type (geography) rather than by name.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0434_drop_gnd_geography_column'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                DECLARE
                    col_name TEXT;
                BEGIN
                    -- Find every geography-typed column in sl_gnd_10m
                    FOR col_name IN
                        SELECT a.attname
                        FROM   pg_catalog.pg_attribute  a
                        JOIN   pg_catalog.pg_class       c ON c.oid = a.attrelid
                        JOIN   pg_catalog.pg_type        t ON t.oid = a.atttypid
                        WHERE  c.relname   = 'sl_gnd_10m'
                          AND  t.typname   = 'geography'
                          AND  a.attnum    > 0
                          AND  NOT a.attisdropped
                    LOOP
                        RAISE NOTICE 'sl_gnd_10m: dropping geography column: [%]', col_name;
                        EXECUTE format('ALTER TABLE sl_gnd_10m DROP COLUMN %I', col_name);
                    END LOOP;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
