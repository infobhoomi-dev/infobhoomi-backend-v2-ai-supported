from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

User = get_user_model()

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
