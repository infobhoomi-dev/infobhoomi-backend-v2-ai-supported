from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0401_drop_survey_rep_geom_history_gnd_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE layers DROP COLUMN IF EXISTS gnd_id;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
