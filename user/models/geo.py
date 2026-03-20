from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ TESTING ________________________________________________________________________

# Test - jason
class TestJsonModel(gismodels.Model):
    id = models.AutoField(primary_key=True)
    note = models.CharField(max_length=255)
    geom = gismodels.GeometryField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'test_json'

# Test - Array Data
class Test_Data_Model(models.Model):
    id = models.AutoField(primary_key=True)
    users = ArrayField(models.CharField(max_length=255), null=True)

    class Meta:
        managed = True
        db_table = 'test_data'

# Test - Data
class Test_List_Model(models.Model):
    id = models.AutoField(primary_key=True)
    permission_id = models.IntegerField(null=False)
    permission_name = models.CharField(max_length=100, null=False)
    username = models.CharField(max_length=50, null=True)
    remark = models.CharField(max_length=255, null=True)

    party_id = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='my_party_id', to_field='pid')

    class Meta:
        managed = True
        db_table = 'test_list'


class Temp_Import_Model(gismodels.Model):
    gid = models.IntegerField(primary_key=True)
    layer_id = models.IntegerField()
    user_id = models.IntegerField()
    geom = gismodels.GeometryField(null=False)

    class Meta:
        managed = False
        db_table = 'temp_import'




#_______________________________________________ sl_gnd_10m Model _______________________________________________________________
class sl_gnd_10m_Model(gismodels.Model):
    gid = models.IntegerField(primary_key=True)
    gnd = models.CharField(max_length=255, null=False)
    dsd = models.CharField(max_length=255, null=False)
    dist = models.CharField(max_length=255, null=False)
    pd = models.CharField(max_length=255, null=False)
    geom = gismodels.GeometryField(null=False)

    class Meta:
        managed = True
        db_table = 'sl_gnd_10m'
