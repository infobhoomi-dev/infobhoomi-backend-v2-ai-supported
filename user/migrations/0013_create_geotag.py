from django.contrib.gis.db import models as gis_models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0012_normalize_audit_event_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeoTag_Model",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("tag_type", models.CharField(choices=[("tree", "Tree"), ("garbage", "Garbage Collection"), ("fire", "Fire Risk"), ("drainage", "Drainage Issue"), ("street_light", "Street Light"), ("road_damage", "Road Damage"), ("other", "Other")], max_length=40)),
                ("label", models.CharField(max_length=120)),
                ("note", models.TextField(blank=True, null=True)),
                ("geom", gis_models.PointField(srid=4326)),
                ("status", models.BooleanField(default=True)),
                ("deleted", models.BooleanField(default=False)),
                ("org_id", models.IntegerField(db_index=True, null=True)),
                ("created_by", models.IntegerField(null=True)),
                ("created_by_name", models.CharField(blank=True, max_length=255, null=True)),
                ("date_created", models.DateTimeField(auto_now_add=True)),
                ("date_modified", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "geo_tag",
                "ordering": ["-date_created"],
                "managed": True,
            },
        ),
    ]
