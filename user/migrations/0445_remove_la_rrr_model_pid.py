# Generated 2026-03-21
#
# Removes the redundant `pid` FK from `la_rrr`.
# Party identity is already stored in `sl_party_roles.pid` (Party_Roles_Model).
# Having it on both tables was a data-redundancy / integrity risk (Issue #1).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0444_party_model_sl_party_type'),
    ]

    operations = [
        # pid column was never present in the la_rrr DB table — state update only.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='la_rrr_model',
                    name='pid',
                ),
            ],
        ),
    ]
