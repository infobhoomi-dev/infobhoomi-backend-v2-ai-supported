from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .models import *
from .constant import *


User = get_user_model()

#_______________________________________________ User Serializer _________________________________________________
class UserSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()  # Rename dep_name to department
    last_active = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password', 'first_name', 'last_name', 
            'mobile', 'address', 'nic', 'birthday', 'sex', 'org_id', 'dep_id', 
            'emp_id', 'post', 'user_type', 'is_active', 'department', 'last_login', 'last_active'
            )
        
        extra_kwargs = {
            'password': {'write_only': True},
            'org_id': {'read_only': True},
            'user_type': {'read_only': True},
            'last_login': {'read_only': True},
            }

    # Retrieve the department name using dep_id
    def get_department(self, obj):
        dep = SL_Department_Model.objects.filter(dep_id=obj.dep_id).first()
        return dep.dep_name if dep else None
    
    # get last_active time from Last_Active_Model using user_id
    def get_last_active(self, obj):
        record = Last_Active_Model.objects.filter(user_id=obj.id).first()
        return record.active_time if record else None

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            mobile=validated_data['mobile'],
            address=validated_data['address'],
            nic=validated_data['nic'],
            birthday=validated_data['birthday'],
            sex=validated_data['sex'],
            org_id=self.context['org_id'],  # ✅ Use context
            dep_id=validated_data['dep_id'],
            emp_id=validated_data['emp_id'],
            post=validated_data['post'],
            is_active=validated_data.get('is_active', True)
        )

         # Add new record to Last_Active_Model
        Last_Active_Model.objects.get_or_create(user_id=user.id, defaults={'active_time': None})

        return user

#_______________________________________________ User Login Serializer ___________________________________________
class UserLoginSerializer(serializers.ModelSerializer):

    user_id = serializers.IntegerField(source='id')  # Rename 'id' to 'user_id'
    role_id = serializers.IntegerField()  # Inject manually from view

    class Meta:
        model = User
        fields = ['user_id', 'user_type', 'org_id', 'role_id']

#_______________________________________________ User Serializer for User List (Add user roles) __________________
class UserSerializer_Add_UserRoles(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()  # Rename dep_name to department

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'department', 'user_type')

    def get_department(self, obj):
        # Retrieve the department name using dep_id
        dep = SL_Department_Model.objects.filter(dep_id=obj.dep_id).first()
        return dep.dep_name if dep else None

#_______________________________________________ User Serializer for get Geom_Create_By (Admin only) _____________
class Geom_Create_by_Serializer(serializers.Serializer):
    
    id = serializers.IntegerField() # User ID
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    date_created = serializers.DateTimeField()  # From Survey_Rep_DATA_Model

#_______________________________________________ Update User Serializer __________________________________________
class Update_User_Serializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

#_______________________________________________ Token Serializer ________________________________________________
#_______________________________________________ Change password Serializer ______________________________________
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)

#_______________________________________________ PASSWORD Check Serializer _______________________________________
class UserPasswordCheckSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

#_______________________________________________ Recent Users Serializer _________________________________________
class Recent_Users_Login_Serializer(serializers.ModelSerializer):

    department = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'user_type', 'department', 'last_login']

    def get_department(self, obj):
        if obj.dep_id:
            dep = SL_Department_Model.objects.filter(dep_id=obj.dep_id).first()
            return dep.dep_name if dep else None
        return None

#_______________________________________________ Admin Acc Data Serializer _______________________________________
class Admin_Acc_Data_Serializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "mobile",
            "post",
        ]




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




#_______________________________________________ Test json _______________________________________________________
class TestJsonSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = TestJsonModel
        geo_field = 'geom'
        fields = '__all__'

class Test_Data_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Test_Data_Model
        fields = '__all__'

    def validate_users(self, value):
        # Ensure usernames are unique within the array
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Usernames in the users field must be unique within the array.")

        # Ensure usernames are unique across all records
        for user in value:
            if Test_Data_Model.objects.filter(~Q(id=self.instance.id if self.instance else None), users__contains=[user]).exists():
                raise serializers.ValidationError(f"Username '{user}' already exists in another record.")
        
        return value

