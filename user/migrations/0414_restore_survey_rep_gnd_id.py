"""
Migration 0414 — Restore gnd_id column to survey_rep table
===========================================================
The gnd_id column was accidentally dropped from survey_rep directly in the DB
without a corresponding Django migration. Django's migration state still
includes it, so we restore it via RunSQL.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0413_fix_survey_rep_ref_id_db_column'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE survey_rep ADD COLUMN IF NOT EXISTS gnd_id integer;',
            reverse_sql='ALTER TABLE survey_rep DROP COLUMN IF EXISTS gnd_id;',
        ),
    ]
