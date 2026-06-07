from django.contrib.gis.db import models as gismodels
from django.db import models


class GeoTag_Model(gismodels.Model):
    TAG_CHOICES = [
        ("tree", "Tree"),
        ("garbage", "Garbage Collection"),
        ("fire", "Fire Risk"),
        ("drainage", "Drainage Issue"),
        ("street_light", "Street Light"),
        ("road_damage", "Road Damage"),
        ("other", "Other"),
    ]

    id = models.AutoField(primary_key=True)
    tag_type = models.CharField(max_length=40, choices=TAG_CHOICES)
    label = models.CharField(max_length=120)
    note = models.TextField(null=True, blank=True)
    geom = gismodels.PointField(srid=4326)
    status = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)
    org_id = models.IntegerField(null=True, db_index=True)
    created_by = models.IntegerField(null=True)
    created_by_name = models.CharField(max_length=255, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "geo_tag"
        ordering = ["-date_created"]
