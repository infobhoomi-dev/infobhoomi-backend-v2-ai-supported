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

#________________________________________________ Register User _________________________________________________________________
class RegisterView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            token, _created = Token.objects.get_or_create(user=user)
            return Response({
                'token': str(token.key),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#________________________________________________ Create User ___________________________________________________________________
class CreateUserView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        create_user = request.user

        if create_user.user_type not in ['admin', 'super_admin']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        org_id = create_user.org_id

        # ✅ Get user count under same organization (excluding admin)
        current_user_count = User.objects.filter(org_id=org_id).exclude(user_type__in=['admin', 'super_admin']).count()

        # ✅ Get organization user limit
        org = SL_Organization_Model.objects.get(org_id=org_id)
        user_limit = org.users_limit

        # ✅ If limit is reached, block account creation
        if user_limit is not None and current_user_count >= user_limit:
            return Response(
                {'error': f'User account limit reached for this organization. Limit: {user_limit}'},
                status=status.HTTP_403_FORBIDDEN
            )

        # ✅ Force user_type based on who creates
        if create_user.user_type == "admin":
            forced_user_type = "user"
            default_password = "user@user123"

        elif create_user.user_type == "super_admin":
            forced_user_type = "admin"
            default_password = "admin@admin123"

        # ✅ Proceed to create user
        serializer = UserSerializer(data=request.data, context={'org_id': org_id})

        if serializer.is_valid():
            user = serializer.save()

            # ✅ set forced user_type
            user.user_type = forced_user_type
            # ✅ set default password
            user.set_password(default_password)

            user.save(update_fields=["user_type", "password"])

            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#________________________________________________ Update User ___________________________________________________________________
class UpdateUserView(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = User.objects.all()
    serializer_class = Update_User_Serializer

    def update(self, request, *args, **kwargs):
        # Use the authenticated user as done_by
        done_by = request.user.id

        # Get the user instance to update
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        # Remove password if present
        if 'password' in validated_data:
            validated_data.pop('password')

        # Track changes and log to history table
        for field_name, new_value in validated_data.items():

            if field_name == "org_id":
                continue  # Skip org_id field

            old_value = getattr(instance, field_name, None)
            if old_value != new_value:
                History_User_Attrib_Model.objects.create(
                    done_by=done_by,
                    user_id=instance.id,
                    field_name=field_name,
                    field_value=f"Updated from '{old_value}' to '{new_value}'"
                )

        # Save the updated user
        serializer.save()

        return Response({"details": "successfully updated."}, status=status.HTTP_200_OK)

#________________________________________________ User Details __________________________________________________________________
class UserDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # get department name
        department_name = None
        try:
            department = SL_Department_Model.objects.get(dep_id=user.dep_id, org_id=user.org_id)
            department_name = department.dep_name
        except SL_Department_Model.DoesNotExist:
            department_name = None

        # Override rule: If super admin, department must be "IT"
        if user.user_type == "super_admin":
            department_name = "IT Department"

        user_details = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,

            'first_name': user.first_name,
            'last_name': user.last_name,
            'mobile': user.mobile,
            'address': user.address,

            'nic': user.nic,
            'birthday': user.birthday,
            'sex': user.sex,

            'org_id': user.org_id,
            'department_id': user.dep_id,
            'department': department_name,
            'post': user.post,
            'emp_id': user.emp_id,

            # 'is_superuser': user.is_superuser,
            # 'is_staff': user.is_staff,
            'is_active': user.is_active,
            'user_type': user.user_type,
        }
        return Response(user_details)

#________________________________________________ CHANGE PASSWORD View __________________________________________________________
class ChangePasswordView(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data.get('old_password')
            new_password = serializer.validated_data.get('new_password')
            confirm_new_password = serializer.validated_data.get('confirm_new_password')

            if not user.check_password(old_password):
                return Response({'error': 'Old password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

            if new_password != confirm_new_password:
                return Response({'error': 'New password and confirm new password do not match.'}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#________________________________________________ RESET PASSWORD View ___________________________________________________________
class ResetPasswordView(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Retrieve the admin and user IDs from the request
            data = json.loads(request.body)
            admin_id = data.get('admin_id')
            user_id = data.get('user_id')

            admin_user = get_object_or_404(User, id=admin_id)
            if admin_user.user_type not in ['admin', 'super_admin']:
                return Response({'error': 'Permission denied. Only admins can reset passwords.'}, status=status.HTTP_403_FORBIDDEN)

            user = get_object_or_404(User, id=user_id)

            if user.user_type == 'admin':
                new_password = "admin@admin123"

            if user.user_type == 'user':
                new_password = "user@user123"

            user.set_password(new_password)
            user.save()

            return Response({'message': f'Password reset successfully for user {user.username}.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

#________________________________________________ PASSWORD Check View ___________________________________________________________
class PasswordCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserPasswordCheckSerializer(data=request.data)

        if serializer.is_valid():
            password = serializer.validated_data['password']
            user = request.user  # Retrieves the user from the token

            if check_password(password, user.password):
                return Response({"message": "Password is correct."}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Incorrect password."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#________________________________________________ Login View ____________________________________________________________________
class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        login_identifier = request.data.get('username')
        password = request.data.get('password')

        user = User.objects.filter(Q(username=login_identifier) | Q(email=login_identifier)).first()

        if user and user.check_password(password) and user.is_active:

            # ✅ Check if organization is active
            if user.user_type != "super_admin":
                org = SL_Organization_Model.objects.filter(org_id=user.org_id, status=True).first()
                if not org:
                    return Response(
                        {"error": "Your organization is not active. Please contact Super Admin."},
                        status=status.HTTP_403_FORBIDDEN
                    )

            # Get user's role_id
            role_id = User_Roles_Model.objects.filter(users__contains=[user.id]).values_list('role_id', flat=True).first()
            if not role_id:
                return Response(
                    {"error": "You are not assigned to a user role. Please contact Admin."},
                    status=status.HTTP_403_FORBIDDEN
                )

            Token.objects.filter(user=user).delete()  # Delete existing token if any
            token = Token.objects.create(user=user)   # Create a new one

            user.last_login = now()
            user.save(update_fields=['last_login'])

            # Build custom data dict with injected role_id
            user_data = UserLoginSerializer({
                'id': user.id,
                'org_id': user.org_id,
                'user_type': user.user_type,
                'emp_id': user.emp_id,
                'role_id': role_id
            }).data

            return Response({
                'token': str(token.key),
                'user': user_data
            })

        return Response({'error': 'Invalid credentials or login expired'}, status=status.HTTP_401_UNAUTHORIZED)

#________________________________________________ Logout View ___________________________________________________________________
class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        token = request.auth
        if token:
            token.delete()
            return Response({'detail': 'Successfully logged out'}, status=status.HTTP_200_OK)
        return Response({'detail': 'No token to delete'}, status=status.HTTP_400_BAD_REQUEST)

#________________________________________________ Verify Token __________________________________________________________________
class VerifyTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Token '):
            return Response({'is_token_valid': False}, status=status.HTTP_400_BAD_REQUEST)

        token = auth_header.split(' ')[1]
        try:
            Token.objects.get(key=token)
            return Response({'is_token_valid': True}, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({'is_token_valid': False}, status=status.HTTP_401_UNAUTHORIZED)

#________________________________________________ Verify User Auth Login ________________________________________________________
class Verify_User_Auth_Login_View(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        auth_header = request.headers.get("Authorization", "")
        role_id = request.data.get("role_id")

        result = verify_token_and_role(auth_header, role_id)
        if not result:
            return Response({"is_token_valid": False}, status=status.HTTP_401_UNAUTHORIZED)

        user = result["user"]


         # ⭐ If super admin → skip all checks and return success
        if user.user_type == "super_admin":
            update_user_last_active(user)
            return Response({
                "is_token_valid": True,
                "is_active": True,
                "is_role_id": True,
                "is_org_active": True,
            }, status=status.HTTP_200_OK)

        # ---------------- Normal User Flow ----------------

        # 1. Check organization first
        org_status = False
        try:
            org = SL_Organization_Model.objects.get(org_id=user.org_id)
            if org.permit_end_date and org.permit_end_date < timezone.now().date():
                org.status = False
                org.save(update_fields=["status"])
            org_status = org.status
        except SL_Organization_Model.DoesNotExist:
            pass

        # If org inactive → force user inactive
        is_active = result["is_active"] if org_status else False

        # 2. If user inactive → forbidden
        if not is_active:
            return Response({
                "is_token_valid": True,
                "is_active": False,
                "is_role_id": result["is_role_id"],
                "is_org_active": org_status,
            }, status=status.HTTP_403_FORBIDDEN)

        # 3. If role not matched → forbidden
        if not result["is_role_id"]:
            return Response({
                "is_token_valid": True,
                "is_active": True,
                "is_role_id": False,
                "is_org_active": org_status,
            }, status=status.HTTP_403_FORBIDDEN)

        # ✅ If all pass → update last active
        update_user_last_active(user)

        return Response({
            "is_token_valid": True,
            "is_active": True,
            "is_role_id": True,
            "is_org_active": org_status,
        }, status=status.HTTP_200_OK)
