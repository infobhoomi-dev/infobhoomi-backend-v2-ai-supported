from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0405_assessment_model_add_user_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE assessment
                ADD COLUMN IF NOT EXISTS user_id integer NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
