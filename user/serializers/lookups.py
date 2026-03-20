from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

# ====================================================================================================================================

#_______________________________________________ Lst_SL_Party_Type_1 Serializer __________________________________
class Lst_SL_Party_Type_1_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_Party_Type_1_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_PartyRoleType_2 Serializer _______________________________
class Lst_SL_PartyRoleType_2_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_PartyRoleType_2_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_Education_Level_3 Serializer _____________________________
class Lst_SL_Education_Level_3_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_Education_Level_3_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_Race_4 Serializer ________________________________________
class Lst_SL_Race_4_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_Race_4_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_HealthStatus_5 Serializer ________________________________
class Lst_SL_HealthStatus_5_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_HealthStatus_5_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_MarriedStatus_6 Serializer _______________________________
class Lst_SL_MarriedStatus_6_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_MarriedStatus_6_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_Religions_7 Serializer ___________________________________
class Lst_SL_Religions_7_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_Religions_7_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_GenderType_8 Serializer __________________________________
class Lst_SL_GenderType_8_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_GenderType_8_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_RightType_9 Serializer ___________________________________
class Lst_SL_RightType_9_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_RightType_9_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_BAUnitType_10 Serializer _________________________________
class Lst_SL_BAUnitType_10_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_BAUnitType_10_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_AdminRestrictionType_11 Serializer _______________________
class Lst_SL_AdminRestrictionType_11_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_AdminRestrictionType_11_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_AnnotationType_12 Serializer _____________________________
class Lst_SL_AnnotationType_12_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_AnnotationType_12_Model
        fields = '__all__'
#_______________________________________________ Lst_Sl_MortgageType_13 Serializer _______________________________
class Lst_Sl_MortgageType_13_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_Sl_MortgageType_13_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_RightShareType_14 Serializer _____________________________
class Lst_SL_RightShareType_14_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_RightShareType_14_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_AdministrativeStatausType_15 Serializer __________________
class Lst_SL_AdministrativeStatausType_15_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_AdministrativeStatausType_15_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_AdministrativeSourceType_16 Serializer ___________________
class Lst_SL_AdministrativeSourceType_16_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_AdministrativeSourceType_16_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_ResponsibilityType_17 Serializer _________________________
class Lst_SL_ResponsibilityType_17_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_ResponsibilityType_17_Model
        fields = '__all__'
#_______________________________________________ Lst_LA_BAUnitType_18 Serializer _________________________________
class Lst_LA_BAUnitType_18_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_LA_BAUnitType_18_Model
        fields = '__all__'
#_______________________________________________ Lst_SU_SL_LevelContentType_19 Serializer ________________________
class Lst_SU_SL_LevelContentType_19_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SU_SL_LevelContentType_19_Model
        fields = '__all__'
#_______________________________________________ Lst_SU_SL_RegesterType_20 Serializer ____________________________
class Lst_SU_SL_RegesterType_20_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SU_SL_RegesterType_20_Model
        fields = '__all__'
#_______________________________________________ Lst_SU_SL_StructureType_21 Serializer ___________________________
class Lst_SU_SL_StructureType_21_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SU_SL_StructureType_21_Model
        fields = '__all__'
#_______________________________________________ Lst_SU_SL_Water_22 Serializer ___________________________________
class Lst_SU_SL_Water_22_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SU_SL_Water_22_Model
        fields = '__all__'
#_______________________________________________ xLst_SU_SL_Sanitation_23 Serializer _____________________________
class Lst_SU_SL_Sanitation_23_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SU_SL_Sanitation_23_Model
        fields = '__all__'
#_______________________________________________ Lst_SU_SL_Roof_Type_24 Serializer _______________________________
class Lst_SU_SL_Roof_Type_24_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SU_SL_Roof_Type_24_Model
        fields = '__all__'
#_______________________________________________ Lst_SU_SL_Wall_Type_25 Serializer _______________________________
class Lst_SU_SL_Wall_Type_25_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SU_SL_Wall_Type_25_Model
        fields = '__all__'
#_______________________________________________ Lst_SU_SL_Floor_Type_26 Serializer ______________________________
class Lst_SU_SL_Floor_Type_26_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SU_SL_Floor_Type_26_Model
        fields = '__all__'
#_______________________________________________ Lst_SR_SL_SpatialSourceTypes_27 Serializer ______________________
class Lst_SR_SL_SpatialSourceTypes_27_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SR_SL_SpatialSourceTypes_27_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtLandUseType_28 Serializer _____________________________
class Lst_EC_ExtLandUseType_28_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtLandUseType_28_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtLandUseSubType_29 Serializer __________________________
class Lst_EC_ExtLandUseSubType_29_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtLandUseSubType_29_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtOuterLegalSpaceUseType_30 Serializer __________________
class Lst_EC_ExtOuterLegalSpaceUseType_30_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtOuterLegalSpaceUseType_30_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtOuterLegalSpaceUseSubType_31 Serializer _______________
class Lst_EC_ExtOuterLegalSpaceUseSubType_31_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtOuterLegalSpaceUseSubType_31_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtBuildUseType_32 Serializer ____________________________
class Lst_EC_ExtBuildUseType_32_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtBuildUseType_32_Model
        fields = '__all__'
#_______________________________________________ xLst_EC_ExtBuildUseSubType_33 Serializer ________________________
class Lst_EC_ExtBuildUseSubType_33_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtBuildUseSubType_33_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtDivisionType_34 Serializer ____________________________
class Lst_EC_ExtDivisionType_34_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtDivisionType_34_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtFeatureMainType_35 Serializer _________________________
class Lst_EC_ExtFeatureMainType_35_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtFeatureMainType_35_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtFeatureMainType_36 Serializer _________________________
class Lst_EC_ExtFeatureMainType_36_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtFeatureMainType_36_Model
        fields = '__all__'
#_______________________________________________ Lst_EC_ExtFeatureMainType_37 Serializer _________________________
class Lst_EC_ExtFeatureMainType_37_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_EC_ExtFeatureMainType_37_Model
        fields = '__all__'
#_______________________________________________ Lst_Telecom_Providers_38 Serializer _____________________________
class Lst_Tele_Providers_38_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_Tele_Providers_38_Model
        fields = '__all__'
#_______________________________________________ Lst_Internet_Providers_39 Serializer ____________________________
class Lst_Int_Providers_39_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_Int_Providers_39_Model
        fields = '__all__'
#_______________________________________________ Lst_Organization_Names_40 Serializer ____________________________
class Lst_Org_Names_40_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_Org_Names_40_Model
        fields = '__all__'
#_______________________________________________ Lst_SL_Group_Party_Type_41 Serializer ___________________________
class Lst_SL_Group_Party_Type_41_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Lst_SL_Group_Party_Type_41_Model
        fields = '__all__'

# ====================================================================================================================================
