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

#________________________________________________ User Roles View _______________________________________________________________
class User_Roles_Create_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = User_Roles_Model.objects.all()
    serializer_class = User_Roles_Create_Serializer

    def get_serializer(self, *args, **kwargs):
        user = self.request.user

        # Ensure the 'admin_id' and 'org_id' are included in the data passed to the serializer
        if 'data' in kwargs:
            kwargs['data'] = {**kwargs['data'], 'admin_id': user.id, 'org_id': user.org_id}

        # Return the serializer with updated data
        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):

        user = self.request.user

        if user.user_type not in ["admin", "super_admin"]:
            raise PermissionDenied("Only Admins can create user roles.")

        user_id = user.id
        add_permission_id = 252

        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response({"error": "User has no assigned roles."}, status=403)

        role_id = user_roles.values_list('role_id', flat=True).first()

        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=add_permission_id,
            add=True
        ).exists()

        if not has_permission:
            raise PermissionDenied({"error": "You do not have permission."})

        new_role = serializer.save()

        # Fetch all permissions
        permissions = Permission_List_Model.objects.all()

        role_permissions = []

        for permission in permissions:
        # Assign permissions depending on "type" and "role_type"
            if permission.type == 1 and new_role.role_type == "admin":
                role_permissions.append(Role_Permission_Model(
                    role_id=new_role,
                    permission_id=permission,
                    view=permission.view,
                    add=permission.add,
                    edit=permission.edit,
                    delete=permission.delete,
                ))
            elif permission.type == 2 and new_role.role_type == "user":
                role_permissions.append(Role_Permission_Model(
                    role_id=new_role,
                    permission_id=permission,
                    view=permission.view,
                    add=permission.add,
                    edit=permission.edit,
                    delete=permission.delete,
                ))
            elif permission.type == 3 and new_role.role_type in ["admin", "user"]:
                role_permissions.append(Role_Permission_Model(
                    role_id=new_role,
                    permission_id=permission,
                    view=permission.view,
                    add=permission.add,
                    edit=permission.edit,
                    delete=permission.delete,
                ))

        # Bulk insert the permissions
        if role_permissions:
            Role_Permission_Model.objects.bulk_create(role_permissions)

