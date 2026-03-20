from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

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
