from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

#_______________________________________________ Survey Rep Serializer ___________________________________________
class Survey_Rep_DATA_Serializer(GeoFeatureModelSerializer):
    class Meta:
        model = Survey_Rep_DATA_Model
        geo_field = 'geom'
        fields = '__all__'
        extra_kwargs = {
            # su_id is set by the view after the initial save (survey_rep.su_id_id = survey_rep.id)
            # so it must never be part of create/update validation.
            'su_id': {'read_only': True},
        }

    def create(self, validated_data):
        # The serializer only creates the main model
        return super().create(validated_data)

#------------------------------------------------------------------------------
class Survey_Rep_DATA_Overview_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Survey_Rep_DATA_Model
        fields = ['dimension_2d_3d', 'calculated_area', 'legal_area', 'legal_area_unit', 'reference_coordinate']

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
