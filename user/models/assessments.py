from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ Assessment Model _______________________________________________________________
class Assessment_Model(models.Model):
    id = models.AutoField(primary_key=True)
    external_ass_id = models.CharField(max_length=255, null=True)
    assessment_no = models.CharField(max_length=20, null=True)
    ass_road = models.CharField(max_length=255, null=True)
    assessment_annual_value = models.DecimalField(max_digits=15, decimal_places=2, null=False, default=0.00)
    assessment_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=False, default=0.00)
    date_of_valuation = models.DateField(null=True)
    year_of_assessment = models.CharField(max_length=4, null=True)
    property_type = models.CharField(max_length=255, null=True)
    assessment_name = models.CharField(max_length=255, null=True)
    ass_out_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    land_value      = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    market_value    = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    tax_status      = models.CharField(max_length=10, null=True)  # paid / pending / overdue

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    user_id = models.IntegerField(null=True)

    class Meta:
                managed = True
                db_table = 'assessment'

#_______________________________________________ Tax_Info Model _________________________________________________________________
class Tax_Info_Model(models.Model):
    id = models.AutoField(primary_key=True)

    tax_annual_value = models.DecimalField(max_digits=15, decimal_places=2, null=False, default=0.00)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=False, default=0.00)
    date_valuation = models.DateTimeField(null=True)
    tax_date = models.DateField(null=True)
    tax_type = models.CharField(max_length=255, null=True)
    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    class Meta:
                managed = True
                db_table = 'tax_info'

#_______________________________________________ LA_SP_Fire_Rescue Model ________________________________________________________
class LA_SP_Fire_Rescue_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    description = models.TextField(null=True)

    class Meta:
                managed = True
                db_table = 'la_sp_fire_rescue'
