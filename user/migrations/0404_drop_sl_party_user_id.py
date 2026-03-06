from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0403_drop_org_location_area'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE sl_party DROP COLUMN IF EXISTS user_id;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
