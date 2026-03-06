from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0400_drop_la_ls_land_unit_user_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE survey_rep_geom_history DROP COLUMN IF EXISTS gnd_id;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
