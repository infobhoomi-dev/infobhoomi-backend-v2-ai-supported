from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView, RetrieveUpdateAPIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import check_password
from django.db.models import Q, Min, Subquery, OuterRef
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.timezone import now
from django.utils import timezone
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.functions import Area, Intersection as GeoIntersection

import json, os
from datetime import timedelta

from ..models import *
from ..serializers import *
from ..constant import *
from ..tests import *

User = get_user_model()

#________________________________________________ Layers DATA View ______________________________________________________________
class LayerData_Create_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LayersModel.objects.all()
    serializer_class = LayerDataSerializer

    def perform_create(self, serializer):

        user_obj = self.request.user
        user_id = user_obj.id
        org_id = user_obj.org_id
        layer_name = serializer.validated_data.get("layer_name")

        if user_obj.user_type == "user":
            add_permission_id = 94

        elif user_obj.user_type in ["admin", "super_admin"]:
            add_permission_id = 253


        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            raise PermissionDenied({"error": "User has no assigned roles."})

        role_id = user_roles.values_list('role_id', flat=True).first()

        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=add_permission_id,
            add=True
        ).exists()

        if not has_permission:
            raise PermissionDenied({"error": "You do not have permission."})


        if LayersModel.objects.filter(user_id=user_id, layer_name=layer_name).exists():
            raise serializers.ValidationError({"error": "Layer name already exists for this user."})

        if user_obj.user_type in ["admin", "super_admin"]:
            group_name = ["org"]
        else:
            group_name = serializer.validated_data.get("group_name", None)

        serializer.save(user_id=user_id, org_id=org_id, group_name=group_name)

#------------------------------------------------------------------------------
class LayerData_Get_User_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        user_obj = request.user
        org_id = user_obj.org_id
        userID = user_obj.id

        group_data = LayersModel.objects.filter(
            Q(group_name__contains=["default"]) |
            Q(group_name__contains=[userID]) |
            (Q(group_name__contains=["org"]) & Q(org_id=org_id)) |
            Q(user_id=userID)
        )
        serializer = LayerDataSerializer(group_data, many=True)

        serialized_data = serializer.data # Modify serialized data to include 'shared_users'

        for layer in serialized_data:
            group_name_ids = layer.get("group_name", [])  # Get group_name list

            if not group_name_ids:  # Handle None or empty list cases
                layer["shared_users"] = []
                continue

            if isinstance(group_name_ids, list):

                numeric_ids = [int(value) for value in group_name_ids if str(value).isdigit()] # Extract numeric IDs from group_name

                shared_users = list(User.objects.filter(id__in=numeric_ids).values("email", "first_name")) # Fetch emails for numeric IDs

                layer["shared_users"] = [
                    f"{user['first_name']} - {user['email']}" for user in shared_users
                ]
            else:
                layer["shared_users"] = []  # Ensure 'shared_users' is always present

        return Response(serialized_data, status=200)

#------------------------------------------------------------------------------
class LayerData_Get_Admin_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_obj = request.user
        org_id = user_obj.org_id

        group_data = LayersModel.objects.filter(
            Q(group_name__contains=["default"]) |
            Q(org_id=org_id)
        )
        serializer = LayerDataSerializer(group_data, many=True)

        serialized_data = serializer.data  # Modify serialized data to include 'shared_users'

        for layer in serialized_data:
            # Get the user_id from the layer
            user_id = layer.get("user_id")

            # Initialize shared_users list
            shared_users_list = []

            # Fetch the owner (user who created the layer) and add to shared_users list
            owner = User.objects.filter(id=user_id).values("email", "first_name").first()
            if owner:
                shared_users_list.append(f"{owner['first_name']} - {owner['email']} - Owner")

            # Get group_name list
            group_name_ids = layer.get("group_name", [])

            if group_name_ids and isinstance(group_name_ids, list):
                # Extract numeric IDs from group_name
                numeric_ids = [int(value) for value in group_name_ids if str(value).isdigit()]

                # Fetch emails and first_names for numeric IDs
                shared_users = list(User.objects.filter(id__in=numeric_ids).values("email", "first_name"))

                # Add shared users to the list
                shared_users_list.extend(
                    [f"{user['first_name']} - {user['email']}" for user in shared_users]
                )

            layer["shared_users"] = shared_users_list  # Assign shared_users list to response

        return Response(serialized_data, status=200)

