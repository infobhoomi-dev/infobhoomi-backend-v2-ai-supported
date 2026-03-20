from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ Last Active Time Model _________________________________________________________
class Last_Active_Model(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=False, db_index=True)
    active_time = models.DateTimeField(null=True)

    class Meta:
        managed = True
        db_table = 'user_last_active'




#_______________________________________________ CityJson data Model ____________________________________________________________
class City_Object_Model(models.Model):
    city_object_id = models.CharField(max_length=255, primary_key=True)
    type = models.CharField(max_length=255)
    attributes = models.JSONField(null=True, blank=True)
    parents = models.JSONField(null=True, blank=True)
    children = models.JSONField(null=True, blank=True)
    geometry = models.JSONField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'city_object'

    def __str__(self):
        return self.city_object_id

#------------------------------------------------------------------------------
class CityJSON_Model(models.Model):
    id = models.AutoField(primary_key=True)
    cityjson_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'city_json'

    def __str__(self):
        return f"CityJSONModel {self.id}"




#_______________________________________________ Import_Vector data Model _______________________________________________________
# class Import_VectorDATA_Model(gismodels.Model):
#     id = models.AutoField(primary_key=True)
#     user_id = models.IntegerField(null=False)
#     dataset_name = models.CharField(max_length=255)
#     layer_id = models.IntegerField(null=False)
#     date_created = models.DateTimeField(auto_now_add=True)
#     geom = gismodels.GeometryField(null=False)

#     class Meta:
#         managed = True
#         constraints = [UniqueConstraint(fields=['user_id', 'dataset_name'], name='import_data_unique')]
#         db_table = 'import_vector_data'

#_______________________________________________ Import_Raster data Model _______________________________________________________
# class Import_RasterData_Model(models.Model):
#     id = models.AutoField(primary_key=True)
#     user_id = models.IntegerField(null=False)
#     datasetName = models.CharField(max_length=255, null=False)
#     layer_id = models.IntegerField(null=True)
#     crs = models.CharField(max_length=255, null=False)
#     file_path = models.FileField(upload_to='documents/raster_data', null=False)
#     capture_date = models.DateField(null=False)
#     remark = models.CharField(max_length=255, null=True)

#     date_created = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         managed = True
#         constraints = [UniqueConstraint(fields=['user_id', 'datasetName'], name='geotif_unique')]
#         db_table = 'import_raster_data'


#_______________________________________________ (RRR) SL Rights & Liabilities Model ____________________________________________
# class SL_Rights_Liabilities_Model(models.Model):
#     id = models.AutoField(primary_key=True)

#     rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', to_field='rrr_id')

#     sl_right_type = models.CharField(max_length=50, null=True)
#     share = models.DecimalField(max_digits=5, decimal_places=2, null=True)

#     party = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='party', to_field='pid')

#     sl_rl_parties = ArrayField(models.IntegerField(), null=True)

#     description = models.TextField(null=True)
#     time_spec = models.CharField(max_length=20, null=True)
#     remark = models.TextField(null=True)
#     status = models.BooleanField(null=False, default=True)

#     date_created = models.DateTimeField(auto_now_add=True)

#     class Meta:
#             managed = True
#             db_table = 'la_rrr_sl_rights_lib'

#_______________________________________________ (RRR) Admin Annotation Model ___________________________________________________
# class Admin_Annotation_Model(models.Model):
#     id = models.AutoField(primary_key=True)

#     rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', to_field='rrr_id')

#     admin_anno_type = models.CharField(max_length=50, null=True)
#     share = models.DecimalField(max_digits=5, decimal_places=2, null=True)
#     area = models.CharField(max_length=50, null=True)

#     claiment_pid = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='claiment_pid', to_field='pid')

#     a_a_parties = ArrayField(models.IntegerField(), null=True)

#     description = models.TextField(null=True)
#     time_spec = models.CharField(max_length=20, null=True)
#     remark = models.TextField(null=True)
#     status = models.BooleanField(null=False, default=True)

#     date_created = models.DateTimeField(auto_now_add=True)


#     class Meta:
#             managed = True
#             db_table = 'la_rrr_admin_annotation'

#_______________________________________________ (RRR) SL Admin Restrict Model __________________________________________________
# class SL_Admin_Restrict_Model(models.Model):
#     id = models.AutoField(primary_key=True)

