from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0415_add_geom_to_sl_gnd_10m'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE la_ls_land_unit DROP COLUMN IF EXISTS gnd_id;',
            reverse_sql='ALTER TABLE la_ls_land_unit ADD COLUMN gnd_id integer;',
        ),
    ]
