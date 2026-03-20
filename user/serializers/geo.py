from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

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
