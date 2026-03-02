# LADM compliance: share and share_type belong to the party's participation
# in an RRR (Party_Roles_Model), not to the RRR record itself.
# This migration moves those columns from la_rrr → sl_party_roles.

from django.db import migrations, models


def copy_share_to_party_roles(apps, schema_editor):
    LA_RRR_Model = apps.get_model('user', 'LA_RRR_Model')
    Party_Roles_Model = apps.get_model('user', 'Party_Roles_Model')

    for rrr in LA_RRR_Model.objects.all():
        party_role = Party_Roles_Model.objects.filter(rrr_id=rrr).first()
        if party_role:
            party_role.share_type = rrr.share_type
            party_role.share = rrr.share
            party_role.save(update_fields=['share_type', 'share'])


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0392_alter_history_spartialunit_attrib_model_su_id_and_more'),
    ]

    operations = [
        # Step 1: add new columns to sl_party_roles (nullable so existing rows are safe)
        migrations.AddField(
            model_name='party_roles_model',
            name='share_type',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='party_roles_model',
            name='share',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),

        # Step 2: copy existing share data from la_rrr → sl_party_roles
        migrations.RunPython(copy_share_to_party_roles, migrations.RunPython.noop),

        # Step 3: drop the columns from la_rrr
        migrations.RemoveField(
            model_name='la_rrr_model',
            name='share_type',
        ),
        migrations.RemoveField(
            model_name='la_rrr_model',
            name='share',
        ),
    ]
