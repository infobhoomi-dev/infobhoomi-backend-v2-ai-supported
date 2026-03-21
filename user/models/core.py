from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ Organization Area Model ________________________________________________________
class Org_Area_Model(models.Model):
    id = models.AutoField(primary_key=True)
    org_id = models.IntegerField(null=False)
    org_area = ArrayField(models.IntegerField(), null=True)

    class Meta:
        managed = True
        db_table = 'org_area'

#_______________________________________________ History_User_Attrib Model ______________________________________________________
class History_User_Attrib_Model(models.Model):
    id = models.AutoField(primary_key=True)
    done_by = models.IntegerField(null=False)
    user_id = models.IntegerField(null=False)
    field_name = models.CharField(max_length=255, null=False)
    field_value = models.CharField(max_length=255, null=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'history_user_attrib'

#_______________________________________________ Layer Model ____________________________________________________________________
class LayersModel(models.Model):
    layer_id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=False)
    layer_name = models.CharField(max_length=100, null=False)
    colour = models.CharField(max_length=100, null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(null=True)
    group_name = ArrayField(models.CharField(max_length=255), null=True)
    org_id = models.IntegerField(null=True)

    class Meta:
        unique_together = ['user_id', 'layer_name']
        db_table = 'layers'

#_______________________________________________ Survey_Rep data Model __________________________________________________________
class Survey_Rep_DATA_Model(gismodels.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=True, unique=True)
    # LADM ISO 19152 – soft FK (db_constraint=False) to handle orphaned rows safely
    su_id = models.ForeignKey(
        'LA_Spatial_Unit_Model', on_delete=models.SET_NULL,
        null=True, db_column='su_id', to_field='su_id', db_constraint=False
    )

    user_id = models.IntegerField(null=False)
    layer_id = models.IntegerField(null=False, db_index=True)
    geom_type = models.CharField(max_length=255, null=False)
    calculated_area = models.DecimalField(max_digits=20, decimal_places=4, null=True)   # auto-computed from geometry, always in sq.m
    legal_area = models.DecimalField(max_digits=20, decimal_places=4, null=True)         # user-provided value
    legal_area_unit = models.CharField(
        max_length=20, null=True,
        choices=[('sqm', 'sq.m'), ('acres', 'Acres'), ('perches', 'Perches')]
    )
    dimension_2d_3d = models.CharField(max_length=50, null=False, default='2D')
    reference_coordinate = models.CharField(max_length=50, null=True)  # e.g. "EPSG:4326"
    geom = gismodels.GeometryField(null=False)

    status = models.BooleanField(null=False, default=True)
    parent_id = ArrayField(models.IntegerField(), null=True)
    ref_id = models.IntegerField(null=True, db_column='ref_ids')

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(null=True)

    gnd_id = models.IntegerField(null=False, db_index=True, db_column='gndid')
    org_id = models.IntegerField(null=False, db_index=True)

    class Meta:
        managed = True
        db_table = 'survey_rep'

#_______________________________________________ Survey_Rep_Geom_History data Model _____________________________________________
class Survey_Rep_Geom_History_Model(gismodels.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.IntegerField(null=False)

    user_id = models.IntegerField(null=False)
    layer_id = models.IntegerField(null=False)
    calculated_area = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    reference_coordinate = models.CharField(max_length=50, null=True)  # e.g. "EPSG:4326"
    geom = gismodels.GeometryField(null=False)

    status = models.BooleanField(null=False, default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    ref_id = models.IntegerField(null=True)

    # parent_id = ArrayField(models.IntegerField(), null=True)
    # geom_type = models.CharField(max_length=255, null=False)
    # dimension_2d_3d = models.CharField(max_length=50, null=False, default='2D')

    class Meta:
        managed = True
        db_table = 'survey_rep_geom_history'

#_______________________________________________ Survey_Rep_Function_history data Model _________________________________________
class Survey_Rep_History_Model(models.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.IntegerField(null=False)
    tool = models.CharField(max_length=20, null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    user_id = models.IntegerField(null=False)
    user_remark = models.TextField(null=True)

    class Meta:
        managed = True
        db_table = 'survey_rep_func_history'

#_______________________________________________ Permission List Model __________________________________________________________
class Permission_List_Model(models.Model):
    permission_id = models.AutoField(primary_key=True)
    category = models.CharField(max_length=50, null=False)
    sub_category = models.CharField(max_length=50, null=True)
    permission_name = models.CharField(max_length=100, null=False)

    view = models.BooleanField(null=True)
    add = models.BooleanField(null=True)
    edit = models.BooleanField(null=True)
    delete = models.BooleanField(null=True)

    remark = models.CharField(max_length=255, null=True)
    status = models.BooleanField(null=False, default=True)
    type = models.IntegerField(null=False)

    class Meta:
        managed = True
        db_table = 'permission_list'

#_______________________________________________ User Roles Model _______________________________________________________________
class User_Roles_Model(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=50, null=False)
    users = ArrayField(models.IntegerField(), blank=True, null=True)
    remark = models.CharField(max_length=255, null=True)
    admin_id = models.IntegerField(null=False)
    org_id = models.IntegerField(null=False, db_index=True)
    role_type = models.CharField(max_length=20, null=False, default='user')

    class Meta:
        managed = True
        constraints = [UniqueConstraint(fields=['role_name', 'org_id'], name='roles_for_org')]
        db_table = 'user_roles'

#_______________________________________________ Role Permission Model __________________________________________________________
class Role_Permission_Model(models.Model):
    id = models.AutoField(primary_key=True)

    role_id = models.ForeignKey('User_Roles_Model', on_delete=models.CASCADE, db_column='role_id')
    permission_id = models.ForeignKey('Permission_List_Model', on_delete=models.CASCADE, db_column='permission_id')

    view = models.BooleanField(null=True)
    add = models.BooleanField(null=True)
    edit = models.BooleanField(null=True)
    delete = models.BooleanField(null=True)

    class Meta:
        managed = True
        db_table = 'role_permission'
        indexes = [
            # Composite index covers the hot filter(role_id=X, permission_id__in=[...], view/edit=True) pattern
            models.Index(fields=['role_id', 'permission_id'], name='idx_roleperm_role_perm'),
        ]
