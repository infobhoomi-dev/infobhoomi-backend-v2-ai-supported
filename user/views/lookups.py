from rest_framework.generics import ListCreateAPIView

from ..models import *
from ..serializers import *


# ── Factory ───────────────────────────────────────────────────────────────────
# Each lookup table is a read-only list endpoint with identical behaviour.
# Instead of 41 separate classes, we generate them with a single factory.

def _lookup_view(model, serializer, methods=None):
    """Return a ListCreateAPIView subclass bound to *model* and *serializer*."""
    class View(ListCreateAPIView):
        http_method_names = methods or ['get']
        queryset = model.objects.all().order_by('id')
        serializer_class = serializer
    return View


# ── Generated lookup views (41 total) ────────────────────────────────────────

Lst_SL_Party_Type_1_View                    = _lookup_view(Lst_SL_Party_Type_1_Model,                    Lst_SL_Party_Type_1_Serializer)
Lst_SL_PartyRoleType_2_View                 = _lookup_view(Lst_SL_PartyRoleType_2_Model,                 Lst_SL_PartyRoleType_2_Serializer)
Lst_SL_Education_Level_3_View               = _lookup_view(Lst_SL_Education_Level_3_Model,               Lst_SL_Education_Level_3_Serializer)
Lst_SL_Race_4_View                          = _lookup_view(Lst_SL_Race_4_Model,                          Lst_SL_Race_4_Serializer)
Lst_SL_HealthStatus_5_View                  = _lookup_view(Lst_SL_HealthStatus_5_Model,                  Lst_SL_HealthStatus_5_Serializer)
Lst_SL_MarriedStatus_6_View                 = _lookup_view(Lst_SL_MarriedStatus_6_Model,                 Lst_SL_MarriedStatus_6_Serializer)
Lst_SL_Religions_7_View                     = _lookup_view(Lst_SL_Religions_7_Model,                     Lst_SL_Religions_7_Serializer)
Lst_SL_GenderType_8_View                    = _lookup_view(Lst_SL_GenderType_8_Model,                    Lst_SL_GenderType_8_Serializer)
Lst_SL_RightType_9_View                     = _lookup_view(Lst_SL_RightType_9_Model,                     Lst_SL_RightType_9_Serializer)
Lst_SL_BAUnitType_10_View                   = _lookup_view(Lst_SL_BAUnitType_10_Model,                   Lst_SL_BAUnitType_10_Serializer)
Lst_SL_AdminRestrictionType_11_View         = _lookup_view(Lst_SL_AdminRestrictionType_11_Model,         Lst_SL_AdminRestrictionType_11_Serializer)
Lst_SL_AnnotationType_12_View               = _lookup_view(Lst_SL_AnnotationType_12_Model,               Lst_SL_AnnotationType_12_Serializer)
Lst_Sl_MortgageType_13_View                 = _lookup_view(Lst_Sl_MortgageType_13_Model,                 Lst_Sl_MortgageType_13_Serializer)
Lst_SL_RightShareType_14_View               = _lookup_view(Lst_SL_RightShareType_14_Model,               Lst_SL_RightShareType_14_Serializer)
Lst_SL_AdministrativeStatausType_15_View    = _lookup_view(Lst_SL_AdministrativeStatausType_15_Model,    Lst_SL_AdministrativeStatausType_15_Serializer)
Lst_SL_AdministrativeSourceType_16_View     = _lookup_view(Lst_SL_AdministrativeSourceType_16_Model,     Lst_SL_AdministrativeSourceType_16_Serializer)
Lst_SL_ResponsibilityType_17_View           = _lookup_view(Lst_SL_ResponsibilityType_17_Model,           Lst_SL_ResponsibilityType_17_Serializer)
Lst_LA_BAUnitType_18_View                   = _lookup_view(Lst_LA_BAUnitType_18_Model,                   Lst_LA_BAUnitType_18_Serializer)
Lst_SU_SL_LevelContentType_19_View          = _lookup_view(Lst_SU_SL_LevelContentType_19_Model,          Lst_SU_SL_LevelContentType_19_Serializer)
Lst_SU_SL_RegesterType_20_View              = _lookup_view(Lst_SU_SL_RegesterType_20_Model,              Lst_SU_SL_RegesterType_20_Serializer)
Lst_SU_SL_StructureType_21_View             = _lookup_view(Lst_SU_SL_StructureType_21_Model,             Lst_SU_SL_StructureType_21_Serializer)
Lst_SU_SL_Water_22_View                     = _lookup_view(Lst_SU_SL_Water_22_Model,                     Lst_SU_SL_Water_22_Serializer)
Lst_SU_SL_Sanitation_23_View                = _lookup_view(Lst_SU_SL_Sanitation_23_Model,                Lst_SU_SL_Sanitation_23_Serializer)
Lst_SU_SL_Roof_Type_24_View                 = _lookup_view(Lst_SU_SL_Roof_Type_24_Model,                 Lst_SU_SL_Roof_Type_24_Serializer)
Lst_SU_SL_Wall_Type_25_View                 = _lookup_view(Lst_SU_SL_Wall_Type_25_Model,                 Lst_SU_SL_Wall_Type_25_Serializer)
Lst_SU_SL_Floor_Type_26_View                = _lookup_view(Lst_SU_SL_Floor_Type_26_Model,                Lst_SU_SL_Floor_Type_26_Serializer)
Lst_SR_SL_SpatialSourceTypes_27_View        = _lookup_view(Lst_SR_SL_SpatialSourceTypes_27_Model,        Lst_SR_SL_SpatialSourceTypes_27_Serializer)
Lst_EC_ExtLandUseType_28_View               = _lookup_view(Lst_EC_ExtLandUseType_28_Model,               Lst_EC_ExtLandUseType_28_Serializer)
Lst_EC_ExtLandUseSubType_29_View            = _lookup_view(Lst_EC_ExtLandUseSubType_29_Model,            Lst_EC_ExtLandUseSubType_29_Serializer)
Lst_EC_ExtOuterLegalSpaceUseType_30_View    = _lookup_view(Lst_EC_ExtOuterLegalSpaceUseType_30_Model,    Lst_EC_ExtOuterLegalSpaceUseType_30_Serializer)
Lst_EC_ExtOuterLegalSpaceUseSubType_31_View = _lookup_view(Lst_EC_ExtOuterLegalSpaceUseSubType_31_Model, Lst_EC_ExtOuterLegalSpaceUseSubType_31_Serializer)
Lst_EC_ExtBuildUseType_32_View              = _lookup_view(Lst_EC_ExtBuildUseType_32_Model,              Lst_EC_ExtBuildUseType_32_Serializer)
Lst_EC_ExtBuildUseSubType_33_View           = _lookup_view(Lst_EC_ExtBuildUseSubType_33_Model,           Lst_EC_ExtBuildUseSubType_33_Serializer)
Lst_EC_ExtDivisionType_34_View              = _lookup_view(Lst_EC_ExtDivisionType_34_Model,              Lst_EC_ExtDivisionType_34_Serializer)
Lst_EC_ExtFeatureMainType_35_View           = _lookup_view(Lst_EC_ExtFeatureMainType_35_Model,           Lst_EC_ExtFeatureMainType_35_Serializer)
Lst_EC_ExtFeatureMainType_36_View           = _lookup_view(Lst_EC_ExtFeatureMainType_36_Model,           Lst_EC_ExtFeatureMainType_36_Serializer)
Lst_EC_ExtFeatureMainType_37_View           = _lookup_view(Lst_EC_ExtFeatureMainType_37_Model,           Lst_EC_ExtFeatureMainType_37_Serializer)
Lst_Tele_Providers_38_View                  = _lookup_view(Lst_Tele_Providers_38_Model,                  Lst_Tele_Providers_38_Serializer)
Lst_Int_Providers_39_View                   = _lookup_view(Lst_Int_Providers_39_Model,                   Lst_Int_Providers_39_Serializer)
Lst_Org_Names_40_View                       = _lookup_view(Lst_Org_Names_40_Model,                       Lst_Org_Names_40_Serializer,       methods=['get', 'post'])
Lst_SL_Group_Party_Type_41_View             = _lookup_view(Lst_SL_Group_Party_Type_41_Model,             Lst_SL_Group_Party_Type_41_Serializer)
