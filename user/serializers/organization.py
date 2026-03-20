from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

#_______________________________________________ SL_Organization Serializer ______________________________________
class SL_Organization_Serializer(serializers.ModelSerializer):
    org_loc = serializers.SerializerMethodField()
    org_area = serializers.SerializerMethodField()

    class Meta:
        model = SL_Organization_Model
        fields = [
            "org_id", "display_name", "permit_start_date", "permit_end_date",
            "org_level",
            "director", "contact_no", "org_email", "org_address",
            "subscription_plan", "users_limit", "status",
            "org_loc", "org_area"
        ]

    def get_org_loc(self, obj):
        return Org_Location_Model.objects.filter(org_id=obj.org_id, geom__isnull=False).exists()

    def get_org_area(self, obj):
        return Org_Area_Model.objects.filter(org_id=obj.org_id).exclude(org_area=None).exists()

#------------------------------------------------------------------------------
class SL_Org_Details_Serializer(serializers.ModelSerializer):
    class Meta:
        model = SL_Organization_Model
        fields = ('display_name', 'permit_end_date', 'subscription_plan', 'users_limit', 'director', 'contact_no', 'org_email', 'org_address', 'status')

#_______________________________________________ SL_Department Serializer ________________________________________
class SL_Department_Serializer(serializers.ModelSerializer):

    org_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = SL_Department_Model
        fields = '__all__'

#_______________________________________________ SL_Org_Area_Parent_Bndry Serializer _____________________________
class SL_Org_Area_Parent_Bndry_Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = SL_Org_Area_Parent_Bndry_Model
        geo_field = 'geom'
        fields = '__all__'

#_______________________________________________ SL_Org_Area_Child_Bndry Serializer ______________________________
class SL_Org_Area_Child_Bndry_Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = SL_Org_Area_Child_Bndry_Model
        geo_field = 'geom'
        fields = '__all__'

#_______________________________________________ History_Spartialunit_Attrib Serializer __________________________
class History_Spartialunit_Attrib_Serializer(serializers.ModelSerializer):
    class Meta:
        model = History_Spartialunit_Attrib_Model
        fields = '__all__'

#_______________________________________________ LA_Spatial_Source Serializer (pdf) ______________________________
class LA_Spatial_Source_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_Spatial_Source_Model
        fields = '__all__'

#------------------------------------------------------------------------------
class LA_Spatial_Source_Retrive_Serializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = LA_Spatial_Source_Model
        fields = ('source_id', 'spatial_source_type', 'description', 'date_accept', 'surveyor_name', 'file_url')

    # def get_file_url(self, obj):
    #     if obj.file_path:
    #         return f"{base_url}secure-media/{obj.file_path}" # Generate the secure URL
    #     return None

    def get_file_url(self, obj):
        if obj.file_path:
            # Convert FieldFile to string and replace backslashes with forward slashes
            sanitized_path = str(obj.file_path).replace("\\", "/")
            return f"{base_url}secure-media/{sanitized_path}"
        return None

#------------------------------------------------------------------------------
class LA_Spatial_Source_Metadata_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_Spatial_Source_Model
        fields = ('spatial_source_type', 'source_id', 'description', 'date_accept', 'surveyor_name')

#_______________________________________________ Assessment Serializer ___________________________________________
class Assessment_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment_Model
        fields = '__all__'

#------------------------------------------------------------------------------
class Assessment_Info_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment_Model
        fields = ('assessment_no','assessment_annual_value','assessment_percentage','date_of_valuation','year_of_assessment','property_type','ass_out_balance','assessment_name','land_value','market_value','tax_status')

#_______________________________________________ Tax_Info Serializer _____________________________________________
class Tax_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Tax_Info_Model
        fields = '__all__'

#------------------------------------------------------------------------------
class Tax_Info_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Tax_Info_Model
        fields = ('tax_annual_value', 'tax_percentage', 'tax_date', 'tax_type')

#_______________________________________________ LA_SP_Fire_Rescue Serializer ____________________________________
class LA_SP_Fire_Rescue_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_SP_Fire_Rescue_Model
        fields = '__all__'

#------------------------------------------------------------------------------
#_______________________________________________ Attrib Panel Image Serializer ___________________________________
class Attrib_Image_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Attrib_Image_Model
        fields = '__all__'

#_______________________________________________ Messages Serializer _____________________________________________
class Messages_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Messages_Model
        fields = '__all__'

#_______________________________________________ Inquiries Serializer ____________________________________________
class Inquiries_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiries_Model
        fields = '__all__'

#_______________________________________________ Reminders Serializer ____________________________________________
class Reminders_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Reminders_Model
        fields = '__all__'

#_______________________________________________ Tags Serializer _________________________________________________
class Tags_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Tags_Model
        fields = '__all__'

#_______________________________________________ Organization Location Serializer ________________________________
class Org_Location_Serializer(GeoFeatureModelSerializer):

    org_name = serializers.SerializerMethodField()

    class Meta:
        model = Org_Location_Model
        geo_field = 'geom'
        fields = '__all__'

        extra_fields = ['org_name']

    def get_org_name(self, obj):
        try:
            org = SL_Organization_Model.objects.get(pk=obj.org_id)
            return org.display_name
        except SL_Organization_Model.DoesNotExist:
            return None

#_______________________________________________ Organization Area Serializer ____________________________________
class Org_Area_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Org_Area_Model
        fields = '__all__'

