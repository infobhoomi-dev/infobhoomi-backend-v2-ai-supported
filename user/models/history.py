from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ History_Spartial_Unit_Attrib Model _____________________________________________
class History_Spartialunit_Attrib_Model(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=False)
    # LADM ISO 19152 – soft FK so audit records survive spatial unit deletion
    su_id = models.ForeignKey(
        'LA_Spatial_Unit_Model', on_delete=models.SET_NULL,
        null=True, db_column='su_id', to_field='su_id', db_constraint=False
    )
    category = models.CharField(max_length=255, null=False)
    field_name = models.CharField(max_length=255, null=False)
    field_value = models.CharField(max_length=255, null=False)
    date_created = models.DateTimeField(auto_now_add=True)


    class Meta:
        managed = True
        db_table = 'history_spatialunit_attrib'

#_______________________________________________ LA_Spatial_Source Model ________________________________________________________
class LA_Spatial_Source_Model(models.Model):
    id = models.AutoField(primary_key=True)
    spatial_source_type = models.CharField(max_length=255, null=True)
    source_id = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    approval_status = models.BooleanField(null=False, default=True)
    date_accept = models.DateField(null=True)
    file_path = models.FileField(upload_to='documents/spatial_source', null=False)

    surveyor_name = models.CharField(max_length=255, null=True)

    status = models.BooleanField(null=False, default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'la_spatial_source'