#------------------------------------------------------------------------------
class User_Role_update_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = User_Roles_Model.objects.all()
    serializer_class = User_Roles_Serializer

    def update(self, request, *args, **kwargs):

        user = self.request.user

        # Allow only admin or super_admin
        if user.user_type not in ["admin", "super_admin"]:
            raise PermissionDenied("Only Admins can create user roles.")

        user_id = user.id
        edit_permission_id = 252

        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response({"error": "User has no assigned roles."}, status=403)

        role_id = user_roles.values_list('role_id', flat=True).first()

        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=edit_permission_id,
            edit=True
        ).exists()

        if not has_permission:
            raise PermissionDenied({"error": "You do not have permission."})

        # print("Received JSON:", json.dumps(request.data, indent=4))

        instance = self.get_object()
        new_users = request.data.get("users", [])

        # Find users that are already assigned to another role
        existing_roles = User_Roles_Model.objects.exclude(role_id=instance.role_id)
        conflicting_users = set()

        for role in existing_roles:
            if role.users:
                conflicting_users.update(set(role.users) & set(new_users))

        # If there are conflicts, return an error response
        if conflicting_users:
            return Response(
                {"error": f"User(s) {list(conflicting_users)} already assigned"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Check user_type vs role_type ---
        mismatched_users = User.objects.filter(id__in=new_users).exclude(user_type=instance.role_type)

        if mismatched_users.exists():
            return Response(
                {"error": f"User(s) cannot be added to this {instance.role_type} role"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If no conflicts, proceed with the update
        return super().update(request, *args, **kwargs)

#------------------------------------------------------------------------------
class User_Role_delete_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = User_Roles_Model.objects.all()
    serializer_class = User_Roles_Serializer

    def destroy(self, request, *args, **kwargs):

        user = request.user

        # user type check
        if user.user_type not in ["admin", "super_admin"]:
            raise PermissionDenied("Only Admins can delete user roles.")

        user_id = user.id
        delete_permission_id = 252

        # check if user has roles
        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response(
                {"error": "User has no assigned roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        role_id = user_roles.values_list('role_id', flat=True).first()

        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=delete_permission_id,
            delete=True
        ).exists()

        if not has_permission:
            raise PermissionDenied({"error": "You do not have permission."})


        instance = self.get_object()

        if instance.users:  # If users list is not empty or None, prevent deletion
            return Response(
                {"Please remove users before deleting the role."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete related role_permission records
        Role_Permission_Model.objects.filter(role_id=instance).delete()

        instance.delete()

        return Response(
            {"message": "Successful"},
            status=status.HTTP_200_OK
        )

#------------------------------------------------------------------------------
class User_Role_View_filter_admin(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.user_type not in ["admin", "super_admin"]:
            return Response(
                {"error": "Permission denied. Only Admins can access this data."},
                status=403
            )

        if user.user_type == "admin":
            # Admin can see only roles with role_type='user'
            role_data = User_Roles_Model.objects.filter(org_id=user.org_id, role_type="user").order_by('role_type', 'role_name')

        elif user.user_type == 'super_admin':
            # Super admin can see roles with role_type in ['user', 'admin']
            role_data = User_Roles_Model.objects.filter(org_id__in=[user.org_id, 0], role_type__in=["user", "admin"]).order_by('role_type', 'role_name')

        serializer = User_Roles_Admin_Serializer(role_data, many=True)
        return Response(serializer.data, status=200)


#________________________________________________ Role Permission View __________________________________________________________
class Role_Permission_Filter_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        permission_ids = request.data.get('permission_id', [])

        user = request.user
        update_user_last_active(user) # update user last active time

        # Validate inputs
        if not isinstance(permission_ids, list):
            return Response({"error": "permission_id should be a list"}, status=400)

        # Get the roles associated with the user_id
        user_roles = User_Roles_Model.objects.filter(users__contains=[user.id]).values_list('role_id', flat=True)

        if not user_roles:
            return Response({"error": "No roles found for the given user_id"}, status=404)

        # Filter by both permission_id and role_id
        permission_list = Role_Permission_Model.objects.filter(permission_id__in=permission_ids, role_id__in=user_roles)
        serializer = Role_permission_Get_Serializer(permission_list, many=True)

        return Response(serializer.data)

#------------------------------------------------------------------------------
class Role_Permission_LayerPanel_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        permission_ids = [80,81,82,83,84,85,86,87,88,89,90,92]

        user_id = request.user.id # Get user_id by token

        # Get the roles associated with the user_id
        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id]).values_list('role_id', flat=True)

        if not user_roles:
            return Response({"error": "No roles found for the given user_id"}, status=404)

        # Filter by both permission_id and role_id
        permission_list = Role_Permission_Model.objects.filter(permission_id__in=permission_ids, role_id__in=user_roles)
        serializer = Role_permission_Get_LayerPanel_Serializer(permission_list, many=True)

        return Response(serializer.data)

#------------------------------------------------------------------------------
class Role_Permission_All_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, role_id):

        role_data = Role_Permission_Model.objects.filter(
            role_id=role_id, permission_id__status=True
            ).select_related('permission_id').order_by('permission_id__category', 'permission_id__sub_category')

        serializer = Role_permission_Get_Serializer(role_data, many=True)

        return Response(serializer.data, status=200)

#------------------------------------------------------------------------------
class Role_Permission_Update_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Role_Permission_Model.objects.all()
    serializer_class = Role_permission_Update_Serializer

    def update(self, request, *args, **kwargs):
        user = request.user

        # Allow only admin or super_admin
        if user.user_type not in ["admin", "super_admin"]:
            raise PermissionDenied("Only Admins can create user roles.")


        user_id = user.id
        edit_permission_id = 252

        # check user has roles
        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response(
                {"error": "User has no assigned roles."},
                status=status.HTTP_403_FORBIDDEN
            )

        role_id = user_roles.values_list('role_id', flat=True).first()

        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=edit_permission_id,
            edit=True
        ).exists()

        if not has_permission:
            raise PermissionDenied("You do not have permission.")

        # if passes checks → call default update
        return super().update(request, *args, **kwargs)
