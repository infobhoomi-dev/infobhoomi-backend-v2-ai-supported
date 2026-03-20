from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ Party Model ____________________________________________________________________
class Party_Model(models.Model):
    pid = models.AutoField(primary_key=True)
    party_name = models.CharField(max_length=255, null=False)
    party_full_name = models.CharField(max_length=255, null=False)

    la_party_type = models.CharField(max_length=255, null=True)
    sl_party_type = models.CharField(max_length=255, null=True)
    ext_pid_type = models.CharField(max_length=255, null=True)
    ext_pid = models.CharField(max_length=255, null=True)

    # ref_id = ArrayField(models.IntegerField(), null=True)
    # sl_group_party_id = models.IntegerField(null=True)

    pmt_address = models.CharField(max_length=255, null=True)
    tp = ArrayField(models.CharField(max_length=10), null=True)
    specific_tp = models.CharField(max_length=10, null=True)
    email = models.EmailField(max_length=255, null=True, unique=True)
    date_of_birth = models.DateField(null=True)
    gender = models.CharField(max_length=15, null=True)
    other_reg = ArrayField(models.CharField(max_length=50), null=True)
    remark = models.TextField(null=True)

    date_created = models.DateTimeField(auto_now_add=True)

    done_by = models.IntegerField(null=False) # person who add the record

    class Meta:
        managed = True
        constraints = [UniqueConstraint(fields=['ext_pid_type', 'ext_pid'], name='unique_ext_pid_type_pid'),
                       UniqueConstraint(fields=['sl_party_type', 'specific_tp'], name='unique_sl_party_type_specific_tp')]
        db_table = 'sl_party'

#_______________________________________________ History_Party_Attrib Model _____________________________________________________
class History_Party_Attrib_Model(models.Model):
    id = models.AutoField(primary_key=True)
    done_by = models.IntegerField(null=False)
    pid = models.IntegerField(null=False)
    field_name = models.CharField(max_length=255, null=False)
    field_value = models.CharField(max_length=255, null=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'history_party_attrib'

#_______________________________________________ Residence info Model ___________________________________________________________
class Residence_Info_Model(models.Model):
    res_id = models.AutoField(primary_key=True)

    pid = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='pid')

    # LADM FK integrity – was plain IntegerField, now references LA_Spatial_Unit_Model.su_id
    su_id = models.ForeignKey(
        'LA_Spatial_Unit_Model', on_delete=models.CASCADE,
        db_column='su_id', to_field='su_id', null=True
    )
    resident_type = models.CharField(max_length=50, null=False)
    user_added_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(null=True)
    expiry_date = models.DateTimeField(null=True)
    status = models.BooleanField(null=False, default=True)

    class Meta:
        managed = True
        db_table = 'residence_info'
