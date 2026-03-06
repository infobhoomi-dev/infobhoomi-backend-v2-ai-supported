"""
Migration 0412 — Fix tax_info.date_valuation NOT NULL mismatch
==============================================================
Migration 0407 dropped date_valuation from Django's model state but the
DB column remained (NOT NULL, no default). Migration 0411 tried to re-add it
as null=True but the ADD COLUMN was a no-op since the column already existed,
leaving the DB column still NOT NULL. This migration aligns the DB with the
model by dropping the NOT NULL constraint.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0411_tax_info_model_date_valuation'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE tax_info ALTER COLUMN date_valuation DROP NOT NULL;',
            reverse_sql='ALTER TABLE tax_info ALTER COLUMN date_valuation SET NOT NULL;',
        ),
    ]
