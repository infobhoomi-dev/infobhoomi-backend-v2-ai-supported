from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0416_drop_gnd_id_from_la_ls_land_unit'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE la_ls_utinet_lu DROP COLUMN IF EXISTS gnd_id;',
            reverse_sql='ALTER TABLE la_ls_utinet_lu ADD COLUMN gnd_id integer;',
        ),
    ]
