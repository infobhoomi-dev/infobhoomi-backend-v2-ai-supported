from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


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
