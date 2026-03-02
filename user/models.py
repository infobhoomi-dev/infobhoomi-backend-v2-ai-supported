from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


class CustomUserManager(BaseUserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("The username must be provided")
        if not email:
            raise ValueError("The email must be provided")
        if not password:
            raise ValueError("The password must be provided")
        
        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        # if extra_fields.get('is_staff') is not True:
        #     raise ValueError('Superuser must have is_staff=True.')
        # if extra_fields.get('is_superuser') is not True:
        #     raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

class User(AbstractUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('user', 'User'),
    )

    username = models.CharField(db_index=True, unique=True, max_length=255, null=False)
    email = models.EmailField(db_index=True, unique=True, max_length=255, null=False)

    first_name = models.CharField(max_length=240, null=False)
    last_name = models.CharField(max_length=240, null=True)
    mobile = models.CharField(max_length=15, null=False)
    address = models.CharField(max_length=255, null=False)

    nic = models.CharField(max_length=20, null=False)
    birthday = models.DateField(null=False)
    sex = models.CharField(max_length=10, null=False)

    org_id = models.IntegerField(null=False)
    dep_id = models.IntegerField(null=False)
    emp_id = models.CharField(max_length=20, null=True)
    post = models.CharField(max_length=100, null=False)

    is_staff = models.BooleanField()
    is_superuser = models.BooleanField()

    user_type = models.CharField(max_length=50, choices=USER_TYPE_CHOICES, default='user', null=False)
    is_active = models.BooleanField(default=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"



# ====================================================================================================================================

#_______________________________________________ Lst_SL_Party_Type_1 Model ______________________________________________________
class Lst_SL_Party_Type_1_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)
    code = models.CharField(max_length=20, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_party_type_1'
#_______________________________________________ Lst_SL_PartyRoleType_2 Model ___________________________________________________
class Lst_SL_PartyRoleType_2_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_partyroletype_2'
#_______________________________________________ Lst_SL_Education_Level_3 Model _________________________________________________
class Lst_SL_Education_Level_3_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_education_level_3'
#_______________________________________________ Lst_SL_Race_4 Model ____________________________________________________________
class Lst_SL_Race_4_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_race_4'
#_______________________________________________ Lst_SL_HealthStatus_5 Model ____________________________________________________
class Lst_SL_HealthStatus_5_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_health_status_5'
#_______________________________________________ Lst_SL_MarriedStatus_6 Model ___________________________________________________
class Lst_SL_MarriedStatus_6_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_married_status_6'
#_______________________________________________ Lst_SL_Religions_7 Model _______________________________________________________
class Lst_SL_Religions_7_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_religions_7'
#_______________________________________________ Lst_SL_GenderType_8 Model ______________________________________________________
class Lst_SL_GenderType_8_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_gendertype_8'
#_______________________________________________ Lst_SL_RightType_9 Model _______________________________________________________
class Lst_SL_RightType_9_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_righttype_9'
#_______________________________________________ Lst_SL_BAUnitType_10 Model _____________________________________________________
class Lst_SL_BAUnitType_10_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_baunittype_10'
#_______________________________________________ Lst_SL_AdminRestrictionType_11 Model ___________________________________________
class Lst_SL_AdminRestrictionType_11_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_adminrestrictiontype_11'
#_______________________________________________ Lst_SL_AnnotationType_12 Model _________________________________________________
class Lst_SL_AnnotationType_12_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_annotationtype_12'
#_______________________________________________ Lst_Sl_MortgageType_13 Model ___________________________________________________
class Lst_Sl_MortgageType_13_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_mortgagetype_13'
#_______________________________________________ Lst_SL_RightShareType_14 Model _________________________________________________
class Lst_SL_RightShareType_14_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_rightsharetype_14'
#_______________________________________________ Lst_SL_AdministrativeStatausType_15 Model ______________________________________
class Lst_SL_AdministrativeStatausType_15_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_administrativestataustype_15'
#_______________________________________________ Lst_SL_AdministrativeSourceType_16 Model _______________________________________
class Lst_SL_AdministrativeSourceType_16_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_administrativesourcetype_16'
#_______________________________________________ Lst_SL_ResponsibilityType_17 Model _____________________________________________
class Lst_SL_ResponsibilityType_17_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_responsibilitytype_17'
#_______________________________________________ Lst_LA_BAUnitType_18 Model _____________________________________________________
class Lst_LA_BAUnitType_18_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_la_baunittype_18'
#_______________________________________________ Lst_SU_SL_LevelContentType_19 Model ____________________________________________
class Lst_SU_SL_LevelContentType_19_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_su_sl_levelcontenttype_19'
#_______________________________________________ Lst_SU_SL_RegesterType_20 Model ________________________________________________
class Lst_SU_SL_RegesterType_20_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_su_sl_regestertype_20'
#_______________________________________________ Lst_SU_SL_StructureType_21 Model _______________________________________________
class Lst_SU_SL_StructureType_21_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_su_sl_structuretype_21'
#_______________________________________________ LA Level Model (LADM ISO 19152 – LA_Level) _____________________________________
class LA_Level_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    # FK references to the existing lookup tables
    content_type = models.ForeignKey(
        'Lst_SU_SL_LevelContentType_19_Model',
        on_delete=models.SET_NULL, null=True, db_column='content_type_id'
    )
    register_type = models.ForeignKey(
        'Lst_SU_SL_RegesterType_20_Model',
        on_delete=models.SET_NULL, null=True, db_column='register_type_id'
    )
    structure_type = models.ForeignKey(
        'Lst_SU_SL_StructureType_21_Model',
        on_delete=models.SET_NULL, null=True, db_column='structure_type_id'
    )

    class Meta:
        managed = True
        db_table = 'la_level'

#_______________________________________________ Lst_SU_SL_Water_22 Model _______________________________________________________
class Lst_SU_SL_Water_22_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_su_sl_water_22'
#_______________________________________________ Lst_SU_SL_Sanitation_23 Model __________________________________________________
class Lst_SU_SL_Sanitation_23_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_su_sl_sanitation_23'
#_______________________________________________ Lst_SU_SL_Roof_Type_24 Model ___________________________________________________
class Lst_SU_SL_Roof_Type_24_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_su_sl_roof_type_24'
#_______________________________________________ Lst_SU_SL_Wall_Type_25 Model ___________________________________________________
class Lst_SU_SL_Wall_Type_25_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_su_sl_wall_type_25'
#_______________________________________________ Lst_SU_SL_Floor_Type_26 Model __________________________________________________
class Lst_SU_SL_Floor_Type_26_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_su_sl_floor_type_26'
#_______________________________________________ Lst_SR_SL_SpatialSourceTypes_27 Model __________________________________________
class Lst_SR_SL_SpatialSourceTypes_27_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sr_sl_spatialsourcetypes_27'
#_______________________________________________ Lst_EC_ExtLandUseType_28 Model _________________________________________________
class Lst_EC_ExtLandUseType_28_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extlandusetype_28'
#_______________________________________________ Lst_EC_ExtLandUseSubType_29 Model ______________________________________________
class Lst_EC_ExtLandUseSubType_29_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extlandusesubtype_29'
#_______________________________________________ Lst_EC_ExtOuterLegalSpaceUseType_30 Model ______________________________________
class Lst_EC_ExtOuterLegalSpaceUseType_30_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extouterlegalspaceusetype_30'
#_______________________________________________ Lst_EC_ExtOuterLegalSpaceUseSubType_31 Model ___________________________________
class Lst_EC_ExtOuterLegalSpaceUseSubType_31_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extouterlegalspaceusesubtype_31'
#_______________________________________________ Lst_EC_ExtBuildUseType_32 Model ________________________________________________
class Lst_EC_ExtBuildUseType_32_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extbuildusetype_32'
#_______________________________________________ Lst_EC_ExtBuildUseSubType_33 Model _____________________________________________
class Lst_EC_ExtBuildUseSubType_33_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extbuildusesubtype_33'
#_______________________________________________ Lst_EC_ExtDivisionType_34 Model ________________________________________________
class Lst_EC_ExtDivisionType_34_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extdivisiontype_34'
#_______________________________________________ Lst_EC_ExtFeatureMainType_35 Model _____________________________________________
class Lst_EC_ExtFeatureMainType_35_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extfeaturemaintype_35'
#_______________________________________________ Lst_EC_ExtFeatureMainType_36 Model _____________________________________________
class Lst_EC_ExtFeatureMainType_36_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extfeatureytype_36'
#_______________________________________________ Lst_EC_ExtFeatureMainType_37 Model _____________________________________________
class Lst_EC_ExtFeatureMainType_37_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_ec_extfeaturebuildtype_37'
#_______________________________________________ Lst_Telecom_Providers_38 Model _________________________________________________
class Lst_Tele_Providers_38_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_telecom_providers_38'
#_______________________________________________ Lst_Internet_Providers_39 Model ________________________________________________
class Lst_Int_Providers_39_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_int_providers_39'
#_______________________________________________ Lst_Organization_Names_40 Model ________________________________________________
class Lst_Org_Names_40_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)
    code = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_org_names_40'
#_______________________________________________ Lst_SL_Group_Party_Type_41 Model _______________________________________________
class Lst_SL_Group_Party_Type_41_Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    class Meta:
        managed = True
        db_table = 'lst_sl_group_party_type_41'

# ====================================================================================================================================





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
        managed = False
        db_table = 'sl_gnd_10m'

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
    layer_id = models.IntegerField(null=False)
    infobhoomi_id = models.CharField(max_length=255, null=True)
    geom_type = models.CharField(max_length=255, null=False)
    area = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    dimension_2d_3d = models.CharField(max_length=50, null=False, default='2D')
    reference_coordinate = gismodels.GeometryField(null=True)
    geom = gismodels.GeometryField(null=False)

    status = models.BooleanField(null=False, default=True)
    parent_id = ArrayField(models.IntegerField(), null=True)
    ref_id = models.IntegerField(null=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(null=True)

    original_point_id = models.CharField(max_length=10, null=True)
    original_x_coord = models.DecimalField(max_digits=20, decimal_places=10, null = True)
    original_y_coord = models.DecimalField(max_digits=20, decimal_places=10, null = True)
    original_z_coord = models.DecimalField(max_digits=20, decimal_places=10, null = True)
    original_code = models.CharField(max_length=10, null=True)

    gnd_id = models.IntegerField(null=True)
    org_id = models.IntegerField(null=False)

    class Meta:
        managed = True
        db_table = 'survey_rep' 

#_______________________________________________ Survey_Rep_Geom_History data Model _____________________________________________
class Survey_Rep_Geom_History_Model(gismodels.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.IntegerField(null=False)
   
    user_id = models.IntegerField(null=False)
    layer_id = models.IntegerField(null=False)
    area = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    reference_coordinate = gismodels.GeometryField(null=True)
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
    org_id = models.IntegerField(null=False)
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
    edu = models.CharField(max_length=20, null=True)
    religion = models.CharField(max_length=15, null=True)
    race = models.CharField(max_length=15, null=True)
    married_status = models.CharField(max_length=15, null=True)
    health_status = models.CharField(max_length=50, null=True)
    other_reg = ArrayField(models.CharField(max_length=50), null=True)
    remark = models.TextField(null=True)

    date_created = models.DateTimeField(auto_now_add=True)

    done_by = models.IntegerField(null=False) # person who add the record

    class Meta:
        managed = True
        constraints = [UniqueConstraint(fields=['ext_pid_type', 'ext_pid'], name='unique_ext_pid_type_pid'),
                       UniqueConstraint(fields=['sl_party_type', 'specific_tp'], name='unique_sl_party_type_specific_tp')]
        db_table = 'sl_party'

#_______________________________________________ Group Party Model ____________________________________________________________________
class SL_Group_Party_Members_Model(models.Model):
    id = models.AutoField(primary_key=True)
    pid = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='pid', to_field='pid') # Group party id
    # group_name = models.CharField(max_length=255, null=True)
    
    sl_group_party_type = models.IntegerField(null=False)

    party_members = ArrayField(models.IntegerField(), null=False)

    date_created = models.DateTimeField(auto_now_add=True)
    done_by = models.IntegerField(null=False) # person who add the record

    class Meta:
        managed = True
        db_table = 'sl_group_party_members'

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

#_______________________________________________ SL BA Unit Model _______________________________________________________________
class SL_BA_Unit_Model(models.Model):
    ba_unit_id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    sl_ba_unit_type = models.CharField(max_length=30, null=False)
    sl_ba_unit_name = models.TextField(null=False)

    status = models.BooleanField(null=False, default=True)
    remark = models.CharField(max_length=255, null=True)

    org_id = models.IntegerField(null=False, default=1)
    role_type = models.CharField(max_length=50, null=False, default='user')

    class Meta:
            managed = True
            db_table = 'sl_ba_unit'

#_______________________________________________ LA Admin Source Model __________________________________________________________
class LA_Admin_Source_Model(models.Model):
    admin_source_id = models.AutoField(primary_key=True)
    admin_source_type = models.CharField(max_length=255, null=False)

    done_by = models.IntegerField(null=False)
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

#_______________________________________________ LA Spatial Unit Model __________________________________________________________
class LA_Spatial_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.IntegerField(null=False, unique=True)

    status = models.BooleanField(null=False, default=True)
    reference_id = models.IntegerField(null=True)
    ladm_value = models.CharField(max_length=30, null=True)
    label = models.CharField(max_length=255, null=True)
    util_obj_id = models.IntegerField(null=True)
    util_obj_code = models.CharField(max_length=20, null=True)

    # LADM ISO 19152 – LA_SpatialUnit.level
    level = models.ForeignKey(
        'LA_Level_Model', on_delete=models.SET_NULL, null=True, db_column='level_id'
    )

    # LADM ISO 19152 – parcel registration status (ACTIVE/PENDING/SUSPENDED/HISTORIC)
    parcel_status = models.CharField(max_length=20, null=True)

    class Meta:
            managed = True
            constraints = [UniqueConstraint(fields=['util_obj_id', 'util_obj_code'], name='util_obj_id_util_obj_code')]
            db_table = 'la_spatial_unit'

#_______________________________________________ LA_LS_Land_Unit Model __________________________________________________________
class LA_LS_Land_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)
    postal_ad_lnd = models.CharField(max_length=255, null=True)
    local_auth = models.CharField(max_length=255, null=True, blank=True)
    ext_landuse_type = models.CharField(max_length=100, null=True)
    ext_landuse_sub_type = models.CharField(max_length=100, null=True)
    sl_land_type = models.CharField(max_length=30, null=True)
    land_name = models.CharField(max_length=255, null=True)
    registration_date = models.DateField(null=True)

    # LADM ISO 19152 – LA_SpatialUnit spatial geometry attributes
    area = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    perimeter = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    dimension_2d_3d = models.CharField(max_length=3, null=True)
    boundary_type = models.CharField(max_length=20, null=True)
    crs = models.CharField(max_length=50, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_land_unit'

#_______________________________________________ LA_LS_Zoning Model _____________________________________________________________
class LA_LS_Zoning_Model(models.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.OneToOneField(
        'LA_Spatial_Unit_Model', on_delete=models.CASCADE,
        db_column='su_id', to_field='su_id'
    )
    zoning_category     = models.CharField(max_length=10, null=True)
    max_building_height = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    max_coverage        = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    max_far             = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    setback_front       = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    setback_rear        = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    setback_side        = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    special_overlay     = models.CharField(max_length=255, null=True)

    class Meta:
        managed = True
        db_table = 'la_ls_zoning'

#_______________________________________________ LA_LS_Physical_Env Model _______________________________________________________
class LA_LS_Physical_Env_Model(models.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.OneToOneField(
        'LA_Spatial_Unit_Model', on_delete=models.CASCADE,
        db_column='su_id', to_field='su_id'
    )
    elevation        = models.DecimalField(max_digits=10, decimal_places=3, null=True)  # metres
    slope            = models.DecimalField(max_digits=5, decimal_places=2, null=True)   # degrees
    soil_type        = models.CharField(max_length=20, null=True)  # CLAY/SAND/LOAM/SILT/ROCK/PEAT/FILL
    flood_zone       = models.BooleanField(null=True)
    vegetation_cover = models.CharField(max_length=255, null=True)

    class Meta:
        managed = True
        db_table = 'la_ls_physical_env'

#_______________________________________________ LA_BAUnit_SpatialUnit (M:M) Model ______________________________________________
class LA_BAUnit_SpatialUnit_Model(models.Model):
    """LADM ISO 19152 – explicit M:M relationship between BA units and spatial units.
    One BA unit can reference multiple spatial units (e.g. a right spanning several parcels)
    and one spatial unit can belong to multiple BA units."""
    id = models.AutoField(primary_key=True)
    ba_unit = models.ForeignKey(
        'SL_BA_Unit_Model', on_delete=models.CASCADE, db_column='ba_unit_id'
    )
    su = models.ForeignKey(
        'LA_Spatial_Unit_Model', on_delete=models.CASCADE,
        db_column='su_id', to_field='su_id'
    )
    # PRIMARY = main parcel, SECONDARY = appurtenant, PART_OF = strata / sub-unit
    relation_type = models.CharField(max_length=20, null=True, default='PRIMARY')

    class Meta:
        managed = True
        db_table = 'la_ba_unit_spatial_unit'
        unique_together = [('ba_unit', 'su')]

#_______________________________________________ LA_LS_Utinet_LU Model __________________________________________________________
class LA_LS_Utinet_LU_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    water = models.CharField(max_length=50, null=True)
    elec = models.CharField(max_length=50, null=True)
    drainage = models.CharField(max_length=50, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    sani_gully = models.CharField(max_length=50, null=True)
    garbage_dispose = models.CharField(max_length=50, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_lu'

#_______________________________________________ LA_LS_Build_Unit Model _________________________________________________________
class LA_LS_Build_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)
    postal_ad_build = models.CharField(max_length=255, null=True)
    house_hold_no = models.CharField(max_length=25, null=True)
    no_floors = models.IntegerField(null=True)

    ext_builduse_type = models.CharField(max_length=100, null=True)
    ext_builduse_sub_type = models.CharField(max_length=100, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    roof_type = models.CharField(max_length=20, null=True)
    wall_type = models.CharField(max_length=20, null=True)
    building_name = models.CharField(max_length=255, null=True)
    bld_property_type = models.CharField(max_length=255, null=True)

    registration_date  = models.DateField(null=True)
    construction_year  = models.IntegerField(null=True)
    structure_type     = models.CharField(max_length=30, null=True)  # CONC_REINF/STEEL_FRM/MASONRY/TIMBER/COMPOSITE
    condition          = models.CharField(max_length=20, null=True)  # EXCELLENT/GOOD/FAIR/POOR/DILAPID

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_build_unit'

#_______________________________________________ LA_LS_Utinet_BU Model __________________________________________________________
class LA_LS_Utinet_BU_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    water = models.CharField(max_length=15, null=True)
    water_drink = models.CharField(max_length=15, null=True)
    elec = models.CharField(max_length=15, null=True)
    tele = models.CharField(max_length=15, null=True)
    internet = models.CharField(max_length=15, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    sani_gully = models.CharField(max_length=50, null=True)
    garbage_dispose = models.CharField(max_length=15, null=True)
    drainage = models.CharField(max_length=100, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_bu'

#_______________________________________________ LA_LS_Apt_Unit Model ___________________________________________________________
class LA_LS_Apt_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    ref_id = models.OneToOneField('LA_LS_Ils_Unit_Model', on_delete=models.CASCADE, db_column='ref_id', to_field='id')

    postal_ad_apt = models.CharField(max_length=255, null=True)
    floor_no = models.IntegerField(null=True)
    house_hold_no = models.CharField(max_length=25, null=True)
    specific_id = models.CharField(max_length=25, null=True)
    ext_div_type = models.CharField(max_length=100, null=True)
    floor_area = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    ext_aptuse_type = models.CharField(max_length=100, null=True)
    ext_aptuse_sub_type = models.CharField(max_length=100, null=True)
    surface_relation = models.CharField(max_length=20, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    roof_type = models.CharField(max_length=20, null=True)
    wall_type = models.CharField(max_length=20, null=True)
    floor_type = models.CharField(max_length=20, null=True)
    apt_name = models.CharField(max_length=255, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_apt_unit'

#_______________________________________________ LA_LS_Utinet_AU Model __________________________________________________________
class LA_LS_Utinet_AU_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    ref_id = models.OneToOneField('LA_LS_Ils_Unit_Model', on_delete=models.CASCADE, db_column='ref_id', to_field='id')

    water = models.CharField(max_length=15, null=True)
    water_drink = models.CharField(max_length=15, null=True)
    elec = models.CharField(max_length=15, null=True)
    tele = models.CharField(max_length=15, null=True)
    internet = models.CharField(max_length=15, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    garbage_dispose = models.CharField(max_length=15, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_au'

#_______________________________________________ LA_LS_Ols_Polygon_Unit Model ___________________________________________________
class LA_LS_Ols_Polygon_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)
    postal_ad_ols = models.CharField(max_length=255, null=True)

    ols_main_type = models.CharField(max_length=100, null=True)
    ext_olsuse_type = models.CharField(max_length=100, null=True)
    ext_olsuse_sub_type = models.CharField(max_length=100, null=True)
    ols_x_type = models.CharField(max_length=100, null=True)
    ols_build_type = models.CharField(max_length=100, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    grade = models.CharField(max_length=10, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    status = models.BooleanField(null=False, default=True)
    ols_poly_name = models.CharField(max_length=255, null=True)

    class Meta:
            managed = True
            db_table = 'la_ls_ols_unit'

#_______________________________________________ LA_LS_Ols_PointLine_Unit Model _________________________________________________
class LA_LS_Ols_PointLine_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)

    ols_made_type = models.CharField(max_length=100, null=True)
    ols_main_type = models.CharField(max_length=100, null=True)
    ols_x_type = models.CharField(max_length=100, null=True)
    ols_build_type = models.CharField(max_length=100, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    grade = models.CharField(max_length=10, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    status = models.BooleanField(null=False, default=True)
    ols_point_line_name = models.CharField(max_length=255, null=True)

    class Meta:
            managed = True
            db_table = 'la_ls_ols_pointline_unit'

#_______________________________________________ LA_LS_MyLayer_Polygon_Unit Model _______________________________________________
class LA_LS_MyLayer_Polygon_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)
    postal_ad_ols = models.CharField(max_length=255, null=True)

    ols_main_type = models.CharField(max_length=100, null=True)
    ext_olsuse_type = models.CharField(max_length=100, null=True)
    ext_olsuse_sub_type = models.CharField(max_length=100, null=True)
    ols_x_type = models.CharField(max_length=100, null=True)
    ols_build_type = models.CharField(max_length=100, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    grade = models.CharField(max_length=10, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_mylayer_unit'

#_______________________________________________ LA_LS_MyLayer_PointLine_Unit Model _____________________________________________
class LA_LS_MyLayer_PointLine_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)

    ols_made_type = models.CharField(max_length=100, null=True)
    ols_main_type = models.CharField(max_length=100, null=True)
    ols_x_type = models.CharField(max_length=100, null=True)
    ols_build_type = models.CharField(max_length=100, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    grade = models.CharField(max_length=10, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_mylayer_pointline_unit'

#_______________________________________________ LA_LS_Utinet_Ols Model _________________________________________________________
class LA_LS_Utinet_Ols_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    water = models.CharField(max_length=15, null=True)
    water_drink = models.CharField(max_length=15, null=True)
    elec = models.CharField(max_length=15, null=True)
    tele = models.CharField(max_length=15, null=True)
    internet = models.CharField(max_length=15, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    sani_gully = models.CharField(max_length=15, null=True)
    drainage = models.CharField(max_length=15, null=True)
    garbage_dispose = models.CharField(max_length=15, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_ols'

#_______________________________________________ LA_LS_Ils_Unit Model ___________________________________________________________
class LA_LS_Ils_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    ref_id = models.OneToOneField('LA_LS_Build_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    postal_ad_ils = models.CharField(max_length=255, null=True)
    floor_no = models.IntegerField(null=True)
    house_hold_no = models.CharField(max_length=25, null=True)
    floor_area = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    ext_ilsuse_type = models.CharField(max_length=100, null=True)
    ext_ilsuse_sub_type = models.CharField(max_length=100, null=True)
    surface_relation = models.CharField(max_length=20, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    roof_type = models.CharField(max_length=20, null=True)
    wall_type = models.CharField(max_length=20, null=True)
    floor_type = models.CharField(max_length=20, null=True)
    ils_name = models.CharField(max_length=255, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_ils_unit'

#_______________________________________________ LA_LS_Utinet_Ils Model _________________________________________________________
class LA_LS_Utinet_Ils_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    ref_id = models.OneToOneField('LA_LS_Build_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    water = models.CharField(max_length=15, null=True)
    water_drink = models.CharField(max_length=15, null=True)
    elec = models.CharField(max_length=15, null=True)
    tele = models.CharField(max_length=15, null=True)
    internet = models.CharField(max_length=15, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    garbage_dispose = models.CharField(max_length=15, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_ils'

#_______________________________________________ LA_Spatial_Unit_Sketch_Ref Model _______________________________________________
class LA_Spatial_Unit_Sketch_Ref_Model(models.Model):
    sketch_ref_id = models.AutoField(primary_key=True)
    sketch_ref_type = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    approval_status = models.BooleanField(null=False, default=True)
    avl_status = models.BooleanField(null=False, default=True)

    file_path = models.FileField(upload_to='documents/sketch_ref', null=True)

    doc_owner = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='doc_owner', to_field='pid', null=True)

    status = models.BooleanField(null=False, default=True)
    remark = models.CharField(max_length=255, null=True)

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'la_spatial_unit_sketch_ref'

#_______________________________________________ SL_Organization Model __________________________________________________________
class SL_Organization_Model(models.Model):
    org_id = models.AutoField(primary_key=True)

    # party_id = models.OneToOneField('Party_Model', on_delete=models.CASCADE, db_column='party_id', to_field='pid')
    # party_id = models.IntegerField(null=True)
    # dimension_2d_3d = models.CharField(max_length=50, null=False, default='2D')

    display_name = models.CharField(max_length=255, null=True)
    permit_start_date = models.DateField(null=True)
    permit_end_date = models.DateField(null=True)
    org_parent_type = models.CharField(max_length=100, null=True)
    org_group_type = models.CharField(max_length=100, null=True)
    
    org_level = models.IntegerField(null=False, default='0')
    org_overview = models.TextField(null=True)

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
    date_expire = models.DateField(null=True)

    file_path = models.FileField(upload_to='documents/spatial_source', null=False)

    surveyor_name = models.CharField(max_length=255, null=True)
    surveyor_tp = models.CharField(max_length=15, null=True)

    status = models.BooleanField(null=False, default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'la_spatial_source'

#_______________________________________________ Assessment Model _______________________________________________________________
class Assessment_Model(models.Model):
    id = models.AutoField(primary_key=True)
    external_ass_id = models.CharField(max_length=255, null=True)
    assessment_no = models.CharField(max_length=10, null=True)
    ass_road = models.CharField(max_length=255, null=True)
    ass_div = models.IntegerField(null=True)
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

    class Meta:
                managed = True
                db_table = 'assessment'

#_______________________________________________ Tax_Info Model _________________________________________________________________
class Tax_Info_Model(models.Model):
    id = models.AutoField(primary_key=True)
    external_tax_id = models.CharField(max_length=255, null=True)
    tax_no = models.CharField(max_length=50, null=True)
    tax_annual_value = models.DecimalField(max_digits=15, decimal_places=2, null=False, default=0.00)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=False, default=0.00)
    date_valuation = models.DateTimeField(null=True)
    tax_date = models.DateField(null=True)
    tax_type = models.CharField(max_length=255, null=True)
    tax_name = models.CharField(max_length=255, null=True)
    tax_out_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    
    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    class Meta:
                managed = True
                db_table = 'tax_info'

#_______________________________________________ LA_SP_Fire_Rescue Model ________________________________________________________
class LA_SP_Fire_Rescue_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    description = models.TextField(null=True)
    officer = models.CharField(max_length=255, null=True)
    issued_date = models.DateField(null=True)
    expired_date = models.DateField(null=True)

    class Meta:
                managed = True
                db_table = 'la_sp_fire_rescue'

#_______________________________________________ Attrib Panel Image Upload Model ________________________________________________
class Attrib_Image_Model(models.Model):
    image_id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    user_id = models.IntegerField(null=False)
    file_path = models.FileField(upload_to='documents/images', null=True)

    status = models.BooleanField(null=False, default=True)
    remark = models.CharField(max_length=255, null=True)

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'attrib_panel_images'

#_______________________________________________ Messages Model _________________________________________________________________
class Messages_Model(models.Model):
    msg_id = models.AutoField(primary_key=True)

    user_id_sender = models.IntegerField(null=False)
    date_sent = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=255, null=False)
    content = models.TextField(null=False)

    user_id_receiver = models.IntegerField(null=False)
    view_status = models.BooleanField(null=False, default=False)
    date_viewed = models.DateTimeField(null=True) # Automatically update this field in the backend when view_status is patched to True
    done_status = models.BooleanField(null=False, default=False)
    hide_status = models.BooleanField(null=False, default=False)

    file_path = models.FileField(upload_to='documents/message_attachements', null=True)

    class Meta:
            managed = True
            db_table = 'messages'

#_______________________________________________ Inquiries Model ________________________________________________________________
class Inquiries_Model(models.Model):
    inq_id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    user_id_creator = models.IntegerField(null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    inquiry_type = models.CharField(max_length=255, null=False)
    content = models.TextField(null=True)

    user_id_assigned = models.IntegerField(null=False)
    view_status = models.BooleanField(null=False, default=False)
    date_viewed = models.DateTimeField(null=True) # Automatically update this field in the backend when view_status is patched to True
    done_status = models.BooleanField(null=False, default=False)
    hide_status = models.BooleanField(null=False, default=False)

    class Meta:
            managed = True
            db_table = 'Inquiries'

#_______________________________________________ Reminders Model ________________________________________________________________
class Reminders_Model(models.Model):
    rmd_id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    user_id_creator = models.IntegerField(null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    reminder_type = models.CharField(max_length=255, null=False)
    content = models.TextField(null=True)
    date_remind = models.DateTimeField(null=False)

    done_status = models.BooleanField(null=False, default=False)
    hide_status = models.BooleanField(null=False, default=False)

    class Meta:
            managed = True
            db_table = 'reminders'

#_______________________________________________ Tags Model _____________________________________________________________________
class Tags_Model(models.Model):
    tag_id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    user_id_creator = models.IntegerField(null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    tag_type = models.CharField(max_length=255, null=False)
    content = models.TextField(null=True)

    active_status = models.BooleanField(null=False, default=True)
    deleted_user = models.CharField(max_length=255, null=True)
    date_deleted = models.DateTimeField(null=True)

    class Meta:
            managed = True
            db_table = 'tags'

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

#_______________________________________________ Last Active Time Model _________________________________________________________
class Last_Active_Model(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=False)
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
