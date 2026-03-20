from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ SL BA Unit Model _______________________________________________________________
class SL_BA_Unit_Model(models.Model):
    ba_unit_id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    sl_ba_unit_type = models.CharField(max_length=30, null=False)
    sl_ba_unit_name = models.TextField(null=False)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'sl_ba_unit'

#_______________________________________________ LA Admin Source Model __________________________________________________________
class LA_Admin_Source_Model(models.Model):
    admin_source_id = models.AutoField(primary_key=True)
    admin_source_type = models.CharField(max_length=255, null=False)

    done_by = models.IntegerField(null=True)
    user_id = models.IntegerField(null=False)
    file_path = models.FileField(upload_to='documents/admin_source', null=True)

    status = models.BooleanField(null=False, default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'la_admin_source'

#_______________________________________________ LA RRR Model ___________________________________________________________________
class LA_RRR_Model(models.Model):
    rrr_id = models.AutoField(primary_key=True)

    ba_unit_id = models.ForeignKey('SL_BA_Unit_Model', on_delete=models.CASCADE, db_column='ba_unit_id', null=True)
    admin_source_id = models.ForeignKey('LA_Admin_Source_Model', on_delete=models.CASCADE, db_column='admin_source_id', null=True)

    pid = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='pid', null=True)

    # LADM ISO 19152 – LA_RRR required attributes
    rrr_type    = models.CharField(max_length=50, null=True)   # RIGHT / RESTRICTION / RESPONSIBILITY
    time_begin  = models.DateField(null=True)                   # validFrom
    time_end    = models.DateField(null=True)                   # validTo
    description = models.TextField(null=True)

    class Meta:
            managed = True
            db_table = 'la_rrr'

#_______________________________________________ LA RRR Document Model (additional docs per BA unit) ___________________________________
class LA_RRR_Document_Model(models.Model):
    """Links additional admin-source documents to a BA unit (beyond the primary admin_source_id on LA_RRR_Model)."""
    id = models.AutoField(primary_key=True)
    ba_unit = models.ForeignKey('SL_BA_Unit_Model', on_delete=models.CASCADE, db_column='ba_unit_id')
    admin_source = models.ForeignKey('LA_Admin_Source_Model', on_delete=models.CASCADE, db_column='admin_source_id')

    class Meta:
        managed = True
        db_table = 'la_rrr_document'

#_______________________________________________ LA RRR Restriction Model _______________________________________________________________
class LA_RRR_Restriction_Model(models.Model):
    id = models.AutoField(primary_key=True)
    rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', related_name='restrictions')
    rrr_restriction_type = models.CharField(max_length=20, null=False)  # RES_EAS/RES_COV/RES_HGT/RES_HER/RES_ENV
    description = models.TextField(null=True)
    time_begin  = models.DateField(null=True)
    time_end    = models.DateField(null=True)

    class Meta:
        managed = True
        db_table = 'la_rrr_restriction'

#_______________________________________________ LA RRR Responsibility Model ____________________________________________________________
class LA_RRR_Responsibility_Model(models.Model):
    id = models.AutoField(primary_key=True)
    rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', related_name='responsibilities')
    rrr_responsibility_type = models.CharField(max_length=20, null=False)  # RSP_MAINT/RSP_TAX/RSP_INS
    description = models.TextField(null=True)
    time_begin  = models.DateField(null=True)
    time_end    = models.DateField(null=True)

    class Meta:
        managed = True
        db_table = 'la_rrr_responsibility'

#_______________________________________________ Party Roles Model ____________________________________________________________________
class Party_Roles_Model(models.Model):
    id = models.AutoField(primary_key=True)

    pid = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='pid', null=True)
    rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', null=True)

    party_role_type = models.CharField(max_length=255, null=False)
    # LADM: share belongs to the party's participation in the RRR, not to the RRR itself
    share_type = models.CharField(max_length=100, null=True, blank=True)
    share = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    done_by = models.IntegerField(null=False) # person who add the record

    class Meta:
        managed = True
        db_table = 'sl_party_roles'
