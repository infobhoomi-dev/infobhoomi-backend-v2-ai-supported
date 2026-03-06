from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0399_drop_assessment_user_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE la_ls_land_unit DROP COLUMN IF EXISTS user_id;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