class Temp_Import_Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = Temp_Import_Model
        geo_field = 'geom'
        fields = ('layer_id','user_id','geom')


#_______________________________________________ CityJson Serializer _____________________________________________
class City_Object_Serializer(serializers.ModelSerializer):
    class Meta:
        model = City_Object_Model
        fields = '__all__'

class CityJSON_Serializer(serializers.ModelSerializer):
    class Meta:
        model = CityJSON_Model
        fields = '__all__'

#_______________________________________________ sl_gnd_10m Serializer ___________________________________________
class sl_gnd_10m_Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = sl_gnd_10m_Model
        geo_field = 'geom'
        fields = '__all__'

#------------------------------------------------------------------------------
class sl_gnd_10m_Attrb_Serializer(serializers.ModelSerializer):
    class Meta:
        model = sl_gnd_10m_Model
        fields = ('pd', 'dist', 'dsd', 'gnd', 'gid')

#_______________________________________________ Layer Serializer ________________________________________________
class LayerDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayersModel
        fields = '__all__'

        extra_kwargs = {
            'user_id': {'read_only': True},  # This prevents the "user_id is required" error
        }

#_______________________________________________ Survey Rep Serializer ___________________________________________
class Survey_Rep_DATA_Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = Survey_Rep_DATA_Model
        geo_field = 'geom'
        fields = '__all__'

    def create(self, validated_data):
        # The serializer only creates the main model
        return super().create(validated_data)

#------------------------------------------------------------------------------
class Survey_Rep_DATA_Overview_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Survey_Rep_DATA_Model
        fields = ['dimension_2d_3d','area','reference_coordinate']

#_______________________________________________ Survey Rep History Serializer ___________________________________
class Survey_Rep_History_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Survey_Rep_History_Model
        fields = '__all__'

#------------------------------------------------------------------------------
class Survey_Rep_History_Serializer_username(serializers.ModelSerializer):
    geom_type = serializers.SerializerMethodField()

    class Meta:
        model = Survey_Rep_History_Model
        fields = '__all__'
        extra_fields = ['geom_type']  # Include the custom field in the response

    def get_geom_type(self, obj):
        survey_data = Survey_Rep_DATA_Model.objects.filter(id=obj.su_id).first()
        return survey_data.geom_type if survey_data else None

#_______________________________________________ Survey Rep Geom History Serializer ______________________________
class Survey_Rep_Geom_History_Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = Survey_Rep_Geom_History_Model
        geo_field = 'geom'
        fields = ('geom', 'user_id', 'date_created')

#_______________________________________________ Search Geom Serializer __________________________________________
class Search_Geom_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Survey_Rep_DATA_Model
        fields = ('id', 'layer_id', 'gnd_id')





#_______________________________________________ User Roles Serializer ___________________________________________
class User_Roles_Serializer(serializers.ModelSerializer):
    class Meta:
        model = User_Roles_Model
        fields = '__all__'

#------------------------------------------------------------------------------
class User_Roles_Admin_Serializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    class Meta:
        model = User_Roles_Model
        fields = ('role_id', 'role_name', 'users', 'remark', 'role_type')

    def get_users(self, obj):

        if not obj.users:
            return []
        
        user_details = User.objects.filter(
            id__in=obj.users
        ).values('id', 'first_name', 'last_name', 'username', 'email', 'dep_id').order_by('first_name')

        # Fetch department details for all dep_ids
        dep_ids = {user['dep_id'] for user in user_details if user['dep_id']}
        department_details = {dep['dep_id']: dep['dep_name'] for dep in SL_Department_Model.objects.filter(dep_id__in=dep_ids).values('dep_id', 'dep_name')}

        users_list = []
        for user in user_details:
            users_list.append({
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "dep_id": user["dep_id"],
                "department": department_details.get(user['dep_id'], None),
                "first_name": f"{user['first_name']} {user.get('last_name', '')}".strip()
            })

        return users_list
    
