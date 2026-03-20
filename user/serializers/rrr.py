from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

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
