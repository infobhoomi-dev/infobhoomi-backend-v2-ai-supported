from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import *
from ..constant import *

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

    # Retrieve the department name — uses annotated value when queryset pre-fetched it (no extra query)
    def get_department(self, obj):
        if hasattr(obj, 'dep_name_annotated'):
            return obj.dep_name_annotated
        dep = SL_Department_Model.objects.filter(dep_id=obj.dep_id).first()
        return dep.dep_name if dep else None

    # get last_active time — uses annotated value when queryset pre-fetched it (no extra query)
    def get_last_active(self, obj):
        if hasattr(obj, 'last_active_annotated'):
            return obj.last_active_annotated
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
        fields = ['user_id', 'user_type', 'org_id', 'emp_id', 'role_id']

#_______________________________________________ User Serializer for User List (Add user roles) __________________
class UserSerializer_Add_UserRoles(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()  # Rename dep_name to department

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'department', 'user_type')

    def get_department(self, obj):
        if hasattr(obj, 'dep_name_annotated'):
            return obj.dep_name_annotated
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
        if hasattr(obj, 'dep_name_annotated'):
            return obj.dep_name_annotated
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