#------------------------------------------------------------------------------
class User_Roles_Create_Serializer(serializers.ModelSerializer):
    class Meta:
        model = User_Roles_Model
        fields = '__all__'

        extra_kwargs = {
            'admin_id': {'required': False},
            'org_id': {'required': False}
        }

    def create(self, validated_data):
        user = self.context['request'].user  # Get the authenticated user
        validated_data['admin_id'] = user.id
        validated_data['org_id'] = user.org_id
        return super().create(validated_data)

#_______________________________________________ Role Permission Serializer ______________________________________
class Role_permission_Get_Serializer(serializers.ModelSerializer):

    permission_name = serializers.CharField(source='permission_id.permission_name', read_only=True)
    category = serializers.CharField(source='permission_id.category', read_only=True)
    sub_category = serializers.CharField(source='permission_id.sub_category', read_only=True)

    class Meta:
        model = Role_Permission_Model
        fields = ('id', 'permission_id', 'category', 'sub_category', 'permission_name', 'view', 'add', 'edit', 'delete')

#------------------------------------------------------------------------------
class Role_permission_Get_LayerPanel_Serializer(serializers.ModelSerializer):

    layer_name = serializers.CharField(source='permission_id.permission_name', read_only=True)
    layer_id = serializers.SerializerMethodField()

    class Meta:
        model = Role_Permission_Model
        fields = ('permission_id', 'layer_id', 'layer_name', 'view', 'add', 'edit', 'delete')

    def get_layer_id(self, obj):
        return PERMISSION_TO_LAYER_MAP.get(obj.permission_id.permission_id)

#------------------------------------------------------------------------------
class Role_permission_Update_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Role_Permission_Model
        fields = '__all__'

#_______________________________________________ SL_Party Serializer _____________________________________________
class Party_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Party_Model
        fields = '__all__'

#------------------------------------------------------------------------------
class Party_Type_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Party_Model
        fields = ('pid', 'party_name', 'party_full_name', 'ext_pid')

#------------------------------------------------------------------------------
class Party_Update_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Party_Model
        # fields = '__all__'
        fields = ['pid',
                  'party_name',
                  'party_full_name',
                  'la_party_type',
                  'sl_party_type',
                  'ext_pid_type',
                  'ext_pid',
                  'ref_id',
                  'sl_group_party_type',
                  'pmt_address',
                  'tp',
                  'specific_tp',
                  'email',
                  'date_of_birth',
                  'gender',
                  'other_reg',
                  'remark']

#_______________________________________________ Residence Info Serializer _______________________________________
class Residence_Info_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Residence_Info_Model
        fields = '__all__'

#_______________________________________________ LA RRR Serializer _______________________________________________
class LA_RRR_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_RRR_Model
        fields = '__all__'

#_______________________________________________ LA Administrative Serializer ____________________________________
class LA_Admin_Source_Serializer(serializers.ModelSerializer):

    class Meta:
        model = LA_Admin_Source_Model
        fields = '__all__'

#------------------------------------------------------------------------------ (pdf)
class User_Admin_Source_Activity_Serializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = LA_Admin_Source_Model
        fields = ('admin_source_id', 'admin_source_type', 'date_created', 'file_url')

    def get_file_url(self, obj):
        if obj.file_path:
            sanitized_path = str(obj.file_path).replace("\\", "/")
            return f"{base_url}secure-media/{sanitized_path}"
        return None

#------------------------------------------------------------------------------ (pdf)
class Ownership_Rights_Serializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = LA_Admin_Source_Model
        fields = ('reference_no', 'file_url')
 
    def get_file_url(self, obj):
        if obj.file_path:
            # Convert FieldFile to string and replace backslashes with forward slashes
            sanitized_path = str(obj.file_path).replace("\\", "/")
            return f"{base_url}secure-media/{sanitized_path}"
        return None

#------------------------------------------------------------------------------ (pdf)
class LA_Admin_Source_RRR_Rights_Serializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = LA_Admin_Source_Model
        fields = ('admin_source_id', 'admin_source_type', 'acceptance_date', 'file_url')

    def get_file_url(self, obj):
        if obj.file_path:
            sanitized_path = str(obj.file_path).replace("\\", "/")
            return f"{base_url}secure-media/{sanitized_path}"
        return None

