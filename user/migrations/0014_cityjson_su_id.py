from django.db import migrations, models


class Migration(migrations.Migration):
    """Add parcel/building link + metadata to CityJSON_Model so a building's
    CityJSON can be fetched by su_id (3D cadastre import pipeline, P2)."""

    dependencies = [
        ("user", "0013_create_geotag"),
    ]

    operations = [
        migrations.AddField(
            model_name="cityjson_model",
            name="su_id",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="cityjson_model",
            name="name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="cityjson_model",
            name="source_file",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
