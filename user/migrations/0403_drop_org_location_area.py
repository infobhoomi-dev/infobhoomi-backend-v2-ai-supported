from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0402_drop_layers_gnd_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE org_location DROP COLUMN IF EXISTS area;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