#------------------------------------------------------------------------------
class LayerData_Get_AdminControlPanel_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_obj = request.user

        if user_obj.user_type not in ['admin', 'super_admin']:
            return Response({"error": "Permission denied. Only admins can access this data."}, status=403)

        org_id = user_obj.org_id

        group_data = LayersModel.objects.filter(
            Q(group_name__contains=["default"]) |
            Q(org_id=org_id)
        )
        serializer = LayerDataSerializer(group_data, many=True)

        serialized_data = serializer.data  # Modify serialized data to include 'shared_users'

        for layer in serialized_data:
            user_id = layer.get("user_id")  # Get owner user_id

            # Fetch owner details (including dep_id)
            owner = User.objects.filter(id=user_id).values("id", "username", "email", "first_name", "last_name", "dep_id").first()

            # Get dep_name for owner (if dep_id exists)
            dep_name = None
            if owner and owner["dep_id"]:
                dep_name = SL_Department_Model.objects.filter(dep_id=owner["dep_id"]).values_list("dep_name", flat=True).first()

            layer["owner"] = {
                "id": owner["id"] if owner else None,
                "username": owner["username"] if owner else None,
                "email": owner["email"] if owner else None,
                "first_name": owner["first_name"] if owner else None,
                "last_name": owner["last_name"] if owner else None,
                "dep_id": owner["dep_id"] if owner else None,
                "dep_name": dep_name if dep_name else "Unknown"
            }

            # Get group_name list
            group_name_ids = layer.get("group_name", [])
            shared_users_list = []

            if isinstance(group_name_ids, list):
                # Extract numeric IDs from group_name
                numeric_ids = [int(value) for value in group_name_ids if str(value).isdigit()]

                # Fetch user details (including dep_id)
                shared_users = list(User.objects.filter(id__in=numeric_ids).values("id", "username", "email", "first_name", "dep_id"))

                # Fetch department names based on dep_id
                dep_ids = {usr["dep_id"] for usr in shared_users if usr["dep_id"]}
                departments = {dep["dep_id"]: dep["dep_name"] for dep in SL_Department_Model.objects.filter(dep_id__in=dep_ids).values("dep_id", "dep_name")}

                # Add dep_name to shared_users list
                for usr in shared_users:
                    usr["dep_name"] = departments.get(usr["dep_id"], "Unknown")  # Assign department name
                    shared_users_list.append(usr)  # Append to shared_users list

            layer["shared_users"] = shared_users_list

        return Response(serialized_data, status=200)

#------------------------------------------------------------------------------
class Layer_Update_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LayersModel.objects.all()
    serializer_class = LayerDataSerializer

    def partial_update(self, request, *args, **kwargs):

        user_obj = self.request.user
        user_id = user_obj.id

        # Set permission ID based on user type
        if user_obj.user_type == "user":
            edit_permission_id = 94
        elif user_obj.user_type in ["admin", "super_admin"]:
            edit_permission_id = 253

        # Check user role
        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            raise PermissionDenied({"error": "User has no assigned roles."})

        role_id = user_roles.values_list("role_id", flat=True).first()

        # Check edit permission
        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=edit_permission_id,
            edit=True
        ).exists()

        if not has_permission:
            raise PermissionDenied({"error": "You do not have permission."})

        # ✅ Check for duplicate before saving
        instance = self.get_object()
        new_layer_name = request.data.get("layer_name")

        if new_layer_name and LayersModel.objects.filter(
            user_id=user_id,
            layer_name=new_layer_name
        ).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError(
                {"error": "Layer name already exists for this user."}
            )

        try:
            with transaction.atomic():  # make sure either all or nothing saves
                return super().partial_update(request, *args, **kwargs)
        except IntegrityError:
            raise serializers.ValidationError(
                {"error": "Layer name already exists for this user."}
            )

#------------------------------------------------------------------------------
class Layer_Delete_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LayersModel.objects.all()
    serializer_class = LayerDataSerializer

    def perform_destroy(self, instance):

        user_obj = self.request.user
        user_id = user_obj.id

        # Set permission_id based on user_type
        if user_obj.user_type == "user":
            delete_permission_id = 94

        elif user_obj.user_type in ["admin", "super_admin"]:
            delete_permission_id = 253

        # Check user role
        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            raise PermissionDenied({"error": "User has no assigned roles."})

        role_id = user_roles.values_list('role_id', flat=True).first()

        # Check delete permission
        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=delete_permission_id,
            delete=True
        ).exists()

        if not has_permission:
            raise PermissionDenied({"error": "You do not have permission."})

        # Delete related geoms
        Survey_Rep_DATA_Model.objects.filter(layer_id=instance.layer_id).delete()

        # Delete the instance itself
        super().perform_destroy(instance)