#_______________________________________________ SL BA Unit Serializer ___________________________________________
class SL_BA_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = SL_BA_Unit_Model
        fields = '__all__'

#_______________________________________________ SL Elect_LocalAuth Serializer ___________________________________
#_______________________________________________ Assessment Ward Serializer ______________________________________
class Assessment_Ward_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment_Ward_Model
        fields = ['id', 'ward_name', 'org_id']
        read_only_fields = ['id', 'org_id']

#_______________________________________________ LA Spatial Unit Serializer ______________________________________
class LA_Spatial_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_Spatial_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Land_Unit Serializer ______________________________________
class LA_LS_Land_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Land_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Zoning Serializer _________________________________________
class LA_LS_Zoning_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Zoning_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Physical_Env Serializer ___________________________________
class LA_LS_Physical_Env_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Physical_Env_Model
        fields = '__all__'

#_______________________________________________ LA_BAUnit_SpatialUnit Serializer ________________________________
class LA_BAUnit_SpatialUnit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_BAUnit_SpatialUnit_Model
        fields = '__all__'

#_______________________________________________ LA_RRR_Restriction Serializer ___________________________________
class LA_RRR_Restriction_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_RRR_Restriction_Model
        fields = '__all__'

#_______________________________________________ LA_RRR_Responsibility Serializer _________________________________
class LA_RRR_Responsibility_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_RRR_Responsibility_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Utinet_LU Serializer ______________________________________
class LA_LS_Utinet_LU_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Utinet_LU_Model
        fields = '__all__'

#------------------------------------------------------------------------------
class Lnd_Utinet_info_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Utinet_LU_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Build_Unit Serializer _____________________________________
class LA_LS_Build_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Build_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Utinet_BU Serializer ______________________________________
class LA_LS_Utinet_BU_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Utinet_BU_Model
        fields = '__all__'

#------------------------------------------------------------------------------
class Bld_Utinet_info_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Utinet_BU_Model
        fields = ('water', 'water_drink', 'elec', 'tele', 'internet', 'sani_sewer', 'sani_gully', 'garbage_dispose', 'drainage')
    
#_______________________________________________ LA_LS_Apt_Unit Serializer _______________________________________
class LA_LS_Apt_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Apt_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Utinet_AU Serializer ______________________________________
class LA_LS_Utinet_AU_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Utinet_AU_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Ols_Polygon_Unit Serializer _______________________________
class LA_LS_Ols_Polygon_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Ols_Polygon_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Ols_PointLine_Unit Serializer _____________________________
class LA_LS_Ols_PointLine_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Ols_PointLine_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_MyLayer_Polygon_Unit Serializer ___________________________
class LA_LS_MyLayer_Polygon_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_MyLayer_Polygon_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_MyLayer_PointLine_Unit Serializer _________________________
class LA_LS_MyLayer_PointLine_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_MyLayer_PointLine_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Utinet_Ols Serializer _____________________________________
class LA_LS_Utinet_Ols_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Utinet_Ols_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Ils_Unit Serializer _______________________________________
class LA_LS_Ils_Unit_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Ils_Unit_Model
        fields = '__all__'

#_______________________________________________ LA_LS_Utinet_Ils Serializer _____________________________________
class LA_LS_Utinet_Ils_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_LS_Utinet_Ils_Model
        fields = '__all__'

#_______________________________________________ LA_Spatial_Unit_Sketch_Ref Serializer ___________________________
class LA_Spatial_Unit_Sketch_Ref_Serializer(serializers.ModelSerializer):
    class Meta:
        model = LA_Spatial_Unit_Sketch_Ref_Model
        fields = '__all__'

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


# __ Dynamic Attribute Serializer __
class DynamicAttribute_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Dynamic_Attribute_Model
        fields = ('id', 'su_id', 'section_key', 'label', 'value', 'date_created')
