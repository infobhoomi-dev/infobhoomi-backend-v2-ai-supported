from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

# __ Dynamic Attribute Serializer __
class DynamicAttribute_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Dynamic_Attribute_Model
        fields = ('id', 'su_id', 'section_key', 'label', 'value', 'date_created')