#_______________________________________________ Last Active Serializer __________________________________________
#_______________________________________________ Import Vector Serializer ________________________________________
# class Import_VectorDATA_Serializer(GeoFeatureModelSerializer):
#     class Meta:
#         model = Import_VectorDATA_Model
#         geo_field = 'geom'
#         fields = '__all__'

#------------------------------------------------------------------------------
# class Import_VectorDATA_List_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = Import_VectorDATA_Model
#         fields = ['id', 'dataset_name']

#_______________________________________________ Import Geotif Serializer ________________________________________
# class Import_RasterData_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = Import_RasterData_Model
#         fields = '__all__'

#------------------------------------------------------------------------------
# class RasterData_List_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = Import_RasterData_Model
#         fields = ['id', 'datasetName', 'capture_date', 'remark']



#_______________________________________________ SL Rights & Liabilities Serializer ______________________________
# class SL_Rights_Liabilities_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = SL_Rights_Liabilities_Model
#         fields = '__all__'

#------------------------------------------------------------------------------
# class SL_Rights_Liabilities_Activity_Serializer(serializers.ModelSerializer):
#     party = serializers.CharField(source='party.party_name', read_only=True)
#     sl_rl_parties = serializers.SerializerMethodField()


#     class Meta:
#         model = SL_Rights_Liabilities_Model
#         fields = ('rrr_id', 'sl_right_type', 'share', 'party', 'sl_rl_parties', 'time_spec', 'date_created')

#     def get_sl_rl_parties(self, obj):
#         # Fetch all parties by their IDs in the `sl_rl_parties` array field
#         parties = Party_Model.objects.filter(pid__in=obj.sl_rl_parties).values_list('party_name', flat=True)
#         return list(parties)

#_______________________________________________ Admin Annotation Serializer _____________________________________
# class Admin_Annotation_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = Admin_Annotation_Model
#         fields = '__all__'

#------------------------------------------------------------------------------
# class Admin_Annotation_Activity_Serializer(serializers.ModelSerializer):
#     claiment_pid = serializers.CharField(source='claiment_pid.party_name', read_only=True)
#     a_a_parties = serializers.SerializerMethodField()

#     class Meta:
#         model = Admin_Annotation_Model
#         fields = ('rrr_id', 'admin_anno_type', 'share', 'area', 'claiment_pid', 'a_a_parties', 'time_spec', 'date_created')

#     def get_a_a_parties(self, obj):
#         # Fetch all parties by their IDs in the `a_a_parties` array field
#         parties = Party_Model.objects.filter(pid__in=obj.a_a_parties).values_list('party_name', flat=True)
#         return list(parties)

#_______________________________________________ SL Admin Restrict Serializer ____________________________________
# class SL_Admin_Restrict_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = SL_Admin_Restrict_Model
#         fields = '__all__'

#------------------------------------------------------------------------------
# class SL_Admin_Restrict_Activity_Serializer(serializers.ModelSerializer):
#     gov_party = serializers.CharField(source='gov_party.party_name', read_only=True)

#     class Meta:
#         model = SL_Admin_Restrict_Model
#         fields = ('rrr_id', 'sl_adm_res_type', 'share', 'adm_res_legal_space', 'adm_res_legal_prov', 'gov_party', 'time_spec', 'date_created')

#_______________________________________________ LA Mortgage Serializer __________________________________________
# class LA_Mortgage_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = LA_Mortgage_Model
#         fields = '__all__'

#------------------------------------------------------------------------------
# class LA_Mortgage_Activity_Serializer(serializers.ModelSerializer):
#     mortgagor = serializers.CharField(source='mortgagor.party_name', read_only=True)

#     class Meta:
#         model = LA_Mortgage_Model
#         fields = ('rrr_id', 'sl_mortgage_type', 'share', 'amount', 'int_rate', 'ranking', 'mort_id', 'mortgagor', 'mortgagee', 'time_spec', 'date_created')

#------------------------------------------------------------------------------
# class LA_Mortgage_Hirtory_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = LA_Mortgage_Model
#         fields = ('share', 'amount', 'int_rate', 'sl_mortgage_type', 'mort_id', 'mortgagor', 'mortgagee', 'time_spec')

#_______________________________________________ SL Rights Serializer ____________________________________________
# class SL_Rights_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = SL_Rights_Model
#         fields = '__all__'

#------------------------------------------------------------------------------
# class SL_Rights_Activity_Serializer(serializers.ModelSerializer):
#     party = serializers.CharField(source='party.party_name', read_only=True)  # Replace 'party' with 'party_name'

#     class Meta:
#         model = SL_Rights_Model
#         fields = ('rrr_id', 'right_type', 'share', 'party', 'time_spec', 'date_created')

#------------------------------------------------------------------------------
# class SL_Rights_History_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = SL_Rights_Model
#         fields = ('rrr_id', 'party', 'right_type', 'share', 'time_spec')

#_______________________________________________ LA Responsibility Serializer ____________________________________
# class LA_Responsibility_Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = LA_Responsibility_Model
#         fields = '__all__'

#------------------------------------------------------------------------------
# class LA_Responsibility_Activity_Serializer(serializers.ModelSerializer):
#     party = serializers.CharField(source='party.party_name', read_only=True)

#     class Meta:
#         model = LA_Responsibility_Model
#         fields = ('rrr_id', 'responsibility_type', 'share', 'party', 'time_spec', 'date_created')
