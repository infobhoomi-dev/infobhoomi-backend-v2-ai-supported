# Generated manually 2026-03-03
# Drops the sl_group_party_members table — the model was never wired to any
# view or serializer and has no active usage in the codebase.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0397_backfill_survey_rep_gnd_id'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SL_Group_Party_Members_Model',
        ),
    ]
