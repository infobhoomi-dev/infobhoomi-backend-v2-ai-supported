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

#________________________________________________ User List - Admin Panel _______________________________________________________
class GetUserAccountsView(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Allow only admin and super_admin
        if user.user_type not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Permission denied. Only admins can access this data.'},
                status=status.HTTP_403_FORBIDDEN
            )

        org_id = user.org_id

        # Subquery annotations eliminate N+1 for department name and last_active per user
        dep_name_sq = Subquery(SL_Department_Model.objects.filter(dep_id=OuterRef('dep_id')).values('dep_name')[:1])
        last_active_sq = Subquery(Last_Active_Model.objects.filter(user_id=OuterRef('id')).values('active_time')[:1])

        if user.user_type == 'admin':
            # Admin can see only 'user' accounts
            users = User.objects.filter(org_id=org_id, user_type='user').order_by('dep_id', 'first_name')

        elif user.user_type == 'super_admin':
            # Super admin can see both 'admin' and 'user' accounts
            users = User.objects.filter(org_id=org_id, user_type__in=['admin', 'user']).order_by('user_type', 'dep_id', 'first_name')

        users = users.annotate(dep_name_annotated=dep_name_sq, last_active_annotated=last_active_sq)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

#________________________________________________ User List (Add users to User Roles) - Admin Panel _____________________________
class GetUserAccounts_Add_UserRoles_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.user_type not in ['admin', 'super_admin']:
            return Response({'error': 'Permission denied. Only admins can access this data.'}, status=status.HTTP_403_FORBIDDEN)

        orgID = user.org_id

        # Get all user IDs from the User_Roles_Model for this organization
        role_user_ids = User_Roles_Model.objects.filter(org_id__in=[orgID, 0]).values_list('users', flat=True)

        # Flatten the list
        role_user_ids = [user_id for sublist in role_user_ids if sublist for user_id in sublist]

        # Get users NOT in the role_user_ids list
        dep_name_sq = Subquery(SL_Department_Model.objects.filter(dep_id=OuterRef('dep_id')).values('dep_name')[:1])
        users_not_in_roles = (
            User.objects.filter(org_id=orgID, user_type__in=['user', 'admin'])
            .exclude(id__in=role_user_ids)
            .annotate(dep_name_annotated=dep_name_sq)
        )

        serializer = UserSerializer_Add_UserRoles(users_not_in_roles, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

#________________________________________________ Recent Users - Admin Panel ____________________________________________________
class Recent_Users_Login_View(ListAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = Recent_Users_Login_Serializer

    def get_queryset(self):
        user = self.request.user
        dep_name_sq = Subquery(SL_Department_Model.objects.filter(dep_id=OuterRef('dep_id')).values('dep_name')[:1])

        if user.user_type == "super_admin":
            return User.objects.filter(
                user_type__in=["admin", "user"], last_login__isnull=False, org_id=user.org_id
            ).order_by("-last_login")[:5].annotate(dep_name_annotated=dep_name_sq)

        elif user.user_type == "admin":
            return User.objects.filter(
                user_type="user", last_login__isnull=False, org_id=user.org_id
            ).order_by("-last_login")[:5].annotate(dep_name_annotated=dep_name_sq)

        return User.objects.none()

    def list(self, request, *args, **kwargs):
        if request.user.user_type not in ["super_admin", "admin"]:
            return Response({"error": "Permission denied."}, status=403)
        return super().list(request, *args, **kwargs)

#________________________________________________ User OverView - Admin Panel ___________________________________________________
class User_Over_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org_id = request.user.org_id  # Get org_id from the authenticated user

        if request.user.user_type == "super_admin":
            user_qs = User.objects.filter(user_type__in=["admin", "user"], org_id=org_id)
        elif request.user.user_type == "admin":
            user_qs = User.objects.filter(user_type="user", org_id=org_id)
        else:
            return Response({"error": "Permission denied."}, status=403)

        user_ids = user_qs.values_list('id', flat=True)

        total_users = user_qs.count()
        active_users = user_qs.filter(is_active=True).count()
        inactive_users = user_qs.filter(is_active=False).count()

        # Time limit for "online users"
        time_threshold = timezone.now() - timedelta(minutes=3)

        # Online user IDs from Last_Active_Model
        online_user_ids = Last_Active_Model.objects.filter(
            user_id__in=user_ids,
            active_time__gte=time_threshold
        ).values_list("user_id", flat=True)

        # Fetch user details
        online_users = User.objects.filter(id__in=online_user_ids).values(
            "username",
            "first_name",
            "last_name",
            "email",
            "user_type"
        ).order_by('user_type', 'first_name')

        return Response({
            "registered": total_users,
            "active": active_users,
            "suspended": inactive_users,
            "online": len(online_users),
            "online_users": list(online_users)
        })

#________________________________________________ Online User Acc update ________________________________________________________
class UserAccounts_online_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        update_user_last_active(user)

        return Response("Successful", status=status.HTTP_200_OK)

#________________________________________________ Admin Acc View (Contact Admin) ________________________________________________
class Admin_Acc_Data_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the authenticated user
        user = request.user

        # Extract org_id
        org_id = user.org_id

        # Query admin accounts in same org
        admins = User.objects.filter(org_id=org_id, user_type='admin')

        serializer = Admin_Acc_Data_Serializer(admins, many=True)
        return Response(serializer.data)


#________________________________________________ Secure Media View______________________________________________________________
class DownloadAdminSourcePDF(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, admin_source_id):
        try:
            admin_source = LA_Admin_Source_Model.objects.get(admin_source_id=admin_source_id)

            if not admin_source.file_path:
                raise Http404("File not found")

            file = admin_source.file_path.open("rb")
            return FileResponse(file, content_type='application/pdf')

        except LA_Admin_Source_Model.DoesNotExist:
            raise Http404("Source ID not found")


#________________________________________________ Admin Source Update View _______________________________________________________________
class AdminSourceUpdateView(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, admin_source_id):
        try:
            admin_source = LA_Admin_Source_Model.objects.get(admin_source_id=admin_source_id)
        except LA_Admin_Source_Model.DoesNotExist:
            return Response({"error": "Admin source not found."}, status=status.HTTP_404_NOT_FOUND)

        # Update type if provided
        new_type = request.data.get('admin_source_type')
        if new_type:
            admin_source.admin_source_type = new_type

        # Replace file if provided
        new_file = request.FILES.get('file')
        if new_file:
            folder_path = 'documents/admin_source'
            new_filename = f"{admin_source_id}.pdf"
            full_path = os.path.join(folder_path, new_filename)

            # Delete existing file before overwriting
            if admin_source.file_path and default_storage.exists(admin_source.file_path.name):
                default_storage.delete(admin_source.file_path.name)

            saved_path = default_storage.save(full_path, ContentFile(new_file.read()))
            admin_source.file_path.name = saved_path

        admin_source.save()

        return Response({
            "admin_source_id": admin_source.admin_source_id,
            "admin_source_type": admin_source.admin_source_type,
            "file_saved_as": admin_source.file_path.name if admin_source.file_path else None,
        }, status=status.HTTP_200_OK)
