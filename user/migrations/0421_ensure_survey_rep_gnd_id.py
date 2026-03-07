"""
Migration 0421 — Ensure survey_rep.gnd_id exists

Migration 0414 already restored this column but the DB on this instance
was missing it again (the column silently disappeared from the dump).
This migration is idempotent (IF NOT EXISTS) so it is safe to re-apply.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0420_fix_missing_columns'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE survey_rep ADD COLUMN IF NOT EXISTS gnd_id integer;',
            reverse_sql='ALTER TABLE survey_rep DROP COLUMN IF EXISTS gnd_id;',
        ),
    ]
