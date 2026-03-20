from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ Electorate/Local Auth Model ____________________________________________________
class SL_Elect_LocalAuth_Model(models.Model):
    id = models.AutoField(primary_key=True)

    gnd_id = models.IntegerField(null=True)
    eletorate = models.CharField(max_length=50, null=True)
    local_auth = models.CharField(max_length=50, null=True)

    class Meta:
            managed = True
            db_table = 'sl_elect_local_auth'

#_______________________________________________ Assessment Ward Model __________________________________________________________
class Assessment_Ward_Model(models.Model):
    id = models.AutoField(primary_key=True)
    ward_name = models.CharField(max_length=100, null=False)
    org_id = models.IntegerField(null=False)

    class Meta:
            managed = True
            db_table = 'assessment_ward'

#_______________________________________________ SL_Organization Model __________________________________________________________
class SL_Organization_Model(models.Model):
    org_id = models.AutoField(primary_key=True)

    # party_id = models.OneToOneField('Party_Model', on_delete=models.CASCADE, db_column='party_id', to_field='pid')
    # party_id = models.IntegerField(null=True)
    # dimension_2d_3d = models.CharField(max_length=50, null=False, default='2D')

    display_name = models.CharField(max_length=255, null=True)
    permit_start_date = models.DateField(null=True)
    permit_end_date = models.DateField(null=True)
    org_level = models.IntegerField(null=False, default='0')

    director = models.CharField(max_length=100, null=True)
    contact_no = models.CharField(max_length=50, null=True)
    org_email = models.EmailField(max_length=100, null=True, blank=True)
    org_address = models.CharField(max_length=255, null=True)

    subscription_plan = models.CharField(max_length=100, null=True)
    users_limit = models.IntegerField(null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
        managed = True
        db_table = 'sl_organization'

#_______________________________________________ SL_Department Model ____________________________________________________________
class SL_Department_Model(models.Model):
    dep_id = models.AutoField(primary_key=True)
    dep_name = models.CharField(max_length=255, null=False)
    org_id = models.IntegerField(null=False)

    class Meta:
        managed = True
        db_table = 'sl_org_department'

#_______________________________________________ SL_Org_Area_Parent_Bndry Model _________________________________________________
class SL_Org_Area_Parent_Bndry_Model(gismodels.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    org_id = models.OneToOneField('SL_Organization_Model', on_delete=models.CASCADE, db_column='org_id')

    user_id = models.IntegerField(null=False)
    layer_id = models.IntegerField(null=False)
    name = models.CharField(max_length=255, null=False)
    area = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    dimension_2d_3d = models.CharField(max_length=50, null=False, default='2D')
    reference_coordinate = gismodels.GeometryField(null=True)
    geom = gismodels.GeometryField(null=False)

    status = models.BooleanField(null=False, default=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(null=True)

    class Meta:
        managed = True
        db_table = 'sl_org_area_parent_bndry'

#_______________________________________________ SL_Org_Area_Child_Bndry Model __________________________________________________
class SL_Org_Area_Child_Bndry_Model(gismodels.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    user_id = models.IntegerField(null=False)
    layer_id = models.IntegerField(null=False)
    name = models.CharField(max_length=255, null=False)
    area = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    dimension_2d_3d = models.CharField(max_length=50, null=False, default='2D')
    reference_coordinate = gismodels.GeometryField(null=True)

    parent_id = models.ForeignKey('SL_Org_Area_Parent_Bndry_Model', on_delete=models.CASCADE, db_column='parent_id', to_field='id')

    geom = gismodels.GeometryField(null=False)

    status = models.BooleanField(null=False, default=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(null=True)

    class Meta:
        managed = True
        db_table = 'sl_org_area_child_bndry'

#_______________________________________________ Organization Location Model ____________________________________________________
class Org_Location_Model(gismodels.Model):
    id = models.AutoField(primary_key=True)
    dist = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=255, null=True)
    org_id = models.IntegerField(null=False, unique=True)
    geom = gismodels.GeometryField(null=True)

    class Meta:
        managed = True
        db_table = 'org_location'
