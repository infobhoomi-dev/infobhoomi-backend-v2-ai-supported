"""
Migration 0410 — Drop unused columns (Session 4 audit)
=======================================================
Tables cleaned:
  assessment — ass_div (100% NULL across 3,604 rows, never populated, not in serializer)

All other 0-row tables reviewed were confirmed as false positives (properly designed
planned features with NOT NULL constraints on required fields).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0409_drop_gnd_id_from_lookup_tables'),
    ]

    operations = [
        migrations.RemoveField(model_name='assessment_model', name='ass_div'),
    ]
