from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0398_delete_sl_group_party_members_model'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE assessment DROP COLUMN IF EXISTS user_id;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
