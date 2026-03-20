from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

#_______________________________________________ Layer Serializer ________________________________________________
class LayerDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayersModel
        fields = '__all__'

        extra_kwargs = {
            'user_id': {'read_only': True},  # This prevents the "user_id is required" error
        }
