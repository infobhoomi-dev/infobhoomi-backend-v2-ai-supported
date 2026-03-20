"""
Migration 0434 — Drop the stale "geom " (geography) column from sl_gnd_10m.

Migration 0432 copied the geography data into geom (geometry) and enforced
NOT NULL, but the DROP of "geom " was silently swallowed by the exception
handler. This migration drops it directly.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0433_alter_sl_gnd_10m_model_options_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE sl_gnd_10m DROP COLUMN IF EXISTS "geom ";
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
