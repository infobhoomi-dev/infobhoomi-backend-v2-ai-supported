from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0452_survey_rep_gnd_id_db_column'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE sl_gnd_10m
                    ALTER COLUMN geom TYPE geometry(MultiPolygon, 4326)
                    USING geom::geometry;
            """,
            reverse_sql="""
                ALTER TABLE sl_gnd_10m
                    ALTER COLUMN geom TYPE geography(MultiPolygon, 4326)
                    USING geom::geography;
            """,
        ),
    ]
