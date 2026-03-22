from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0453_convert_gnd_geom_to_geometry'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE survey_rep
                    ALTER COLUMN geom TYPE geometry(Geometry, 4326)
                    USING geom::geometry;
            """,
            reverse_sql="""
                ALTER TABLE survey_rep
                    ALTER COLUMN geom TYPE geography(Geometry, 4326)
                    USING geom::geography;
            """,
        ),
    ]