#     rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', to_field='rrr_id')

#     sl_adm_res_type = models.CharField(max_length=50, null=True)
#     share = models.DecimalField(max_digits=5, decimal_places=2, null=True)
#     adm_res_legal_space = models.CharField(max_length=50, null=True)
#     adm_res_legal_prov = models.CharField(max_length=50, null=True)

#     gov_party = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='gov_party', to_field='pid')

#     description = models.TextField(null=True)
#     time_spec = models.CharField(max_length=20, null=True)
#     remark = models.TextField(null=True)
#     status = models.BooleanField(null=False, default=True)

#     date_created = models.DateTimeField(auto_now_add=True)


#     class Meta:
#             managed = True
#             db_table = 'la_rrr_sl_admin_restrict'

#_______________________________________________ (RRR) LA Mortgage Model ________________________________________________________
# class LA_Mortgage_Model(models.Model):
#     id = models.AutoField(primary_key=True)

#     rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', to_field='rrr_id')

#     share = models.DecimalField(max_digits=5, decimal_places=2, null=True)
#     share_type = models.CharField(max_length=100, null=True)
#     amount = models.DecimalField(max_digits=15, decimal_places=2, null=True)
#     int_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)
#     ranking = models.IntegerField(null=True)
#     sl_mortgage_type = models.CharField(max_length=50, null=True)
#     mort_id = models.CharField(max_length=50, null=False)

#     mortgagor = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='mortgagor', to_field='pid')

#     mortgagee = models.CharField(max_length=50, null=False)

#     time_spec = models.CharField(max_length=20, null=True)
#     date_start = models.DateField(null=True)
#     date_end = models.DateField(null=True)
#     remark = models.TextField(null=True)
#     status = models.BooleanField(null=False, default=True)

#     date_created = models.DateTimeField(auto_now_add=True)


#     class Meta:
#             managed = True
#             db_table = 'la_rrr_la_Mortgage'

#_______________________________________________ (RRR) SL Rights Model __________________________________________________________
# class SL_Rights_Model(models.Model):
#     id = models.AutoField(primary_key=True)

#     # rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', to_field='rrr_id')
#     rrr_id = models.IntegerField(null=True)


#     share = models.DecimalField(max_digits=5, decimal_places=2, null=True)
#     share_type = models.CharField(max_length=100, null=True)
#     right_type = models.CharField(max_length=50, null=True)

#     # party = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='party', to_field='pid')
#     party = models.IntegerField(null=True)


#     description = models.TextField(null=True)
#     time_spec = models.CharField(max_length=20, null=True)
#     date_start = models.DateField(null=True)
#     date_end = models.DateField(null=True)
#     remark = models.TextField(null=True)
#     status = models.BooleanField(null=False, default=True)

#     date_created = models.DateTimeField(auto_now_add=True)

#     class Meta:
#             managed = True
#             db_table = 'la_rrr_sl_rights'

#_______________________________________________ (RRR) LA Responsibility Model __________________________________________________
# class LA_Responsibility_Model(models.Model):
#     id = models.AutoField(primary_key=True)

#     rrr_id = models.ForeignKey('LA_RRR_Model', on_delete=models.CASCADE, db_column='rrr_id', to_field='rrr_id')

#     share = models.DecimalField(max_digits=5, decimal_places=2, null=True)
#     responsibility_type = models.CharField(max_length=50, null=False)

#     party = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='party', to_field='pid')

#     description = models.TextField(null=True)
#     time_spec = models.CharField(max_length=20, null=True)
#     remark = models.TextField(null=True)
#     status = models.BooleanField(null=False, default=True)

#     date_created = models.DateTimeField(auto_now_add=True)

#     class Meta:
#             managed = True
#             db_table = 'la_rrr_la_responsibility'


# __ Dynamic Attribute (Land Tab custom fields per section) __
class Dynamic_Attribute_Model(models.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.IntegerField()
    section_key = models.CharField(max_length=30)   # ADMIN_INFO | LAND_OVERVIEW | UTILITY_INFO | TAX_ASSESSMENT | TAX_INFO
    label = models.CharField(max_length=255)
    value = models.TextField(null=True, blank=True)
    created_by = models.IntegerField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'dynamic_attribute'
