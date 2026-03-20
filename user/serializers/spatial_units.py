from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

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
