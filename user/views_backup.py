from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView, RetrieveUpdateAPIView

from .models import *
from .serializers import *
from .constant import *

from .tests import *

from rest_framework import status
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate

import json
from django.db.models import Q

from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Min

from django.utils.timezone import now
from django.utils import timezone
from datetime import timedelta

import os
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings

from rest_framework import generics, status
from django.db.models import Subquery, OuterRef
from django.core.exceptions import PermissionDenied 

from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.functions import Area, Intersection as GeoIntersection

from django.db import IntegrityError, transaction

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile



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

        if user.user_type == 'admin':
            # Admin can see only 'user' accounts
            users = User.objects.filter(org_id=org_id, user_type='user').order_by('dep_id', 'first_name')

        elif user.user_type == 'super_admin':
            # Super admin can see both 'admin' and 'user' accounts
            users = User.objects.filter(org_id=org_id, user_type__in=['admin', 'user']).order_by('user_type', 'dep_id', 'first_name')

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
        users_not_in_roles = User.objects.filter(org_id=orgID, user_type__in=['user', 'admin']).exclude(id__in=role_user_ids)

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

        if user.user_type == "super_admin":
            return User.objects.filter(
                user_type__in=["admin", "user"], last_login__isnull=False, org_id=user.org_id
            ).order_by("-last_login")[:5]

        elif user.user_type == "admin":
            return User.objects.filter(
                user_type="user", last_login__isnull=False, org_id=user.org_id
            ).order_by("-last_login")[:5]

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


#================================================ LIST ====================================================================================

#________________________________________________ Lst_SL_Party_Type_1 View ______________________________________________________
class Lst_SL_Party_Type_1_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_Party_Type_1_Model.objects.all().order_by('id')
    serializer_class = Lst_SL_Party_Type_1_Serializer
#________________________________________________ Lst_SL_PartyRoleType_2 View ___________________________________________________
class Lst_SL_PartyRoleType_2_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_PartyRoleType_2_Model.objects.all()
    serializer_class = Lst_SL_PartyRoleType_2_Serializer
#________________________________________________ Lst_SL_Education_Level_3 View _________________________________________________
class Lst_SL_Education_Level_3_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_Education_Level_3_Model.objects.all()
    serializer_class = Lst_SL_Education_Level_3_Serializer
#________________________________________________ Lst_SL_Race_4 View ____________________________________________________________
class Lst_SL_Race_4_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_Race_4_Model.objects.all()
    serializer_class = Lst_SL_Race_4_Serializer
#________________________________________________ Lst_SL_HealthStatus_5 View ____________________________________________________
class Lst_SL_HealthStatus_5_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_HealthStatus_5_Model.objects.all()
    serializer_class = Lst_SL_HealthStatus_5_Serializer
#________________________________________________ Lst_SL_MarriedStatus_6 View ___________________________________________________
class Lst_SL_MarriedStatus_6_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_MarriedStatus_6_Model.objects.all()
    serializer_class = Lst_SL_MarriedStatus_6_Serializer
#________________________________________________ Lst_SL_Religions_7 View _______________________________________________________
class Lst_SL_Religions_7_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_Religions_7_Model.objects.all()
    serializer_class = Lst_SL_Religions_7_Serializer
#________________________________________________ Lst_SL_GenderType_8 View ______________________________________________________
class Lst_SL_GenderType_8_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_GenderType_8_Model.objects.all()
    serializer_class = Lst_SL_GenderType_8_Serializer
#________________________________________________ Lst_SL_RightType_9 View _______________________________________________________
class Lst_SL_RightType_9_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_RightType_9_Model.objects.all()
    serializer_class = Lst_SL_RightType_9_Serializer
#________________________________________________ Lst_SL_BAUnitType_10 View _____________________________________________________
class Lst_SL_BAUnitType_10_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_BAUnitType_10_Model.objects.all()
    serializer_class = Lst_SL_BAUnitType_10_Serializer
#________________________________________________ Lst_SL_AdminRestrictionType_11 View ___________________________________________
class Lst_SL_AdminRestrictionType_11_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_AdminRestrictionType_11_Model.objects.all()
    serializer_class = Lst_SL_AdminRestrictionType_11_Serializer
#________________________________________________ Lst_SL_AnnotationType_12 View _________________________________________________
class Lst_SL_AnnotationType_12_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_AnnotationType_12_Model.objects.all()
    serializer_class = Lst_SL_AnnotationType_12_Serializer
#________________________________________________ Lst_Sl_MortgageType_13 View ___________________________________________________
class Lst_Sl_MortgageType_13_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_Sl_MortgageType_13_Model.objects.all()
    serializer_class = Lst_Sl_MortgageType_13_Serializer
#________________________________________________ Lst_SL_RightShareType_14 View _________________________________________________
class Lst_SL_RightShareType_14_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_RightShareType_14_Model.objects.all()
    serializer_class = Lst_SL_RightShareType_14_Serializer
#________________________________________________ Lst_SL_AdministrativeStatausType_15 View ______________________________________
class Lst_SL_AdministrativeStatausType_15_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_AdministrativeStatausType_15_Model.objects.all()
    serializer_class = Lst_SL_AdministrativeStatausType_15_Serializer
#________________________________________________ Lst_SL_AdministrativeSourceType_16 View _______________________________________
class Lst_SL_AdministrativeSourceType_16_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_AdministrativeSourceType_16_Model.objects.all()
    serializer_class = Lst_SL_AdministrativeSourceType_16_Serializer
#________________________________________________ Lst_SL_ResponsibilityType_17 View _____________________________________________
class Lst_SL_ResponsibilityType_17_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_ResponsibilityType_17_Model.objects.all()
    serializer_class = Lst_SL_ResponsibilityType_17_Serializer
#________________________________________________ Lst_LA_BAUnitType_18 View _____________________________________________________
class Lst_LA_BAUnitType_18_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_LA_BAUnitType_18_Model.objects.all()
    serializer_class = Lst_LA_BAUnitType_18_Serializer
#________________________________________________ Lst_SU_SL_LevelContentType_19 View ____________________________________________
class Lst_SU_SL_LevelContentType_19_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SU_SL_LevelContentType_19_Model.objects.all()
    serializer_class = Lst_SU_SL_LevelContentType_19_Serializer
#________________________________________________ Lst_SU_SL_RegesterType_20 View ________________________________________________
class Lst_SU_SL_RegesterType_20_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SU_SL_RegesterType_20_Model.objects.all()
    serializer_class = Lst_SU_SL_RegesterType_20_Serializer
#________________________________________________ Lst_SU_SL_StructureType_21 View _______________________________________________
class Lst_SU_SL_StructureType_21_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SU_SL_StructureType_21_Model.objects.all()
    serializer_class = Lst_SU_SL_StructureType_21_Serializer
#________________________________________________ Lst_SU_SL_Water_22 View _______________________________________________________
class Lst_SU_SL_Water_22_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SU_SL_Water_22_Model.objects.all()
    serializer_class = Lst_SU_SL_Water_22_Serializer
#________________________________________________ Lst_SU_SL_Sanitation_23 View __________________________________________________
class Lst_SU_SL_Sanitation_23_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SU_SL_Sanitation_23_Model.objects.all()
    serializer_class = Lst_SU_SL_Sanitation_23_Serializer
#________________________________________________ Lst_SU_SL_Roof_Type_24 View ___________________________________________________
class Lst_SU_SL_Roof_Type_24_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SU_SL_Roof_Type_24_Model.objects.all()
    serializer_class = Lst_SU_SL_Roof_Type_24_Serializer
#________________________________________________ Lst_SU_SL_Wall_Type_25 View ___________________________________________________
class Lst_SU_SL_Wall_Type_25_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SU_SL_Wall_Type_25_Model.objects.all()
    serializer_class = Lst_SU_SL_Wall_Type_25_Serializer
#________________________________________________ Lst_SU_SL_Floor_Type_26 View __________________________________________________
class Lst_SU_SL_Floor_Type_26_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SU_SL_Floor_Type_26_Model.objects.all()
    serializer_class = Lst_SU_SL_Floor_Type_26_Serializer
#________________________________________________ Lst_SR_SL_SpatialSourceTypes_27 View __________________________________________
class Lst_SR_SL_SpatialSourceTypes_27_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SR_SL_SpatialSourceTypes_27_Model.objects.all()
    serializer_class = Lst_SR_SL_SpatialSourceTypes_27_Serializer
#________________________________________________ Lst_EC_ExtLandUseType_28 View _________________________________________________
class Lst_EC_ExtLandUseType_28_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtLandUseType_28_Model.objects.all()
    serializer_class = Lst_EC_ExtLandUseType_28_Serializer
#________________________________________________ Lst_EC_ExtLandUseSubType_29 View ______________________________________________
class Lst_EC_ExtLandUseSubType_29_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtLandUseSubType_29_Model.objects.all()
    serializer_class = Lst_EC_ExtLandUseSubType_29_Serializer
#________________________________________________ Lst_EC_ExtOuterLegalSpaceUseType_30 View ______________________________________
class Lst_EC_ExtOuterLegalSpaceUseType_30_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtOuterLegalSpaceUseType_30_Model.objects.all()
    serializer_class = Lst_EC_ExtOuterLegalSpaceUseType_30_Serializer
#________________________________________________ Lst_EC_ExtOuterLegalSpaceUseSubType_31 View ___________________________________
class Lst_EC_ExtOuterLegalSpaceUseSubType_31_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtOuterLegalSpaceUseSubType_31_Model.objects.all()
    serializer_class = Lst_EC_ExtOuterLegalSpaceUseSubType_31_Serializer
#________________________________________________ Lst_EC_ExtBuildUseType_32 View ________________________________________________
class Lst_EC_ExtBuildUseType_32_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtBuildUseType_32_Model.objects.all()
    serializer_class = Lst_EC_ExtBuildUseType_32_Serializer
#________________________________________________ Lst_EC_ExtBuildUseSubType_33 View _____________________________________________
class Lst_EC_ExtBuildUseSubType_33_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtBuildUseSubType_33_Model.objects.all()
    serializer_class = Lst_EC_ExtBuildUseSubType_33_Serializer
#________________________________________________ Lst_EC_ExtDivisionType_34 View ________________________________________________
class Lst_EC_ExtDivisionType_34_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtDivisionType_34_Model.objects.all()
    serializer_class = Lst_EC_ExtDivisionType_34_Serializer
#________________________________________________ Lst_EC_ExtFeatureMainType_35 View _____________________________________________
class Lst_EC_ExtFeatureMainType_35_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtFeatureMainType_35_Model.objects.all()
    serializer_class = Lst_EC_ExtFeatureMainType_35_Serializer
#________________________________________________ Lst_EC_ExtFeatureMainType_36 View _____________________________________________
class Lst_EC_ExtFeatureMainType_36_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtFeatureMainType_36_Model.objects.all()
    serializer_class = Lst_EC_ExtFeatureMainType_36_Serializer
#________________________________________________ Lst_EC_ExtFeatureMainType_37 View _____________________________________________
class Lst_EC_ExtFeatureMainType_37_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_EC_ExtFeatureMainType_37_Model.objects.all()
    serializer_class = Lst_EC_ExtFeatureMainType_37_Serializer
#________________________________________________ Lst_Telecom_Providers_38 View _________________________________________________
class Lst_Tele_Providers_38_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_Tele_Providers_38_Model.objects.all()
    serializer_class = Lst_Tele_Providers_38_Serializer
#________________________________________________ Lst_Internet_Providers_39 View ________________________________________________
class Lst_Int_Providers_39_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_Int_Providers_39_Model.objects.all()
    serializer_class = Lst_Int_Providers_39_Serializer
#________________________________________________ Lst_Organization_Names_40 View ________________________________________________
class Lst_Org_Names_40_View(ListCreateAPIView):
    http_method_names = ['post', 'get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_Org_Names_40_Model.objects.all()
    serializer_class = Lst_Org_Names_40_Serializer
#________________________________________________ Lst_SL_Group_Party_Type_41 View _______________________________________________
class Lst_SL_Group_Party_Type_41_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Lst_SL_Group_Party_Type_41_Model.objects.all()
    serializer_class = Lst_SL_Group_Party_Type_41_Serializer


#________________________________________________ Lst_gnd View (for Admin Info drop down) _______________________________________
class Lst_gnd_10m_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:
            user = request.user

            orgID = user.org_id

            gnd_ids_from_org = Org_Area_Model.objects.filter(org_id=orgID).values_list('org_area', flat=True)
            gnd_ids = [gnd_id for sublist in gnd_ids_from_org for gnd_id in sublist]

            list_data = sl_gnd_10m_Model.objects.filter(gid__in=gnd_ids).values('gid', 'gnd')

            return Response(list(list_data))

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#==========================================================================================================================================



#________________________________________________ TESTING _______________________________________________________________________

class TestJsonView(ListCreateAPIView):
    
    queryset = TestJsonModel.objects.all()
    serializer_class = TestJsonSerializer
    pagination_class = PageNumberPagination


class Test_Data_MyLayerIDs_View(APIView):
    http_method_names = ['post']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        # Retrieve username from request data
        userID = request.data.get("user_id")
        if not userID:
            return Response({"detail": "user_id is required."}, status=400)

        # Filter LayersModel to get relevant layer_ids
        my_layerIDs = LayersModel.objects.filter(group_name__contains=[userID]).values_list('layer_id', flat=True)
       
        return Response(my_layerIDs, status=200)


class Temp_Import_View(ListCreateAPIView):
    http_method_names = ['get']
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = Temp_Import_Model.objects.filter(layer_id=1)
    serializer_class = Temp_Import_Serializer


#________________________________________________ CityJson View _________________________________________________________________
class CityJSON_Model_ListCreate(generics.ListCreateAPIView):
    queryset = CityJSON_Model.objects.all()
    serializer_class = CityJSON_Serializer

#------------------------------------------------------------------------------
class CityJSON_Model_Retrieve(generics.RetrieveAPIView):
    queryset = CityJSON_Model.objects.all()
    serializer_class = CityJSON_Serializer

#------------------------------------------------------------------------------
class CityJSON_Upload(generics.CreateAPIView):
    serializer_class = CityJSON_Serializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Extract CityObjects after saving the CityJSONModel
        city_objects_count = self.extract_city_objects(serializer.instance.cityjson_data)

        return Response({
            "message": "CityJSON data uploaded successfully",
            "cityjson_id": serializer.instance.id,
            "city_objects_count": city_objects_count
        }, status=status.HTTP_201_CREATED)

    def extract_city_objects(self, cityjson_data):
        try:
            city_objects = cityjson_data.get('CityObjects', {})
            bulk_objects = []

            for city_object_id, data in city_objects.items():
                bulk_objects.append(City_Object_Model(
                    city_object_id=city_object_id,
                    type=data.get('type'),
                    attributes=data.get('attributes'),
                    parents=data.get('parents'),
                    children=data.get('children'),
                    geometry=data.get('geometry'),
                ))

            # Bulk insert to optimize performance
            with transaction.atomic():
                City_Object_Model.objects.bulk_create(bulk_objects, ignore_conflicts=True)

            return len(bulk_objects)

        except Exception as e:
            print(f"Error extracting CityObjects: {e}")
            return 0  # Return 0 if extraction fails

#------------------------------------------------------------------------------
class City_Object_List(generics.ListAPIView):
    queryset = City_Object_Model.objects.all()
    serializer_class = City_Object_Serializer

#------------------------------------------------------------------------------
class City_Object_Retrieve(generics.RetrieveAPIView):
    queryset = City_Object_Model.objects.all()
    serializer_class = City_Object_Serializer

#------------------------------------------------------------------------------
# from rest_framework.parsers import MultiPartParser
# import tempfile
# import ifcopenshell
# import ifcopenshell.geom


# class IFCtoCityJSONView(APIView):
#     parser_classes = [MultiPartParser]

#     def post(self, request):

#         # 1️⃣ Get IFC file
#         ifc_file = request.FILES.get("file")
#         if not ifc_file:
#             return Response({"error": "No IFC file provided"}, status=400)

#         # 2️⃣ Save IFC temporarily
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
#             for chunk in ifc_file.chunks():
#                 tmp.write(chunk)
#             tmp_path = tmp.name

#         try:
#             # 3️⃣ Open IFC
#             ifc = ifcopenshell.open(tmp_path)

#             # 4️⃣ Geometry settings
#             settings = ifcopenshell.geom.settings()
#             settings.set(settings.USE_WORLD_COORDS, True)
#             settings.set(settings.DISABLE_OPENING_SUBTRACTIONS, True)

#             # 5️⃣ List of IFC element types to include
#             element_types = ["IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow"]

#             city_vertices = []
#             vertex_map = {}
#             city_objects = {}

#             for elem_type in element_types:
#                 elements = ifc.by_type(elem_type)
#                 for elem in elements:
#                     try:
#                         shape = ifcopenshell.geom.create_shape(settings, elem)
#                     except RuntimeError:
#                         # Skip elements with no geometry
#                         continue

#                     verts = shape.geometry.verts
#                     faces = shape.geometry.faces

#                     boundaries = []
#                     for i in range(0, len(faces), 3):
#                         ring = []
#                         for idx in faces[i:i+3]:
#                             v = (verts[idx*3], verts[idx*3+1], verts[idx*3+2])
#                             key = (round(v[0],5), round(v[1],5), round(v[2],5))
#                             if key not in vertex_map:
#                                 vertex_map[key] = len(city_vertices)
#                                 city_vertices.append(list(key))
#                             ring.append(vertex_map[key])
#                         boundaries.append([ring])

#                     city_objects[elem.GlobalId] = {
#                         "type": "Building",
#                         "attributes": {
#                             "ifc_type": elem_type,
#                             "name": getattr(elem, "Name", "")
#                         },
#                         "geometry": [
#                             {
#                                 "type": "MultiSurface",
#                                 "lod": "2",
#                                 "boundaries": boundaries
#                             }
#                         ]
#                     }

#             # 8️⃣ Build final CityJSON
#             cityjson = {
#                 "type": "CityJSON",
#                 "version": "1.1",
#                 "CityObjects": city_objects,
#                 "vertices": city_vertices
#             }

#             return Response(cityjson)

#         finally:
#             # 9️⃣ Cleanup temp file
#             if os.path.exists(tmp_path):
#                 os.remove(tmp_path)










#________________________________________________ sl_gnd_10m View _______________________________________________________________
class GND_All_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = sl_gnd_10m_Model.objects.all()
    serializer_class = sl_gnd_10m_Attrb_Serializer

#------------------------------------------------------------------------------
class PD_List_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pd_values = sl_gnd_10m_Model.objects.values_list('pd', flat=True).distinct()
        return Response({"pd_list": pd_values})

#------------------------------------------------------------------------------
class PD_Data_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pd_name):
        queryset = sl_gnd_10m_Model.objects.filter(pd=pd_name)
        if not queryset.exists():
            return Response({"error": "No data found for this PD"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = sl_gnd_10m_Attrb_Serializer(queryset, many=True)
        return Response(serializer.data)

#------------------------------------------------------------------------------
class Dist_List_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dist_values = sl_gnd_10m_Model.objects.values_list('dist', flat=True).distinct().order_by('dist')
        return Response(dist_values)


#________________________________________________ SL_Organization View __________________________________________________________
class SL_Organization_View(ListCreateAPIView):
    http_method_names = ['get', 'post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = SL_Organization_Model.objects.all()
    serializer_class = SL_Organization_Serializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type != "super_admin":
            raise PermissionDenied({"error":"Only super admin can update organization details."})
        
        # Get the super_admin's own organization
        own_org = SL_Organization_Model.objects.filter(org_id=user.org_id)

        # Get the rest of the organizations
        other_orgs = SL_Organization_Model.objects.exclude(org_id=user.org_id).order_by('display_name')

        # Combine: own organization first, then others
        return list(own_org) + list(other_orgs)

    def perform_create(self, serializer):
        user = self.request.user
        if user.user_type != "super_admin":
            raise PermissionDenied({"error":"Only super admin can update organization details."})
        
        # Save organization
        organization = serializer.save()

        # Create location record (with empty values first)
        Org_Location_Model.objects.create(
            org_id=organization.org_id,
            dist=None,
            city=None,
            geom=None
        )

        # Create org_area record (with null array)
        Org_Area_Model.objects.create(
            org_id=organization.org_id,
            org_area=None
        )

#------------------------------------------------------------------------------
class SL_Organization_Get_By_ID_View(RetrieveAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = SL_Organization_Model.objects.all()
    serializer_class = SL_Organization_Serializer
    # lookup_field = "org_id"  # match org_id from URL

    def get_object(self):
        user = self.request.user
        if user.user_type != "super_admin":
            raise PermissionDenied({"error":"Only super admin can update organization details."})
        return super().get_object()
    
#------------------------------------------------------------------------------
class SL_Organization_Update_View(RetrieveUpdateAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = SL_Organization_Model.objects.all()
    serializer_class = SL_Organization_Serializer
    # lookup_field = "org_id"   # use org_id in URL (optional, can keep pk)

    def get_object(self):
        user = self.request.user
        if user.user_type != "super_admin":
            raise PermissionDenied({"error":"Only super admin can update organization details."})
        return super().get_object()

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        # 🚫 Block status change if org_id matches the super_admin's own org
        if "status" in request.data and instance.org_id == request.user.org_id:
            raise PermissionDenied({"error": "You cannot deactivate your own organization. Please switch to another organization first."})

        return super().partial_update(request, *args, **kwargs)
    
#------------------------------------------------------------------------------
class Org_Detail_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        org_id = user.org_id

        try:
            organization = SL_Organization_Model.objects.get(org_id=org_id)
            serializer = SL_Org_Details_Serializer(organization)
            return Response(serializer.data)
        except SL_Organization_Model.DoesNotExist:
            return Response({"error": "Organization not found."}, status=status.HTTP_404_NOT_FOUND)


#________________________________________________ Organization Area View ________________________________________________________
class GND_By_Org_Area_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = sl_gnd_10m_Serializer

    def get(self, request):
        try:
            user = request.user
            org_id = user.org_id

            if not org_id:
                return Response(
                    {"error": "No org_id associated with this user."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Retrieve the Org_Area_Model
            org_area_data = Org_Area_Model.objects.filter(org_id=org_id).first()

           # If no org_area_data or empty area list, return org_area = null
            if not org_area_data or not org_area_data.org_area:
                return Response(
                    {
                        "org_area": None
                    },
                    status=status.HTTP_200_OK
                )
            
            allowed_area = org_area_data.org_area

            # If org_area = [0], return all data
            if allowed_area == [0]:
                gnd_qs = sl_gnd_10m_Model.objects.all()
            else:
                gnd_qs = sl_gnd_10m_Model.objects.filter(gid__in=allowed_area)

            try:
                serializer = self.serializer_class(gnd_qs, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception:
                # geom column missing in local DB — return empty GeoJSON FeatureCollection
                return Response(
                    {"type": "FeatureCollection", "features": []},
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Org_Area_By_OrgID_View(ListAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, org_id):
        try:
            org_area = Org_Area_Model.objects.get(org_id=org_id)
        except Org_Area_Model.DoesNotExist:
            return Response({"error": "Org area not found"}, status=404)
        
        # ✅ fetch org_name
        org_name = SL_Organization_Model.objects.get(org_id=org_id).display_name
        
        # If org_area is None or empty
        if not org_area.org_area:
            return Response({
                "org_name": org_name,
                "org_area": None
            })
        
        gids = org_area.org_area  # list of gids

        gnd_data = (
            sl_gnd_10m_Model.objects.filter(gid__in=gids).values("dist", "dsd", "gnd", "gid")
            .order_by("dist", "dsd", "gnd")
        )

        return Response({
            "org_name": org_name,
            "org_area": gnd_data
        })

#------------------------------------------------------------------------------
class Org_Area_Update_View(RetrieveUpdateAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Org_Area_Model.objects.all()
    serializer_class = Org_Area_Serializer
    lookup_field = "org_id"  # use org_id instead of pk

    def perform_update(self, serializer):
        user = self.request.user
        # ✅ Optional: restrict update permission
        if user.user_type != "super_admin":
            raise PermissionDenied({"error": "Only super admin can update organization area."})

        serializer.save()


#________________________________________________ Organization Location View ____________________________________________________
class Org_Location_Get_by_ID_View(RetrieveAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Org_Location_Model.objects.all()
    serializer_class = Org_Location_Serializer
    lookup_field = "org_id"  # match org_id from URL

#------------------------------------------------------------------------------
class Org_Location_Get_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_obj = request.user
        org_id = user_obj.org_id

        location_data = Org_Location_Model.objects.filter(org_id=org_id)
        serializer = Org_Location_Serializer(location_data, many=True)

        response_data = {
            "type": "FeatureCollection",
            "features": serializer.data["features"]
        }
        return Response(response_data, status=200)

#------------------------------------------------------------------------------
class Org_Location_Update_View(RetrieveUpdateAPIView):
    http_method_names = ['patch']   # only allow PATCH
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Org_Location_Model.objects.all()
    serializer_class = Org_Location_Serializer
    lookup_field = "org_id"  # use org_id instead of pk

    def perform_update(self, serializer):
        user = self.request.user
        # ✅ Optional: restrict update permission
        if user.user_type != "super_admin":
            raise PermissionDenied({"error": "Only super admin can update organization location."})

        serializer.save()


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


#________________________________________________ Survey Rep DATA View __________________________________________________________
class Survey_Rep_DATA_Save_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = Survey_Rep_DATA_Serializer

    def post(self, request):

        import logging
        logger = logging.getLogger('survey_rep_save')

        data = request.data
        user = request.user
        user_id = user.id

        logger.debug(f"[SAVE] ── New save request from user_id={user_id}, feature_count={len(data) if isinstance(data, list) else 'NOT A LIST'}")

        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response({"error": "User has no assigned roles."}, status=403)

        role_id = user_roles.values_list('role_id', flat=True).first()

        if not isinstance(data, list):
            return Response({"Expected a list of GEOM DATA"}, status=400)

        saved_records = []
        errors = []
        warnings = []

        with transaction.atomic():
            for index, item in enumerate(data):
                _props = item.get("properties", {})
                _geom  = item.get("geometry", {})
                logger.debug(
                    f"[SAVE] [{index}] uuid={_props.get('uuid')} | layer_id={_props.get('layer_id')} "
                    f"| geom_type={_geom.get('type')} | area={_props.get('area')} "
                    f"| gnd_id={_props.get('gnd_id')} | parent_uuid={_props.get('parent_uuid')} "
                    f"| feature_Id={_props.get('feature_Id')} | isUpdateOnly={_props.get('isUpdateOnly')}"
                )
                try:
                  with transaction.atomic():
                     # Step 1: Check if user has save/edit permission
                    permission_id = 201

                    # Check if parent_uuid is null or not
                    parent_uuid = item.get("properties", {}).get("parent_uuid", [])

                    if not parent_uuid:  # parent_uuid is null or empty → ADD permission
                        has_permission = Role_Permission_Model.objects.filter(
                            role_id=role_id,
                            permission_id=permission_id,
                            add=True
                        ).exists()
                        if not has_permission:
                            return Response({"error": "You do not have add permission."}, status=403)

                    else:  # parent_uuid exists → EDIT permission
                        has_permission = Role_Permission_Model.objects.filter(
                            role_id=role_id,
                            permission_id=permission_id,
                            edit=True
                        ).exists()
                        if not has_permission:
                            return Response({"error": "You do not have edit permission."}, status=403)   

                    item.setdefault("properties", {})["user_id"] = user.id
                    item["properties"]["org_id"] = user.org_id

                    # Retrieve layer_ids associated with the user for save data to LA_LS_MyLayer
                    my_layerIDs = LayersModel.objects.filter(group_name__contains=[user_id]).values_list('layer_id', flat=True)
                    
                    # Extract geom_type for save it to geom_type field
                    geom_type = item.get("geometry", {}).get("type", None)
                    if not geom_type:
                        raise ValueError("The 'geometry.type' field is required")
                    
                    geom_type = geom_type.lower()
                    item["properties"]["geom_type"] = geom_type

                    # Extract length and assign it to the area field if geom_type is 'linestring'
                    if geom_type == "linestring":
                        length_value = item.get("properties", {}).get("length")
                        if length_value is not None:
                            item["properties"]["area"] = length_value

                    # Check gnd_id only for Polygon or MultiPolygon
                    if geom_type in ["polygon", "multipolygon"]:
                        layer_id_val = item.get("properties", {}).get("layer_id")
                        is_land_parcel = layer_id_val in [1, 6]
                        gndID = item.get("properties", {}).get("gnd_id")
                        if not gndID:
                            # gnd_id missing — auto-detect via PostGIS spatial intersection
                            geom_json = item.get("geometry")
                            geom_obj = GEOSGeometry(json.dumps(geom_json), srid=4326)
                            # Get all intersecting GNDs ordered by intersection area (largest first — dominant GND)
                            try:
                                # Wrap in its own savepoint so a DB error (e.g. missing
                                # geom column on sl_gnd_10m) is rolled back before we
                                # continue — otherwise PostgreSQL leaves the connection in
                                # an ABORTED state and all subsequent queries fail with
                                # "current transaction is aborted".
                                with transaction.atomic():
                                    intersecting_gnds = (
                                        sl_gnd_10m_Model.objects
                                        .filter(geom__intersects=geom_obj)
                                        .annotate(inter_area=Area(GeoIntersection('geom', geom_obj)))
                                        .order_by('-inter_area')
                                    )
                                    dominant_gnd = intersecting_gnds.first()
                            except Exception:
                                # sl_gnd_10m has no geom column — skip GND validation
                                dominant_gnd = None
                                is_land_parcel = False  # allow save without GND

                            if not dominant_gnd:
                                if is_land_parcel:
                                    raise ValueError("Cannot save land parcel: geometry does not fall within any GND boundary.")
                                else:
                                    item["properties"]["gnd_id"] = None
                            else:
                                # Validate detected GND is within the org's allowed area
                                org_area_obj = Org_Area_Model.objects.filter(org_id=user.org_id).first()
                                if org_area_obj and org_area_obj.org_area and org_area_obj.org_area != [0]:
                                    if dominant_gnd.gid not in org_area_obj.org_area:
                                        if is_land_parcel:
                                            raise ValueError("Cannot save land parcel: geometry falls outside your organisation's allowed GND area.")
                                        else:
                                            item["properties"]["gnd_id"] = None
                                    else:
                                        item["properties"]["gnd_id"] = dominant_gnd.gid
                                else:
                                    item["properties"]["gnd_id"] = dominant_gnd.gid

                    # Extract parent_id
                    parent_ids = item.get("properties", {}).get("parent_id", [])
                    if isinstance(parent_ids, list) and parent_ids:
                        Survey_Rep_DATA_Model.objects.filter(id__in=parent_ids).update(status=False)

                    # Extract parent_uuid and convert it to parent_id
                    parent_uuids = item.get("properties", {}).get("parent_uuid", [])
                    parent_ids = []

                    if isinstance(parent_uuids, list) and parent_uuids:
                        parent_ids = list(Survey_Rep_DATA_Model.objects.filter(uuid__in=parent_uuids).values_list('id', flat=True))
                        item["properties"]["parent_id"] = parent_ids  # Assign retrieved IDs to parent_id

                    # Update status for parent_ids if they exist
                    if parent_ids:
                        Survey_Rep_DATA_Model.objects.filter(id__in=parent_ids).update(status=False)
                        logger.debug(f"[SAVE] [{index}] Parent IDs set to status=False: {parent_ids}")

                    serializer = self.serializer_class(data=item)
                    if serializer.is_valid():

                        # Save Survey_Rep_DATA_Model instance
                        survey_rep = serializer.save()
                        survey_rep.su_id_id = survey_rep.id
                        survey_rep.save()
                        logger.debug(f"[SAVE] [{index}] Saved survey_rep id={survey_rep.id} uuid={survey_rep.uuid} status={survey_rep.status} gnd_id={survey_rep.gnd_id} layer_id={survey_rep.layer_id}")

                        # Create record to Survey_Rep_Geom_History_Model
                        # Use stored reference_coordinate or fall back to geometry centroid
                        _ref_coord = survey_rep.reference_coordinate
                        if _ref_coord is None and survey_rep.geom:
                            _ref_coord = survey_rep.geom.centroid
                        Survey_Rep_Geom_History_Model.objects.create(
                            su_id=survey_rep.id,
                            user_id=survey_rep.user_id,
                            layer_id=survey_rep.layer_id,
                            area=survey_rep.area,
                            reference_coordinate=_ref_coord,
                            geom=survey_rep.geom,
                            status=survey_rep.status,
                            ref_id=survey_rep.ref_id,
                        )

                        # Create LA_Spatial_Unit_Model instance
                        suID = LA_Spatial_Unit_Model.objects.create(su_id=survey_rep.id)

                        # Create SL_BA_Unit_Model instance linked to Models
                        # SL_BA_Unit_Model.objects.create(su_id=suID)

                        # Creation of other models based on layer_id
                        if survey_rep.layer_id in [1, 3, 6, 12]:
                            if survey_rep.geom_type in ["multipolygon", "polygon"]:
                                Assessment_Model.objects.create(su_id=suID, user_id=user.id)
                                Tax_Info_Model.objects.create(su_id=suID)
                        
                        if survey_rep.layer_id in [3, 12]:
                            if survey_rep.geom_type in ["multipolygon", "polygon"]:
                                LA_SP_Fire_Rescue_Model.objects.create(su_id=suID)

                        if survey_rep.layer_id in [1, 6]:
                            LA_LS_Land_Unit_Model.objects.create(su_id=suID)
                            LA_LS_Utinet_LU_Model.objects.create(su_id=suID)

                        if survey_rep.layer_id in [2, 4, 5, 8, 9, 11]:
                            if survey_rep.geom_type in ["multipolygon", "polygon"]:
                                LA_LS_Ols_Polygon_Unit_Model.objects.create(su_id=suID)
                            elif survey_rep.geom_type in ["linestring", "point"]:
                                LA_LS_Ols_PointLine_Unit_Model.objects.create(su_id=suID)

                        if survey_rep.layer_id == 3:
                            LA_LS_Build_Unit_Model.objects.create(su_id=suID)
                            LA_LS_Utinet_BU_Model.objects.create(su_id=suID)

                        if survey_rep.layer_id == 7:
                            LA_LS_Ols_Polygon_Unit_Model.objects.create(su_id=suID)
                            LA_LS_Utinet_Ols_Model.objects.create(su_id=suID)

                        # if survey_rep.layer_id == 12:
                        #     LA_LS_Apt_Unit_Model.objects.create(su_id=suID)
                        #     LA_LS_Utinet_AU_Model.objects.create(su_id=suID)
                        
                        # Check if layer_id is related to the user
                        if survey_rep.layer_id in my_layerIDs:
                            if survey_rep.geom_type in ["multipolygon", "polygon"]:
                                LA_LS_MyLayer_Polygon_Unit_Model.objects.create(su_id=suID)
                            elif survey_rep.geom_type in ["linestring", "point"]:
                                LA_LS_MyLayer_PointLine_Unit_Model.objects.create(su_id=suID)

                       # Add the saved instance to the response
                        saved_records.append(serializer.data)

                    else:
                        logger.debug(f"[SAVE] [{index}] Serializer validation FAILED: {serializer.errors}")
                        errors.append({"index": index, "errors": serializer.errors})
                except Exception as e:
                        logger.debug(f"[SAVE] [{index}] Exception during save: {e}", exc_info=True)
                        errors.append({"index": index, "detail": str(e)})

        # Return the response with saved records and errors
        response_data = {
            "saved_records": saved_records,
            "errors": errors,
            "warnings": warnings,
        }

        logger.debug(f"[SAVE] ── Done: saved={len(saved_records)} errors={len(errors)}")
        if saved_records:
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

#------------------------------------------------------------------------------
class Survey_Rep_DATA_Filter_User_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        user_obj = request.user
        userID = user_obj.id # Retrieve userID from the User model
        org_id = user_obj.org_id

        layers = LayersModel.objects.filter(
            Q(group_name__contains=["default"]) | 
            Q(group_name__contains=[userID]) |
            (Q(group_name__contains=["org"]) & Q(org_id=org_id)) |
            Q(user_id=userID)
        ).values_list('layer_id', flat=True)

        # Use the retrieved layer_ids to filter Survey_Rep_DATA_Model
        # Exclude null-geometry records — these are legacy LADM records imported
        # without spatial data.  Sending them to the frontend causes console spam
        # and wastes bandwidth since they can never be rendered.
        geom_data = Survey_Rep_DATA_Model.objects.filter(
            layer_id__in=layers,
            status=True,
            org_id=org_id,
            geom__isnull=False,
        )

        # Serialize geom data
        serializer = Survey_Rep_DATA_Serializer(geom_data, many=True)
        return Response(serializer.data, status=200)

#------------------------------------------------------------------------------
class Survey_Rep_DATA_Update_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Survey_Rep_DATA_Model.objects.all()
    serializer_class = Survey_Rep_DATA_Serializer

    def update(self, request, *args, **kwargs):

        data = request.data
        user = request.user
        user_id = user.id

        # 🔐 Step 1: Check if user has edit permission

        edit_permission_id = 201

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
            return Response({"error": "You do not have permission."}, status=403)
        
        # print("Received GeoJSON Data:",json.dumps(data, indent=4))

        with transaction.atomic():
            # Retrieve the instance being updated
            instance = self.get_object()

            # Store the current values for comparison
            old_data = {
                "user_id": instance.user_id,
                "layer_id": instance.layer_id,
                "area": instance.area,
                "reference_coordinate": instance.reference_coordinate,
                "geom": instance.geom,
                "status": instance.status,
                "ref_id": instance.ref_id,
            }

            # Update the date_modified field
            instance.date_modified = now()
            instance.save(update_fields=['date_modified'])

            # Proceed with the default update logic
            response = super().update(request, *args, **kwargs)

            # Check if any of the specific fields were updated
            updated_instance = self.get_object()  # Get the instance with updated values
            new_data = {
                "user_id": updated_instance.user_id,
                "layer_id": updated_instance.layer_id,
                "area": updated_instance.area,
                "reference_coordinate": updated_instance.reference_coordinate,
                "geom": updated_instance.geom,
                "status": updated_instance.status,
                "ref_id": instance.ref_id,
            }

            if old_data != new_data:  # Compare old and new data
                Survey_Rep_Geom_History_Model.objects.create(
                    su_id=updated_instance.id,
                    user_id=updated_instance.user_id,
                    layer_id=updated_instance.layer_id,
                    area=updated_instance.area,
                    reference_coordinate=updated_instance.reference_coordinate,
                    geom=updated_instance.geom,
                    status=updated_instance.status,
                    ref_id=updated_instance.ref_id,
                )

            # Refresh the instance to include the latest data
            updated_instance.refresh_from_db()

            # Serialize and return the updated instance
            serializer = self.get_serializer(updated_instance)

            return Response(serializer.data, status=200)

#------------------------ Bulk DELETE by IDs ----------------------------------
class Survey_Rep_DATA_BulkDelete_id_View(APIView):
    http_method_names = ['delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete_record_and_related(self, request, su_id):
        user = request.user
        user_id = user.id

        user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
        if not user_roles.exists():
            return Response({"error": "User has no assigned roles."}, status=403)

        role_id = user_roles.values_list('role_id', flat=True).first()

        # 🔐 Step 1: Check if user has delete permission

        del_permission_id = 201

        has_permission = Role_Permission_Model.objects.filter(
            role_id=role_id,
            permission_id=del_permission_id,
            delete=True
        ).exists()

        if not has_permission:
            return Response({"error": "You do not have delete permission."}, status=403)

        total_deleted = 0
        parent_ids = []

        try:
            primary = Survey_Rep_DATA_Model.objects.get(id=su_id)
            parent_ids = primary.parent_id or []

            # Delete LA_Spatial_Unit_Model for this su_id
            total_deleted += LA_Spatial_Unit_Model.objects.filter(su_id=su_id).delete()[0]

            # Delete ref_id-related Survey_Rep_DATA_Model and LA_Spatial_Unit_Model
            ref_qs = Survey_Rep_DATA_Model.objects.filter(ref_id=su_id)
            ref_ids = list(ref_qs.values_list("id", flat=True))
            total_deleted += ref_qs.delete()[0]
            total_deleted += LA_Spatial_Unit_Model.objects.filter(su_id__in=ref_ids).delete()[0]

            # Delete the main record
            primary.delete()
            total_deleted += 1

        except Survey_Rep_DATA_Model.DoesNotExist:
            pass

        return total_deleted, parent_ids

    def delete(self, request):
        su_ids = request.data.get('ids', [])
        if not isinstance(su_ids, list) or not su_ids:
            return Response({"error": "Please provide a list of ids to delete."}, status=status.HTTP_400_BAD_REQUEST)

        total_deleted = 0
        deleted_ids = set()
        parent_ids_to_update = set()

        for su_id in su_ids:
            if su_id in deleted_ids:
                continue

            # Pass request to the method
            result = self.delete_record_and_related(request, su_id)
            if isinstance(result, Response):  # permission denied
                return result

            deleted, parent_ids = result
            total_deleted += deleted
            deleted_ids.add(su_id)

            if len(parent_ids) == 1:
                parent_id = parent_ids[0]
                siblings = Survey_Rep_DATA_Model.objects.filter(parent_id__contains=[parent_id])
                for sibling in siblings:
                    if sibling.id not in deleted_ids:
                        d_result = self.delete_record_and_related(request, sibling.id)
                        if isinstance(d_result, Response):  # permission denied
                            return d_result

                        d, _ = d_result
                        total_deleted += d
                        deleted_ids.add(sibling.id)

                parent_ids_to_update.add(parent_id)

            elif len(parent_ids) > 1:
                parent_ids_to_update.update(parent_ids)

        if parent_ids_to_update:
            Survey_Rep_DATA_Model.objects.filter(id__in=parent_ids_to_update).update(status=True)

        return Response(
            {"message": f"Records deleted. {total_deleted} total record(s) affected."},
            status=status.HTTP_200_OK
        )


#________________________________________________ Survey Rep History View _______________________________________________________ not used
class Survey_Rep_History_View_filter(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        rep_history = Survey_Rep_History_Model.objects.filter(su_id=su_id)
        serializer = Survey_Rep_History_Serializer(rep_history, many=True)
        return Response(serializer.data, status=200)

#------------------------------------------------------------------------------
class Survey_Rep_History_View_filter_username(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user  # Get user from token
        user_id = user.id    # Extract user_id


        # Step 1: Get Survey_Rep_History records for the given userID
        rep_history = Survey_Rep_History_Model.objects.filter(user_id=user_id)
        serializer = Survey_Rep_History_Serializer_username(rep_history, many=True)

        # Step 2: Extract `layer_id` for each record in `serializer.data`
        response_data = []
        for record in serializer.data:
            su_id = record.get('su_id')  # Assuming `su_id` is in serializer.data

            # Add `layer_id` to the response
            layer_id_record = Survey_Rep_DATA_Model.objects.filter(id=su_id).values('layer_id').first()
            record['layer_id'] = layer_id_record['layer_id'] if layer_id_record else None

            # Fetch `user_email` from User model
            user_id = record.get('user_id')
            user = User.objects.filter(id=user_id).values('email').first()
            record['username'] = user['email'] if user else None

            response_data.append(record)

        # Return the response with layer_id and other serializer data
        return Response(response_data, status=200)

#------------------------------------------------------------------------------
class Survey_Rep_History_View_update(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch', 'put', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Survey_Rep_History_Model.objects.all()
    serializer_class = Survey_Rep_History_Serializer


#________________________________________________ Geom Edit History View ________________________________________________________
class Geom_Edit_History_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = Survey_Rep_Geom_History_Serializer

    def get_queryset(self):
        # Get the su_id from the URL
        ver_suid = self.kwargs.get('ver_suid')
   
        # Subquery to find the earliest record for each unique geom
        earliest_geom_records = (Survey_Rep_Geom_History_Model.objects.filter(su_id=ver_suid)
            .values('geom')  # Group by geom
            .annotate(earliest_date=Min('date_created'))  # Find the earliest date for each geom
            .values_list('geom', 'earliest_date')  # Get geom and earliest date pairs
        )

        # Filter to include only records with the earliest date for each unique geom
        queryset = Survey_Rep_Geom_History_Model.objects.filter(su_id=ver_suid).filter(
            Q(geom__in=[record[0] for record in earliest_geom_records]) &
            Q(date_created__in=[record[1] for record in earliest_geom_records])
        )

        return queryset.order_by('date_created')


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


#________________________________________________ Search Geom View ______________________________________________________________
class Search_Geom_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only process if su_id is provided
        if "su_id" not in request.data:
            return Response(
                {"error": "su_id field is required at this time."},
                status=status.HTTP_400_BAD_REQUEST
            )

        su_id = request.data.get("su_id")

        records = Survey_Rep_DATA_Model.objects.filter(
            id=su_id,  # using su_id as id
            org_id=request.user.org_id
        )

        if not records.exists():
            return Response(
                {"error": f"No records found for su_id {su_id} in your organization."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = Search_Geom_Serializer(records, many=True)
        data = serializer.data

        # ✅ Add layer_name and GND details to each record
        for item in data:
            # Layer name
            try:
                layer = LayersModel.objects.get(layer_id=item["layer_id"])
                item["layer_name"] = layer.layer_name
            except LayersModel.DoesNotExist:
                item["layer_name"] = None

            # GND details (without geom)
            try:
                gnd_data = sl_gnd_10m_Model.objects.values("gnd", "dsd").get(gid=item["gnd_id"])
                item.update(gnd_data)
            except sl_gnd_10m_Model.DoesNotExist:
                item["gnd"] = None
                item["dsd"] = None

            # ✅ Add Postal address only if layer_id is 1 or 6
            if item["layer_id"] in [1, 6]:
                try:
                    postal_data = LA_LS_Land_Unit_Model.objects.values(
                        "postal_ad_lnd"
                    ).get(su_id=su_id)
                    item["postal_address"] = postal_data["postal_ad_lnd"]
                except LA_LS_Land_Unit_Model.DoesNotExist:
                    item["postal_address"] = None

            # ✅ Add Postal address only if layer_id is 3
            elif item["layer_id"] == 3:
                try:
                    postal_data = LA_LS_Build_Unit_Model.objects.values(
                        "postal_ad_build"
                    ).get(su_id=su_id)
                    item["postal_address"] = postal_data["postal_ad_build"]
                except LA_LS_Build_Unit_Model.DoesNotExist:
                    item["postal_address"] = None

            else:
                item["postal_address"] = None

        return Response(data, status=status.HTTP_200_OK)


#________________________________________________ Query Parcels View ___________________________________________________________
class Query_Parcels_View(APIView):
    """
    POST /api/user/query-parcels/
    Body: { layer_id, conditions: [{field, operator, value}], logic: 'AND'|'OR' }
    Returns matching features with GeoJSON geometry + attribute data for table display.
    """
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    LAND_LAYER_IDS = {1, 6}
    BUILDING_LAYER_IDS = {3, 12}

    # operator string → Django ORM lookup suffix
    OPERATOR_MAP = {
        '=':  '',
        '!=': '',       # handled as exclude
        '>':  '__gt',
        '<':  '__lt',
        '>=': '__gte',
        '<=': '__lte',
        '%':  '__icontains',
    }

    # field_name → (source, db_field, value_type)
    LAND_FIELDS = {
        'area_m2':          ('survey',     'area',                   'decimal'),
        'land_name':        ('land_unit',  'land_name',              'string'),
        'access_road':      ('land_unit',  'access_road',            'string'),
        'sl_land_type':     ('land_unit',  'sl_land_type',           'string'),
        'postal_address':   ('land_unit',  'postal_ad_lnd',          'string'),
        'assessment_value': ('assessment', 'assessment_annual_value', 'decimal'),
        'market_value':     ('assessment', 'market_value',           'decimal'),
        'land_value':       ('assessment', 'land_value',             'decimal'),
        'tax_status':       ('assessment', 'tax_status',             'string'),
    }

    BUILDING_FIELDS = {
        'area_m2':            ('survey',     'area',                   'decimal'),
        'building_name':      ('build_unit', 'building_name',          'string'),
        'no_floors':          ('build_unit', 'no_floors',              'int'),
        'structure_type':     ('build_unit', 'structure_type',         'string'),
        'condition':          ('build_unit', 'condition',              'string'),
        'roof_type':          ('build_unit', 'roof_type',              'string'),
        'construction_year':  ('build_unit', 'construction_year',      'int'),
        'assessment_value':   ('assessment', 'assessment_annual_value', 'decimal'),
        'market_value':       ('assessment', 'market_value',           'decimal'),
        'land_value':         ('assessment', 'land_value',             'decimal'),
        'tax_status':         ('assessment', 'tax_status',             'string'),
    }

    def _matching_ids(self, base_qs, source, db_field, suffix, value, negated):
        """Return a Python set of Survey_Rep_DATA_Model PKs matching one condition."""
        if source == 'survey':
            if negated:
                ids = set(base_qs.exclude(**{db_field: value}).values_list('id', flat=True))
            else:
                ids = set(base_qs.filter(**{f'{db_field}{suffix}': value}).values_list('id', flat=True))
        elif source == 'land_unit':
            if negated:
                matched = LA_LS_Land_Unit_Model.objects.filter(**{db_field: value}).values_list('su_id', flat=True)
                ids = set(base_qs.exclude(su_id_id__in=matched).values_list('id', flat=True))
            else:
                matched = LA_LS_Land_Unit_Model.objects.filter(**{f'{db_field}{suffix}': value}).values_list('su_id', flat=True)
                ids = set(base_qs.filter(su_id_id__in=matched).values_list('id', flat=True))
        elif source == 'build_unit':
            if negated:
                matched = LA_LS_Build_Unit_Model.objects.filter(**{db_field: value}).values_list('su_id', flat=True)
                ids = set(base_qs.exclude(su_id_id__in=matched).values_list('id', flat=True))
            else:
                matched = LA_LS_Build_Unit_Model.objects.filter(**{f'{db_field}{suffix}': value}).values_list('su_id', flat=True)
                ids = set(base_qs.filter(su_id_id__in=matched).values_list('id', flat=True))
        elif source == 'assessment':
            if negated:
                matched = Assessment_Model.objects.filter(**{db_field: value}).values_list('su_id', flat=True)
                ids = set(base_qs.exclude(su_id_id__in=matched).values_list('id', flat=True))
            else:
                matched = Assessment_Model.objects.filter(**{f'{db_field}{suffix}': value}).values_list('su_id', flat=True)
                ids = set(base_qs.filter(su_id_id__in=matched).values_list('id', flat=True))
        else:
            ids = set()
        return ids

    def _run_query(self, request):
        """
        Execute the query and return (features, layer_id, error_response).
        error_response is None on success, a Response object on failure.
        """
        layer_id = request.data.get('layer_id')
        conditions = request.data.get('conditions', [])
        logic = str(request.data.get('logic', 'AND')).upper()

        if not layer_id:
            return None, None, Response({'error': 'layer_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            layer_id = int(layer_id)
        except (ValueError, TypeError):
            return None, None, Response({'error': 'layer_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        if layer_id in self.LAND_LAYER_IDS:
            field_map = self.LAND_FIELDS
            is_land = True
        elif layer_id in self.BUILDING_LAYER_IDS:
            field_map = self.BUILDING_FIELDS
            is_land = False
        else:
            return None, None, Response(
                {'error': f'Unsupported layer_id: {layer_id}. Supported: 1, 3, 6, 12'},
                status=status.HTTP_400_BAD_REQUEST
            )

        base_qs = Survey_Rep_DATA_Model.objects.filter(
            layer_id=layer_id,
            org_id=request.user.org_id,
            status=True,
        )

        if not conditions:
            qs = base_qs
        else:
            id_sets = []
            for cond in conditions:
                field    = str(cond.get('field', '')).strip()
                operator = str(cond.get('operator', '='))
                value    = cond.get('value', '')

                if field not in field_map:
                    continue

                source, db_field, field_type = field_map[field]

                try:
                    if field_type == 'int':
                        value = int(value)
                    elif field_type == 'decimal':
                        value = float(value)
                    else:
                        value = str(value)
                except (ValueError, TypeError):
                    return None, None, Response(
                        {'error': f'Invalid value "{value}" for field "{field}"'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                negated  = (operator == '!=')
                suffix   = self.OPERATOR_MAP.get(operator, '')
                cond_ids = self._matching_ids(base_qs, source, db_field, suffix, value, negated)
                id_sets.append(cond_ids)

            if not id_sets:
                qs = base_qs.none()
            elif logic == 'OR':
                result_ids = set().union(*id_sets)
                qs = base_qs.filter(id__in=result_ids)
            else:  # AND
                result_ids = id_sets[0]
                for s in id_sets[1:]:
                    result_ids &= s
                qs = base_qs.filter(id__in=result_ids)

        # ── Bulk-fetch attributes to enrich each feature row ──────────────────
        records  = list(qs[:500])
        su_ids   = [r.su_id_id for r in records if r.su_id_id is not None]

        assessments = {
            a.su_id_id: a
            for a in Assessment_Model.objects.filter(su_id_id__in=su_ids)
        }
        if is_land:
            attr_map = {
                lu.su_id_id: lu
                for lu in LA_LS_Land_Unit_Model.objects.filter(su_id_id__in=su_ids)
            }
        else:
            attr_map = {
                bu.su_id_id: bu
                for bu in LA_LS_Build_Unit_Model.objects.filter(su_id_id__in=su_ids)
            }

        features = []
        for record in records:
            su_id = record.su_id_id
            try:
                geom_json = json.loads(record.geom.geojson) if record.geom else None
            except Exception:
                geom_json = None

            a   = attr_map.get(su_id)
            ass = assessments.get(su_id)

            feat = {
                'su_id':            su_id,
                'layer_id':         record.layer_id,
                'area_m2':          float(record.area) if record.area else None,
                'geojson':          geom_json,
                'assessment_value': float(ass.assessment_annual_value) if ass and ass.assessment_annual_value is not None else None,
                'market_value':     float(ass.market_value)            if ass and ass.market_value is not None else None,
                'land_value':       float(ass.land_value)              if ass and ass.land_value is not None else None,
                'tax_status':       ass.tax_status                     if ass else None,
            }
            if is_land:
                feat.update({
                    'land_name':      a.land_name      if a else None,
                    'access_road':    a.access_road    if a else None,
                    'sl_land_type':   a.sl_land_type   if a else None,
                    'postal_address': a.postal_ad_lnd  if a else None,
                })
            else:
                feat.update({
                    'building_name':     a.building_name     if a else None,
                    'no_floors':         a.no_floors         if a else None,
                    'structure_type':    a.structure_type    if a else None,
                    'condition':         a.condition         if a else None,
                    'roof_type':         a.roof_type         if a else None,
                    'construction_year': a.construction_year if a else None,
                })
            features.append(feat)

        return features, layer_id, None

    def post(self, request):
        features, layer_id, err = self._run_query(request)
        if err:
            return err
        return Response({
            'count':    len(features),
            'layer_id': layer_id,
            'features': features,
        }, status=status.HTTP_200_OK)


#________________________________________________ Query Parcels SHP Export View ________________________________________________
class Query_Parcels_SHP_Export_View(Query_Parcels_View):
    """
    POST /api/user/query-parcels/export-shp/
    Same body as query-parcels/. Returns a ZIP containing a shapefile of the results.
    Requires: pip install pyshp
    """
    WGS84_PRJ = (
        'GEOGCS["GCS_WGS_1984",'
        'DATUM["D_WGS_1984",'
        'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
        'PRIMEM["Greenwich",0.0],'
        'UNIT["Degree",0.0174532925199433]]'
    )

    def post(self, request):
        try:
            import shapefile
        except ImportError:
            return Response({'error': 'pyshp not installed. Run: pip install pyshp'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        import io, zipfile
        from django.http import HttpResponse

        features, layer_id, err = self._run_query(request)
        if err:
            return err

        is_land = layer_id in self.LAND_LAYER_IDS

        shp_buf = io.BytesIO()
        shx_buf = io.BytesIO()
        dbf_buf = io.BytesIO()

        w = shapefile.Writer(shp=shp_buf, shx=shx_buf, dbf=dbf_buf, shapeType=shapefile.POLYGON)
        w.autoBalance = 1

        # Common fields
        w.field('SU_ID',     'N', 10)
        w.field('LAYER_ID',  'N', 4)
        w.field('AREA_M2',   'N', 15, 2)
        w.field('TAX_STAT',  'C', 10)
        w.field('ASMT_VAL',  'N', 15, 2)
        w.field('MKT_VAL',   'N', 15, 2)
        if is_land:
            w.field('LAND_NAME', 'C', 100)
            w.field('LAND_TYPE', 'C', 50)
            w.field('POSTAL',    'C', 100)
        else:
            w.field('BLD_NAME',  'C', 100)
            w.field('FLOORS',    'N', 4)
            w.field('STRUCT',    'C', 30)
            w.field('COND',      'C', 20)

        for feat in features:
            geom = feat.get('geojson')
            if not geom:
                continue
            try:
                gtype  = geom.get('type', '')
                coords = geom.get('coordinates', [])
                if gtype == 'Polygon':
                    w.poly(coords)
                elif gtype == 'MultiPolygon':
                    w.poly([ring for polygon in coords for ring in polygon])
                else:
                    w.null()
            except Exception:
                w.null()

            common = [
                feat.get('su_id') or 0,
                feat.get('layer_id') or 0,
                float(feat.get('area_m2') or 0),
                (feat.get('tax_status') or '')[:10],
                float(feat.get('assessment_value') or 0),
                float(feat.get('market_value') or 0),
            ]
            if is_land:
                w.record(*common,
                         (feat.get('land_name') or '')[:100],
                         (feat.get('sl_land_type') or '')[:50],
                         (feat.get('postal_address') or '')[:100])
            else:
                w.record(*common,
                         (feat.get('building_name') or '')[:100],
                         int(feat.get('no_floors') or 0),
                         (feat.get('structure_type') or '')[:30],
                         (feat.get('condition') or '')[:20])

        w.close()

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('query_results.shp', shp_buf.getvalue())
            zf.writestr('query_results.shx', shx_buf.getvalue())
            zf.writestr('query_results.dbf', dbf_buf.getvalue())
            zf.writestr('query_results.prj', self.WGS84_PRJ)

        resp = HttpResponse(zip_buf.getvalue(), content_type='application/zip')
        resp['Content-Disposition'] = 'attachment; filename="query_results.zip"'
        return resp


#________________________________________________ Geom Create by View ___________________________________________________________
class Geom_Create_by_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Restrict to admin or super_admin
        if request.user.user_type not in ['admin', 'super_admin']:
            return Response(
                {"error": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        su_id = request.data.get('su_id')

        if not su_id:
            return Response(
                {"error": "su_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get survey
        survey_rep = get_object_or_404(Survey_Rep_DATA_Model, id=su_id)

        # Get user
        user = get_object_or_404(User, id=survey_rep.user_id)

        # Combine data
        data = {
            "id": survey_rep.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_created": survey_rep.date_created
        }

        # Serialize and return
        serializer = Geom_Create_by_Serializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

#________________________________________________ Party View ____________________________________________________________________
class Party_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Party_Model.objects.all()
    serializer_class = Party_Serializer

    # def create(self, request, *args, **kwargs):
    #     print("Received JSON:", json.dumps(request.data, indent=4))

    #     return super().create(request, *args, **kwargs)

#------------------------------------------------------------------------------
class Party_Data_Get_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        ext_pid_type = request.data.get('ext_pid_type')
        ext_pid = request.data.get('ext_pid')

        if not ext_pid_type or not ext_pid:
            return Response({'error': 'ext_pid_type and ext_pid are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Normal search
        parties = Party_Model.objects.filter(ext_pid_type=ext_pid_type, ext_pid=ext_pid)

        if parties.exists():
            serializer = Party_Serializer(parties, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Step 2: Search in `other_reg`
        possible_match = Party_Model.objects.filter(other_reg__icontains=ext_pid).first()

        if possible_match:
            return Response({
                'message': f"found under '{possible_match.ext_pid_type}', '{possible_match.ext_pid}'"
            }, status=status.HTTP_200_OK)

        # Step 3: No matches found
        return Response({'message': 'No matching party found'}, status=status.HTTP_404_NOT_FOUND)

#------------------------------------------------------------------------------
class Party_Data_Get_PID_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        pid = request.data.get('pid')

        if not pid:
            return Response({'error': 'pid are required'}, status=status.HTTP_400_BAD_REQUEST)

        parties = Party_Model.objects.filter(pid=pid)
        serializer = Party_Serializer(parties, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
#------------------------------------------------------------------------------
class Party_Data_View_Type(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, type):
        party_type = Party_Model.objects.filter(sl_party_type=type)
        serializer = Party_Type_Serializer(party_type, many=True)
        return Response(serializer.data, status=200)

#------------------------------------------------------------------------------
class Party_Update_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Party_Model.objects.all()
    serializer_class = Party_Update_Serializer

    def update(self, request, *args, **kwargs):

        # print("Received JSON:", json.dumps(request.data, indent=4))

        # Extract `done_by` from the request data
        done_by = request.data.get('done_by')
        if not done_by:
            return Response({"done_by": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the user instance
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data

        # Track changes and log to history table
        for field_name, new_value in validated_data.items():

            old_value = getattr(instance, field_name, None)

            if old_value != new_value:
                # Log the change to the history table
                History_Party_Attrib_Model.objects.create(
                    done_by=done_by,
                    pid=instance.pid,
                    field_name=field_name,
                    field_value=f"Updated from '{old_value}' to '{new_value}'"
                )

        # Save the updated user
        serializer.save()

        # Return a custom response
        return Response({"details": "successfully updated."}, status=status.HTTP_200_OK)


#________________________________________________ Residence Info View ___________________________________________________________
class Residence_Info_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Residence_Info_Model.objects.all()
    serializer_class = Residence_Info_Serializer



#------------------------------------------------------------------------------
class User_Admin_Source_Activity_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, userID):
            # Step 1: Get LA_Admin_Source records created by this user
            admin_sources = LA_Admin_Source_Model.objects.filter(done_by=userID).order_by('-date_created')

            serializer = User_Admin_Source_Activity_Serializer(admin_sources, many=True, context={'request': request})

            # Step 2: For each admin source, find su_id via the RRR → BA Unit chain
            rrr_map = {}
            for rrr in LA_RRR_Model.objects.filter(
                admin_source_id__in=admin_sources.values_list('admin_source_id', flat=True)
            ).select_related('ba_unit_id'):
                src_id = rrr.admin_source_id_id
                if src_id not in rrr_map:
                    rrr_map[src_id] = {
                        'ba_unit_id': rrr.ba_unit_id.ba_unit_id,
                        'su_id': rrr.ba_unit_id.su_id_id,
                    }

            response_data = []
            for record in serializer.data:
                src_id = record.get('admin_source_id')
                linked = rrr_map.get(src_id, {})
                record['ba_unit_id'] = linked.get('ba_unit_id')
                record['su_id'] = linked.get('su_id')
                response_data.append(record)

            return Response(response_data, status=200)

#________________________________________________ SL BA Unit View _______________________________________________________________ not used
class SL_BA_Unit_ID_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        ba_unit_id = SL_BA_Unit_Model.objects.filter(su_id=su_id).values_list('ba_unit_id', flat=True).first()
        return Response({"ba_unit_id": ba_unit_id}, status=200)

#________________________________________________ Summary (Land) View ___________________________________________________________
class Lnd_Summary_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get roles for the user
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"detail": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 2: Field to permission mapping
            FIELD_PERMISSION_MAP = {
                "property_type": 10,
                "postal_ad_lnd": 11,
                "assessment_no": 24,
                "assessment_div": 6,
                "land_area": 14
            }

            # Step 3: Check permissions
            allowed_fields = []
            for field_name, perm_id in FIELD_PERMISSION_MAP.items():
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists():
                    allowed_fields.append(field_name)

            # Step 4: Get land unit data
            land_unit = LA_LS_Land_Unit_Model.objects.filter(su_id=su_id).first()
            land_unit_data = {
                "property_type": land_unit.sl_land_type if land_unit else None,
                "postal_ad_lnd": land_unit.postal_ad_lnd if land_unit else None,
            }

            # Step 4a: Get Land Area
            land_area = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
            land_area_data = {
                "land_area": land_area.area if land_area else None
            }

            # Step 5: Get assessment data
            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            assessment_unit_data = {
                "assessment_div": None,
                "assessment_no": None
            }

            if assessment_unit:
                assessment_unit_data["assessment_no"] = assessment_unit.assessment_no

                ass_div = getattr(assessment_unit, 'ass_div', None)
                if ass_div:
                    ward = Assessment_Ward_Model.objects.filter(id=ass_div).first()
                    if ward:
                        assessment_unit_data["assessment_div"] = ward.ward_name

            # Step 6: Combine + Filter by permission
            combined_data = {}

            # Merge both dictionaries
            all_data = {**land_unit_data, **assessment_unit_data, **land_area_data}

            # Add only allowed fields to the response
            for field in allowed_fields:
                if field in all_data:
                    combined_data[field] = all_data[field]

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#________________________________________________ Admin_Info (Land) View ________________________________________________________
class Lnd_Admin_Info_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            
            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 2: Define permission map
            FIELD_PERMISSION_MAP = {
                "administrative_type": 1,
                "pd": 2,
                "dist": 3,
                "dsd": 4,
                "gnd_id": 5,
                "gnd": 5,
                "ass_div": 6,
                "eletorate": 7,
                "local_auth": 8,
                "access_road": 9,
                "sl_land_type": 10,
                "postal_ad_lnd": 11,
                "land_name": 12,
            }

            # Step 3: Get allowed fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 4: Derive gnd_id from spatial intersection of the parcel polygon
            # Falls back to stored gnd_id when the sl_gnd_10m table has no geometry column.
            survey_data = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
            gnd_id = None
            if survey_data and survey_data.geom:
                from django.db import transaction as _tx
                _geom_sid = _tx.savepoint()
                try:
                    gnd_match = sl_gnd_10m_Model.objects.filter(geom__intersects=survey_data.geom).first()
                    gnd_id = gnd_match.gid if gnd_match else None
                    # Cache result back to survey_rep so other queries stay consistent
                    if gnd_id and survey_data.gnd_id != gnd_id:
                        Survey_Rep_DATA_Model.objects.filter(su_id=su_id).update(gnd_id=gnd_id)
                    _tx.savepoint_commit(_geom_sid)
                except Exception:
                    _tx.savepoint_rollback(_geom_sid)
                    gnd_id = survey_data.gnd_id  # geom column missing — use stored value
            elif survey_data:
                gnd_id = survey_data.gnd_id  # fallback to stored value if no geometry yet

            gnd_data = sl_gnd_10m_Model.objects.filter(gid=gnd_id).values("gnd", "dsd", "dist", "pd").first()
            elect_data = SL_Elect_LocalAuth_Model.objects.filter(gnd_id=gnd_id).values("eletorate", "local_auth").first()
            
            land_unit = LA_LS_Land_Unit_Model.objects.filter(su_id=su_id).first()
            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            spatial_unit = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).first()

            # Step 5: Collect all possible data
            all_data = {
                "gnd_id": gnd_id,
                "gnd": gnd_data["gnd"] if gnd_data else None,
                "dsd": gnd_data["dsd"] if gnd_data else None,
                "dist": gnd_data["dist"] if gnd_data else None,
                "pd": gnd_data["pd"] if gnd_data else None,
                "eletorate": elect_data["eletorate"] if elect_data else None,
                "local_auth": (land_unit.local_auth if (land_unit and land_unit.local_auth) else (elect_data["local_auth"] if elect_data else None)),
                "sl_land_type": land_unit.sl_land_type if land_unit else None,
                "tenure_type": land_unit.tenure_type if land_unit else None,
                "access_road": land_unit.access_road if land_unit else None,
                "postal_ad_lnd": land_unit.postal_ad_lnd if land_unit else None,
                "land_name": land_unit.land_name if land_unit else None,
                "registration_date": str(land_unit.registration_date) if land_unit and land_unit.registration_date else None,
                "ass_div": getattr(assessment_unit, 'ass_div', None) if assessment_unit else None,
                "administrative_type": "None"
            }

            # Step 6: Filter by allowed fields
            response_data = {field: value for field, value in all_data.items() if field in allowed_fields}

            # Fields without dedicated permission IDs — always returned
            response_data["registration_date"] = all_data.get("registration_date")
            response_data["tenure_type"] = all_data.get("tenure_type")
            response_data["parcel_status"] = spatial_unit.parcel_status if spatial_unit else None
            response_data["adjacent_parcels"] = land_unit.adjacent_parcels if land_unit else None
            response_data["parent_parcel"] = land_unit.parent_parcel if land_unit else None
            response_data["child_parcels"] = land_unit.child_parcels if land_unit else None
            response_data["part_of_estate"] = land_unit.part_of_estate if land_unit else None

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Lnd_Admin_Info_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "LND"

            # Step 1: Get user's roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)
            
            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: editable fields and permission IDs
            # gnd_id is excluded — it is auto-derived from spatial intersection, not user-editable
            FIELD_PERMISSION_MAP = {
                "ass_div": 6,
                "local_auth": 8,
                "access_road": 9,
                "sl_land_type": 10,
                "postal_ad_lnd": 11,
                "land_name": 12,
            }

            # Step 3: allowed editable fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 4: Filter request data by allowed fields
            filtered_data = {field: value for field, value in request.data.items() if field in allowed_fields}

            # --- LA_LS_Land_Unit_Model update ---
            # Use get_or_create so parcels imported before this record was auto-created still work
            spatial_unit_ref = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).first()
            if spatial_unit_ref:
                land_unit, _ = LA_LS_Land_Unit_Model.objects.get_or_create(su_id=spatial_unit_ref)
            else:
                land_unit = None
            if land_unit:
                lu_fields = ["sl_land_type", "tenure_type", "access_road", "postal_ad_lnd", "land_name", "local_auth"]
                lu_data = {f: filtered_data[f] for f in lu_fields if f in filtered_data}
                # Fields without dedicated permission IDs — always allowed
                for rel_field in ["adjacent_parcels", "parent_parcel", "child_parcels", "part_of_estate"]:
                    if rel_field in request.data:
                        lu_data[rel_field] = request.data[rel_field] or None
                if "registration_date" in request.data and request.data["registration_date"]:
                    lu_data["registration_date"] = request.data["registration_date"]
                if "tenure_type" in request.data:
                    lu_data["tenure_type"] = request.data["tenure_type"] or None
                if lu_data:
                    original_data = land_unit.__dict__.copy()
                    serializer = LA_LS_Land_Unit_Serializer(land_unit, data=lu_data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
                    else:
                        return Response(serializer.errors, status=400)

            # --- Assessment_Model update ---
            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            if assessment_unit and "ass_div" in filtered_data:
                original_data = assessment_unit.__dict__.copy()
                serializer = Assessment_Serializer(assessment_unit, data={"ass_div": filtered_data["ass_div"]}, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=400)

            # --- LA_Spatial_Unit_Model update (parcel_status) — always allowed ---
            if "parcel_status" in request.data:
                spatial_unit = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).first()
                if spatial_unit:
                    spatial_unit.parcel_status = request.data["parcel_status"] or None
                    spatial_unit.save(update_fields=["parcel_status"])

            return Response({"detail": "Data updated successfully."}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(History_Spartialunit_Attrib_Model(
                    user_id=user_id,
                    su_id_id=su_id,
                    category=category,
                    field_name=field,
                    field_value=new_value
                ))
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)

#________________________________________________ Overview DATA (Land) View _____________________________________________________
class Lnd_Overview_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user's roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"detail": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Define permission map
            FIELD_PERMISSION_MAP = {
                "dimension_2d_3d": 13,
                "boundary_type": 13,
                "crs": 13,
                "area": 14,
                "perimeter": 14,
                "reference_coordinate": 16,
                "ext_landuse_type": 17,
                "ext_landuse_sub_type": 18,
            }

            # Step 3: Get allowed fields
            allowed_fields = [
                key for key, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 4: Get land unit data (primary LADM source for spatial attrs)
            land_unit = LA_LS_Land_Unit_Model.objects.filter(su_id=su_id).first()

            # Step 5: Get Survey Rep data (fallback for area/dimension + reference_coordinate)
            survey_data = Survey_Rep_DATA_Model.objects.filter(id=su_id).first()
            survey_area = None
            survey_dim = None
            survey_ref_coord = None
            if survey_data:
                sr_serializer = Survey_Rep_DATA_Overview_Serializer(survey_data)
                sr_data = sr_serializer.data
                survey_area = sr_data.get("area")
                survey_dim = sr_data.get("dimension_2d_3d")
                survey_ref_coord = sr_data.get("reference_coordinate")

            # Prefer la_ls_land_unit values; fall back to survey_rep for backward compat
            all_data = {
                "area": (float(land_unit.area) if land_unit and land_unit.area is not None else survey_area),
                "perimeter": (float(land_unit.perimeter) if land_unit and land_unit.perimeter is not None else None),
                "dimension_2d_3d": (land_unit.dimension_2d_3d if land_unit and land_unit.dimension_2d_3d else survey_dim),
                "boundary_type": land_unit.boundary_type if land_unit else None,
                "crs": land_unit.crs if land_unit else None,
                "reference_coordinate": survey_ref_coord,
                "ext_landuse_type": land_unit.ext_landuse_type if land_unit else None,
                "ext_landuse_sub_type": land_unit.ext_landuse_sub_type if land_unit else None,
            }

            # Step 6: Filter permission-gated fields
            combined_data = {field: all_data[field] for field in allowed_fields if field in all_data}

            return Response(combined_data, status=status.HTTP_200_OK)


        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
#------------------------------------------------------------------------------
class Lnd_Overview_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "LND"

            # Step 1: Get user's role IDs
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)
            
            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Get or create related land unit (parcels imported before auto-creation need this)
            spatial_unit_ref = LA_Spatial_Unit_Model.objects.filter(su_id=su_id).first()
            if not spatial_unit_ref:
                return Response({"error": "Spatial unit not found for the given su_id."}, status=status.HTTP_404_NOT_FOUND)
            land_unit, _ = LA_LS_Land_Unit_Model.objects.get_or_create(su_id=spatial_unit_ref)

            # Step 3: Define permission map (edit-only)
            FIELD_PERMISSION_MAP = {
                "dimension_2d_3d": 13,
                "boundary_type": 13,
                "crs": 13,
                "area": 14,
                "perimeter": 14,
                "ext_landuse_type": 17,
                "ext_landuse_sub_type": 18,
            }

            # Step 4: Determine editable fields for the user
            editable_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 5: Filter update data by editable fields
            update_data = {field: request.data[field] for field in editable_fields if field in request.data}

            # Step 6: Apply land-unit update (only if there are permitted fields to update)
            if update_data:
                original_data = land_unit.__dict__.copy()
                serializer = LA_LS_Land_Unit_Serializer(land_unit, data=update_data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Step 8: Save reference_coordinate (centroid) to survey_rep as a Point geometry (P7)
            if 'reference_coordinate' in request.data and request.data['reference_coordinate']:
                try:
                    from django.contrib.gis.geos import Point
                    lon, lat = [float(x.strip()) for x in str(request.data['reference_coordinate']).split(',')]
                    survey = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
                    if survey:
                        survey.reference_coordinate = Point(lon, lat, srid=4326)
                        survey.save(update_fields=['reference_coordinate'])
                except (ValueError, AttributeError):
                    pass  # ignore malformed coordinate strings

            return Response({"detail": "Data updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(
                    History_Spartialunit_Attrib_Model(
                        user_id=user_id,
                        su_id_id=su_id,
                        category=category,
                        field_name=field,
                        field_value=new_value
                    )
                )
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)

#________________________________________________ Zoning Info (Land) Views _______________________________________________________
class Lnd_Zoning_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    FIELD_PERMISSION_MAP = {
        "zoning_category": 48, "max_building_height": 49, "max_coverage": 50,
        "max_far": 51, "setback_front": 52, "setback_rear": 53,
        "setback_side": 54, "special_overlay": 55,
    }

    def get(self, request, su_id):
        try:
            user_roles = User_Roles_Model.objects.filter(users__contains=[request.user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            role_id = user_roles.values_list("role_id", flat=True).first()
            allowed_fields = [
                f for f, pid in self.FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(role_id=role_id, permission_id=pid, view=True).exists()
            ]
            zoning = LA_LS_Zoning_Model.objects.filter(su_id=su_id).first()
            empty = {f: None for f in allowed_fields}
            if not zoning:
                return Response(empty, status=status.HTTP_200_OK)
            data = LA_LS_Zoning_Serializer(zoning).data
            return Response({f: data.get(f) for f in allowed_fields}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Lnd_Zoning_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    FIELD_PERMISSION_MAP = {
        "zoning_category": 48, "max_building_height": 49, "max_coverage": 50,
        "max_far": 51, "setback_front": 52, "setback_rear": 53,
        "setback_side": 54, "special_overlay": 55,
    }

    def patch(self, request, su_id):
        try:
            user_roles = User_Roles_Model.objects.filter(users__contains=[request.user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            role_id = user_roles.values_list("role_id", flat=True).first()
            allowed_fields = [
                f for f, pid in self.FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(role_id=role_id, permission_id=pid, edit=True).exists()
            ]
            zoning, _ = LA_LS_Zoning_Model.objects.get_or_create(su_id_id=su_id)
            update_data = {k: (None if v == '' else v) for k, v in request.data.items() if k in allowed_fields}
            serializer = LA_LS_Zoning_Serializer(zoning, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"detail": "Zoning data updated successfully."}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#________________________________________________ Physical_Env_Info (Land) Views _________________________________________________
class Lnd_Physical_Env_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    FIELD_PERMISSION_MAP = {
        "elevation": 43, "slope": 44, "soil_type": 45,
        "flood_zone": 46, "vegetation_cover": 47,
    }

    def get(self, request, su_id):
        try:
            user_roles = User_Roles_Model.objects.filter(users__contains=[request.user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            role_id = user_roles.values_list("role_id", flat=True).first()
            allowed_fields = [
                f for f, pid in self.FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(role_id=role_id, permission_id=pid, view=True).exists()
            ]
            obj = LA_LS_Physical_Env_Model.objects.filter(su_id=su_id).first()
            empty = {f: None for f in allowed_fields}
            if not obj:
                return Response(empty, status=status.HTTP_200_OK)
            data = LA_LS_Physical_Env_Serializer(obj).data
            return Response({f: data.get(f) for f in allowed_fields}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Lnd_Physical_Env_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    FIELD_PERMISSION_MAP = {
        "elevation": 43, "slope": 44, "soil_type": 45,
        "flood_zone": 46, "vegetation_cover": 47,
    }

    def patch(self, request, su_id):
        try:
            user_roles = User_Roles_Model.objects.filter(users__contains=[request.user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            role_id = user_roles.values_list("role_id", flat=True).first()
            allowed_fields = [
                f for f, pid in self.FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(role_id=role_id, permission_id=pid, edit=True).exists()
            ]
            obj, _ = LA_LS_Physical_Env_Model.objects.get_or_create(su_id_id=su_id)
            update_data = {k: (None if v == '' else v) for k, v in request.data.items() if k in allowed_fields}
            serializer = LA_LS_Physical_Env_Serializer(obj, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"detail": "Physical/environmental data updated successfully."}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#________________________________________________ LA_BAUnit_SpatialUnit (M:M) Views _____________________________________________
class LA_BAUnit_SpatialUnit_View(APIView):
    """LADM ISO 19152 – manage the M:M associations between BA units and spatial units.

    GET  ba-unit-spatial-unit/ba_unit_id=<int>/  → list all SUs linked to this BA unit
    POST ba-unit-spatial-unit/ba_unit_id=<int>/  → add a new association  { su_id, relation_type? }
    DELETE ba-unit-spatial-unit/ba_unit_id=<int>/ → remove one association { id }
    """
    http_method_names = ['get', 'post', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, ba_unit_id):
        try:
            links = LA_BAUnit_SpatialUnit_Model.objects.filter(ba_unit_id=ba_unit_id)
            serializer = LA_BAUnit_SpatialUnit_Serializer(links, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, ba_unit_id):
        try:
            su_id = request.data.get('su_id')
            relation_type = request.data.get('relation_type', 'PRIMARY')
            if not su_id:
                return Response({"error": "su_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            if not LA_Spatial_Unit_Model.objects.filter(su_id=su_id).exists():
                return Response({"error": "Spatial unit not found."}, status=status.HTTP_404_NOT_FOUND)
            link, created = LA_BAUnit_SpatialUnit_Model.objects.get_or_create(
                ba_unit_id=ba_unit_id, su_id=su_id,
                defaults={'relation_type': relation_type}
            )
            if not created:
                link.relation_type = relation_type
                link.save()
            serializer = LA_BAUnit_SpatialUnit_Serializer(link)
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, ba_unit_id):
        try:
            link_id = request.data.get('id') or request.query_params.get('id')
            if not link_id:
                return Response({"error": "id is required."}, status=status.HTTP_400_BAD_REQUEST)
            deleted, _ = LA_BAUnit_SpatialUnit_Model.objects.filter(
                id=link_id, ba_unit_id=ba_unit_id
            ).delete()
            if deleted == 0:
                return Response({"error": "Association not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"detail": "Association removed."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────────────────────
# RRR Role-Based Permission Helpers
# ─────────────────────────────────────────────────────────────────────────────
_LAND_LAYERS    = frozenset({1, 6})
_BUILDING_LAYERS = frozenset({3, 12})
_RRR_PERM_LAND     = 59   # Land RRR section permission ID
_RRR_PERM_BUILDING = 162  # Building RRR section permission ID


def _rrr_perm_for_su(su_id):
    """Return the correct RRR permission ID (59 or 162) for a spatial unit."""
    sr = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).values('layer_id').first()
    if sr:
        if sr['layer_id'] in _LAND_LAYERS:
            return _RRR_PERM_LAND
        if sr['layer_id'] in _BUILDING_LAYERS:
            return _RRR_PERM_BUILDING
    # Fallback: if a build_unit record exists it is a building
    if LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).exists():
        return _RRR_PERM_BUILDING
    return _RRR_PERM_LAND


def _rrr_perm_for_ba(ba_unit_id):
    """Return the RRR permission ID by resolving ba_unit_id → su_id."""
    ba = SL_BA_Unit_Model.objects.filter(ba_unit_id=ba_unit_id).values('su_id_id').first()
    return _rrr_perm_for_su(ba['su_id_id']) if ba else _RRR_PERM_LAND


def _rrr_perm_for_rrr_id(rrr_id):
    """Return the RRR permission ID by resolving rrr_id → ba_unit → su_id."""
    rrr = LA_RRR_Model.objects.filter(rrr_id=rrr_id).values('ba_unit_id_id').first()
    return _rrr_perm_for_ba(rrr['ba_unit_id_id']) if rrr else _RRR_PERM_LAND


def _has_rrr_perm(user_id, perm_id, action):
    """Return True if the user's role has the RRR permission for the given action.
    action must be one of: 'view', 'edit', 'add'
    """
    role = User_Roles_Model.objects.filter(users__contains=[user_id]).values('role_id').first()
    if not role:
        return False
    return Role_Permission_Model.objects.filter(
        role_id=role['role_id'],
        permission_id=perm_id,
        **{action: True}
    ).exists()


def _rrr_permission_denied():
    return Response({"error": "You do not have permission to perform this RRR action."},
                    status=status.HTTP_403_FORBIDDEN)


#________________________________________________ RRR Restriction Views __________________________________________________________
class RRR_Restriction_View(APIView):
    http_method_names = ['get', 'post', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'view'):
            return _rrr_permission_denied()
        try:
            restrictions = LA_RRR_Restriction_Model.objects.filter(rrr_id=rrr_id)
            serializer = LA_RRR_Restriction_Serializer(restrictions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'add'):
            return _rrr_permission_denied()
        try:
            allowed_fields = ['rrr_restriction_type', 'description', 'time_begin', 'time_end']
            data = {k: (None if v == '' else v) for k, v in request.data.items() if k in allowed_fields}
            data['rrr_id'] = rrr_id
            serializer = LA_RRR_Restriction_Serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()
        restriction_id = request.data.get('id') or request.query_params.get('id')
        if not restriction_id:
            return Response({"error": "id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            obj = LA_RRR_Restriction_Model.objects.get(id=restriction_id, rrr_id=rrr_id)
            obj.delete()
            return Response({"detail": "Restriction deleted."}, status=status.HTTP_200_OK)
        except LA_RRR_Restriction_Model.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#________________________________________________ RRR Responsibility Views _______________________________________________________
class RRR_Responsibility_View(APIView):
    http_method_names = ['get', 'post', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'view'):
            return _rrr_permission_denied()
        try:
            responsibilities = LA_RRR_Responsibility_Model.objects.filter(rrr_id=rrr_id)
            serializer = LA_RRR_Responsibility_Serializer(responsibilities, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'add'):
            return _rrr_permission_denied()
        try:
            allowed_fields = ['rrr_responsibility_type', 'description', 'time_begin', 'time_end']
            data = {k: (None if v == '' else v) for k, v in request.data.items() if k in allowed_fields}
            data['rrr_id'] = rrr_id
            serializer = LA_RRR_Responsibility_Serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, rrr_id):
        perm_id = _rrr_perm_for_rrr_id(rrr_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()
        responsibility_id = request.data.get('id') or request.query_params.get('id')
        if not responsibility_id:
            return Response({"error": "id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            obj = LA_RRR_Responsibility_Model.objects.get(id=responsibility_id, rrr_id=rrr_id)
            obj.delete()
            return Response({"detail": "Responsibility deleted."}, status=status.HTTP_200_OK)
        except LA_RRR_Responsibility_Model.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#________________________________________________ Utility_Network_Info (Land) View ______________________________________________
class Lnd_Utility_Network_Info_View(ListCreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        user = request.user

        # Step 1: Get user roles
        user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
        if not user_roles.exists():
            return Response({"detail": "User has no assigned roles."}, status=403)

        # Step 2: Field to permission mapping
        FIELD_PERMISSION_MAP = {
            "electricity": 19,
            "water_supply": 20,
            "drainage_system": 21,
            "sanitation_gully": 22,
            "garbage_disposal": 23,
        }

        # Step 3: Check allowed fields
        role_id = user_roles.values_list('role_id', flat=True).first()

        allowed_field_keys = [
            key for key, perm_id in FIELD_PERMISSION_MAP.items()
            if Role_Permission_Model.objects.filter(
                role_id=role_id,
                permission_id=perm_id,
                view=True
            ).exists()
        ]

        # Step 4: Fetch utility network data
        utinet_data = LA_LS_Utinet_LU_Model.objects.filter(su_id=su_id).first()
        if not utinet_data:
            # Return empty nulls for all allowed fields instead of 404
            return Response({key: None for key in allowed_field_keys}, status=200)

        # Step 5: Serialize data
        raw_data = Lnd_Utinet_info_Serializer(utinet_data).data

        # Step 6: Mapping field keys to model fields
        model_field_map = {
            "electricity": "elec",
            "water_supply": "water",
            "drainage_system": "drainage",
            "sanitation_gully": "sani_gully",
            "garbage_disposal": "garbage_dispose"
        }

        # Step 7: Combine + Filter by permission
        response_data = {
            key: raw_data.get(model_field_map[key])
            for key in allowed_field_keys
        }

        return Response(response_data, status=200)

#------------------------------------------------------------------------------
class Lnd_Utility_Network_Info_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "LND"

            utinet_data = LA_LS_Utinet_LU_Model.objects.filter(su_id=su_id).first()
            if not utinet_data:
                utinet_data = LA_LS_Utinet_LU_Model.objects.create(su_id_id=su_id)

            # Permissions: Role → Permissions for editing
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)

            role_id = user_roles.values_list('role_id', flat=True).first()

            # Define field mapping and corresponding permission IDs
            FIELD_PERMISSION_MAP = {
                "water_supply": {"model_field": "water", "permission_id": 20},
                "electricity": {"model_field": "elec", "permission_id": 19},
                "drainage_system": {"model_field": "drainage", "permission_id": 21},
                "sanitation_gully": {"model_field": "sani_gully", "permission_id": 22},
                "garbage_disposal": {"model_field": "garbage_dispose", "permission_id": 23},
            }

            # Copy original data to compare for logging
            original_data = utinet_data.__dict__.copy()

            update_data = {}

            # Only allow updates for fields with `edit=True` permission
            for input_field, info in FIELD_PERMISSION_MAP.items():
                if input_field in request.data:
                    has_edit_perm = Role_Permission_Model.objects.filter(
                        role_id=role_id,
                        permission_id=info["permission_id"],
                        edit=True
                    ).exists()

                    if has_edit_perm:
                        model_field = info["model_field"]
                        update_data[model_field] = request.data[input_field]

            # Apply changes
            for field, value in update_data.items():
                setattr(utinet_data, field, value)

            utinet_data.save()

            # Log updated fields
            self.log_changes(
                user_id=user_id,
                category=category,
                su_id=su_id,
                original_data=original_data,
                updated_data=update_data
            )

            return Response({"detail": "Data updated successfully."}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(
                    History_Spartialunit_Attrib_Model(
                        user_id=user_id,
                        su_id_id=su_id,
                        category=category,
                        field_name=field,
                        field_value=new_value
                    )
                )
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)



#________________________________________________ Summary (Building) View _______________________________________________________
class Bld_Summary_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            
            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Field to permission mapping
            FIELD_PERMISSION_MAP = {
                "assessment_div": 108,
                "postal_ad_bld": 111,
                "bld_property_type": 113,
                "assessment_no": 131,
            }

            # Step 3: Filter fields user has permission to view
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 4: Fetch model data
            bld_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            if not bld_unit:
                return Response({"error": "Data not found for the given su_id."}, status=status.HTTP_404_NOT_FOUND)

            bld_unit_data = {
                "postal_ad_bld": bld_unit.postal_ad_build if bld_unit else None,
                "bld_property_type": bld_unit.bld_property_type if bld_unit else None,
            }

            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            if assessment_unit:
                ward_name = None
                ass_div = getattr(assessment_unit, 'ass_div', None)
                if ass_div:
                    ward = Assessment_Ward_Model.objects.filter(id=ass_div).first()
                    ward_name = ward.ward_name if ward else None
                assessment_unit_data = {
                    "assessment_div": ward_name,
                    "assessment_no": assessment_unit.assessment_no,
                }
            else:
                assessment_unit_data = {
                    "assessment_div": None,
                    "assessment_no": None,
                }

            # Step 5: Combine data and apply field-level filtering
            all_data = {**bld_unit_data, **assessment_unit_data}
            combined_data = {
                field: all_data[field] for field in allowed_fields if field in all_data
            }

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#________________________________________________ Admin_Info (Building) View ____________________________________________________
class Bld_Admin_Info_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            
            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Define permission mapping
            FIELD_PERMISSION_MAP = {
                "administrative_type": 101,
                "pd": 102,
                "dist": 103,
                "dsd": 104,
                "gnd_id": 105,
                "gnd": 105,
                "eletorate": 106,
                "local_auth": 107,
                "ass_div": 108,
                "access_road": 109,
                "bld_name": 110,
                "building_name": 110,
                "postal_ad_build": 111,
                "house_hold_no": 112,
                "bld_property_type": 113,
                "no_floors": 114,
                "registration_date": 155,
                "construction_year": 156,
                "structure_type": 157,
                "condition": 158,
                "wall_type": 121,
            }

            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 3: Get survey rep record
            survey_data = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
            gnd_id = survey_data.gnd_id if survey_data else None

            # Step 4: GND details
            gnd_data = sl_gnd_10m_Model.objects.filter(gid=gnd_id).values("gnd", "dsd", "dist", "pd").first()
            gnd_info = {
                "gnd_id": gnd_id,
                "gnd": gnd_data["gnd"] if gnd_data else None,
                "dsd": gnd_data["dsd"] if gnd_data else None,
                "dist": gnd_data["dist"] if gnd_data else None,
                "pd": gnd_data["pd"] if gnd_data else None,
            }

            # Step 5: Local authority
            elect_data = SL_Elect_LocalAuth_Model.objects.filter(gnd_id=gnd_id).values("eletorate", "local_auth").first()
            gnd_info["eletorate"] = elect_data["eletorate"] if elect_data else None
            gnd_info["local_auth"] = elect_data["local_auth"] if elect_data else None

            # Step 6: Building unit
            build_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            build_unit_data = {
                "access_road": build_unit.access_road if build_unit else None,
                "bld_property_type": build_unit.bld_property_type if build_unit else None,
                "bld_name": build_unit.building_name if build_unit else None,
                "building_name": build_unit.building_name if build_unit else None,
                "postal_ad_build": build_unit.postal_ad_build if build_unit else None,
                "house_hold_no": build_unit.house_hold_no if build_unit else None,
                "no_floors": build_unit.no_floors if build_unit else None,
                "wall_type": build_unit.wall_type if build_unit else None,
                "registration_date": str(build_unit.registration_date) if build_unit and build_unit.registration_date else None,
                "construction_year": build_unit.construction_year if build_unit else None,
                "structure_type": build_unit.structure_type if build_unit else None,
                "condition": build_unit.condition if build_unit else None,
            }

            # Step 7: Assessment
            assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
            assessment_unit_data = {
                "ass_div": getattr(assessment_unit, 'ass_div', None) if assessment_unit else None,
            }

            # Step 8: Static field
            static_data = {
                "administrative_type": "Type01"
            }

            # Combine all
            all_data = {
                **gnd_info,
                **build_unit_data,
                **assessment_unit_data,
                **static_data
            }

            # Apply permission filter
            combined_data = {
                field: all_data[field]
                for field in allowed_fields
                if field in all_data
            }

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Bld_Admin_Info_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "BLD"

            # Define editable field-permission mapping
            FIELD_PERMISSION_MAP = {
                "administrative_type": 101,
                "gnd_id": 105,
                "ass_div": 108,
                "access_road": 109,
                "building_name": 110,
                "postal_ad_build": 111,
                "house_hold_no": 112,
                "bld_property_type": 113,
                "no_floors": 114,
                "wall_type": 121,
                "registration_date": 155,
                "construction_year": 156,
                "structure_type": 157,
                "condition": 158,
            }

            # Step 1: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)

            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Get allowed fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 3: Filter request data to only editable fields
            filtered_data = {
                key: value for key, value in request.data.items()
                if key in allowed_fields
            }

            if not filtered_data:
                return Response({"detail": "Nothing to update."}, status=status.HTTP_200_OK)

            # 4. Update LA_LS_Build_Unit_Model (permission-gated fields)
            build_fields = {"building_name", "access_road", "postal_ad_build", "house_hold_no", "bld_property_type",
                            "no_floors", "wall_type", "registration_date", "construction_year", "structure_type", "condition"}
            build_update_data = {k: v for k, v in filtered_data.items() if k in build_fields}

            build_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            if build_unit and build_update_data:
                original = build_unit.__dict__.copy()
                serializer = LA_LS_Build_Unit_Serializer(build_unit, data=build_update_data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    self.log_changes(user_id, category, su_id, original, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 5. Update Assessment_Model
            if "ass_div" in filtered_data:
                assessment_unit = Assessment_Model.objects.filter(su_id=su_id).first()
                if assessment_unit:
                    original = assessment_unit.__dict__.copy()
                    serializer = Assessment_Serializer(assessment_unit, data={"ass_div": filtered_data["ass_div"]}, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        self.log_changes(user_id, category, su_id, original, serializer.validated_data)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # 6. Update Survey_Rep_DATA_Model
            if "gnd_id" in filtered_data:
                survey_unit = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
                if survey_unit:
                    original = survey_unit.__dict__.copy()
                    serializer = Survey_Rep_DATA_Serializer(survey_unit, data={"gnd_id": filtered_data["gnd_id"]}, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        self.log_changes(user_id, category, su_id, original, serializer.validated_data)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Data updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        """Log changes to History_Spartialunit_Attrib_Model."""
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)

            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:  # Check if the field value has changed
                changes.append(
                    History_Spartialunit_Attrib_Model(
                        user_id=user_id,
                        su_id_id=su_id,
                        category=category,
                        field_name=field,
                        field_value=new_value
                    )
                )
        # Bulk create all changes
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)

#________________________________________________ Overview DATA (Building) View _________________________________________________
class Bld_Overview_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user's roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)
            
            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Define field-permission mapping
            FIELD_PERMISSION_MAP = {
                "dimension_2d_3d": 115,
                "reference_coordinate": 116,
                "area": 117,
                "ext_builduse_type": 118,
                "ext_builduse_sub_type": 119,
                "roof_type": 120,
                "wall_type": 121
            }

            # Step 3: Get allowed fields based on view permissions
            allowed_fields = [
                key for key, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 4: Get Survey Rep data
            survey_instance = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
            survey_data_dict = {
                "dimension_2d_3d": None,
                "area": None,
                "reference_coordinate": None
            }

            if survey_instance:
                serializer = Survey_Rep_DATA_Overview_Serializer(survey_instance)
                survey_data_dict.update(serializer.data)

            # Step 5: Get Building Unit data
            build_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()
            build_unit_data = {
                "ext_builduse_type": build_unit.ext_builduse_type if build_unit else None,
                "ext_builduse_sub_type": build_unit.ext_builduse_sub_type if build_unit else None,
                "roof_type": build_unit.roof_type if build_unit else None,
                "wall_type": build_unit.wall_type if build_unit else None,
            }

            # Step 6: Combine and filter data based on permissions
            all_data = {**survey_data_dict, **build_unit_data}
            combined_data = {
                field: all_data[field]
                for field in allowed_fields
                if field in all_data
            }

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Bld_Overview_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "BLD"

            # Step 1: Get user's role IDs
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)
            
            role_id = user_roles.values_list("role_id", flat=True).first()

            # Step 2: Get related build unit
            build_unit = LA_LS_Build_Unit_Model.objects.filter(su_id=su_id).first()

            # Step 3: Define permission map (edit-only)
            FIELD_PERMISSION_MAP = {
                "area": 117,
                "ext_builduse_type": 118,
                "ext_builduse_sub_type": 119,
                "roof_type": 120,
                "wall_type": 121,
            }

            # Step 4: Determine editable fields for the user
            editable_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 5: Filter update data by editable fields
            update_data = {field: request.data[field] for field in editable_fields if field in request.data}

            # Step 6: Apply build_unit update (area goes to survey_rep below)
            build_unit_fields = {"ext_builduse_type", "ext_builduse_sub_type", "roof_type", "wall_type"}
            build_update = {k: v for k, v in update_data.items() if k in build_unit_fields}
            if build_unit and build_update:
                original_data = build_unit.__dict__.copy()
                serializer = LA_LS_Build_Unit_Serializer(build_unit, data=build_update, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Step 7: Save area to Survey_Rep_DATA_Model if permitted
            if "area" in update_data and update_data["area"] not in (None, ""):
                survey_unit = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
                if survey_unit:
                    try:
                        survey_unit.area = update_data["area"]
                        survey_unit.save(update_fields=["area"])
                    except Exception:
                        pass

            return Response({"detail": "Data updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(
                    History_Spartialunit_Attrib_Model(
                        user_id=user_id,
                        su_id_id=su_id,
                        category=category,
                        field_name=field,
                        field_value=new_value
                    )
                )
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)

#________________________________________________ Utility_Network_Info (Building) View __________________________________________
class Bld_Utility_Network_Info_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user
            user_id = user.id

            # Step 1: Permission map
            FIELD_PERMISSION_MAP = {
                "elec": 122,
                "tele": 123,
                "internet": 124,
                "water_drink": 125,
                "water": 126,
                "drainage": 127,
                "sani_sewer": 128,
                "sani_gully": 129,
                "garbage_dispose": 130,
            }

            # Step 2: Get user role IDs
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)
            
            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 3: Get allowed fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id, permission_id=perm_id, view=True
                ).exists()
            ]

            # Step 4: Get a single utility record
            data = LA_LS_Utinet_BU_Model.objects.filter(su_id=su_id).first()
            if not data:
                return Response({}, status=status.HTTP_200_OK)

            serializer = Bld_Utinet_info_Serializer(data)
            return Response(
                {k: v for k, v in serializer.data.items() if k in allowed_fields},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Bld_Utility_Network_Info_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "BLD"

            # Step 1: Permission map
            FIELD_PERMISSION_MAP = {
                "elec": 122,
                "tele": 123,
                "internet": 124,
                "water_drink": 125,
                "water": 126,
                "drainage": 127,
                "sani_sewer": 128,
                "sani_gully": 129,
                "garbage_dispose": 130,
            }

            # Step 2: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user_id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)
            
            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 3: Determine editable fields
            editable_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 4: Filter incoming data by editable fields
            update_data = {
                field: request.data[field]
                for field in editable_fields
                if field in request.data and request.data[field] not in (None, "")
            }
            if not update_data:
                return Response({"detail": "Nothing to update."}, status=200)

            # Step 5: Get utility network record
            instance = LA_LS_Utinet_BU_Model.objects.filter(su_id=su_id).first()
            if not instance:
                return Response({"error": "No data found for the given su_id."}, status=status.HTTP_404_NOT_FOUND)

            # Step 6: Update utility data
            original_data = instance.__dict__.copy()
            serializer = Bld_Utinet_info_Serializer(instance, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                self.log_changes(user_id, category, su_id, original_data, serializer.validated_data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return Response({"detail": "Data updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        """Log changes to History_Spartialunit_Attrib_Model."""
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(
                    History_Spartialunit_Attrib_Model(
                        user_id=user_id,
                        su_id_id=su_id,
                        category=category,
                        field_name=field,
                        field_value=new_value
                    )
                )
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)


#________________________________________________ Tax_Assessment DATA View (Common for Land and Building) _______________________
class Tax_Assessment_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, su_id):
        try:
            user = request.user

            # Step 1: Get user roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=status.HTTP_403_FORBIDDEN)
            
            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 2: Define permission map
            FIELD_PERMISSION_MAP = {
                # Assessment_Model fields
                "assessment_no": 24,
                "assessment_name": 25,
                "assessment_annual_value": 26,
                "assessment_percentage": 27,
                "ass_out_balance": 29,
                "date_of_valuation": 30,
                "year_of_assessment": 31,
                "property_type": 32,
                # Tax_Info_Model fields
                "tax_annual_value": 33,
                "tax_percentage": 34,
                "tax_date": 36,
                "tax_type": 37,
            }

            # Step 3: Determine allowed fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    view=True
                ).exists()
            ]

            # Step 4: Fetch assessment data
            ass_data = Assessment_Model.objects.filter(su_id=su_id).first()
            assessment_data = {
                "assessment_no": None,
                "assessment_name": None,
                "assessment_annual_value": None,
                "assessment_percentage": None,
                "ass_out_balance": None,
                "date_of_valuation": None,
                "year_of_assessment": None,
                "property_type": None,
            }
            if ass_data:
                assessment_data.update(Assessment_Info_Serializer(ass_data).data)

            # Step 5: Fetch tax info data
            tax_data = Tax_Info_Model.objects.filter(su_id=su_id).first()
            tax_info_data = {
                "tax_annual_value": None,
                "tax_percentage": None,
                "tax_date": None,
                "tax_type": None,
            }
            if tax_data:
                tax_info_data.update(Tax_Info_Serializer(tax_data).data)

            # Step 6: Construct combined response using loop
            combined_data = {}

            for field in allowed_fields:
                if field in assessment_data:
                    combined_data[field] = assessment_data[field]
                elif field in tax_info_data:
                    combined_data[field] = tax_info_data[field]

            # Always return new valuation fields (bypass permission gate)
            combined_data["land_value"]    = ass_data.land_value    if ass_data else None
            combined_data["market_value"]  = ass_data.market_value  if ass_data else None
            combined_data["tax_status"]    = ass_data.tax_status    if ass_data else None

            return Response(combined_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------
class Tax_Assessment_Update_View(APIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, su_id):
        try:
            user = request.user
            user_id = user.id
            category = "Tax-Assess"

            # Step 1: Get roles
            user_roles = User_Roles_Model.objects.filter(users__contains=[user.id])
            if not user_roles.exists():
                return Response({"error": "User has no assigned roles."}, status=403)
            
            role_id = user_roles.values_list('role_id', flat=True).first()

            # Step 2: Define permission mapping
            FIELD_PERMISSION_MAP = {
                "assessment_no": 24,
                "assessment_name": 25,
                "assessment_annual_value": 26,
                "assessment_percentage": 27,
                "ass_out_balance": 29,
                "date_of_valuation": 30,
                "year_of_assessment": 31,
                "property_type": 32,
                "tax_annual_value": 33,
                "tax_percentage": 34,
                "tax_date": 36,
                "tax_type": 37,
                "land_value": 56,
                "market_value": 57,
                "tax_status": 58,
            }

            # Step 3: Determine allowed update fields
            allowed_fields = [
                field for field, perm_id in FIELD_PERMISSION_MAP.items()
                if Role_Permission_Model.objects.filter(
                    role_id=role_id,
                    permission_id=perm_id,
                    edit=True
                ).exists()
            ]

            # Step 4: Filter request data by allowed fields
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

            # Step 5: Update Assessment_Model (create if not exists)
            ass_data = Assessment_Model.objects.filter(su_id=su_id).first()
            if not ass_data:
                ass_data = Assessment_Model(su_id_id=su_id)
                ass_data.save()

            original_assessment_data = ass_data.__dict__.copy()
            assessment_update = {k: v for k, v in update_data.items() if k in Assessment_Info_Serializer.Meta.fields}
            assessment_serializer = Assessment_Info_Serializer(ass_data, data=assessment_update, partial=True)

            if assessment_serializer.is_valid():
                assessment_serializer.save()
                self.log_changes(user_id, category, su_id, original_assessment_data, assessment_serializer.validated_data)
            else:
                return Response(assessment_serializer.errors, status=400)

            # Step 6: Update Tax_Info_Model (create if needed, when tax fields are provided)
            tax_update = {k: v for k, v in update_data.items() if k in Tax_Info_Serializer.Meta.fields}
            tax_info = Tax_Info_Model.objects.filter(su_id=su_id).first()
            if not tax_info and tax_update:
                tax_info = Tax_Info_Model(su_id_id=su_id)
                tax_info.save()
            if tax_info and tax_update:
                original_tax_data = tax_info.__dict__.copy()
                tax_serializer = Tax_Info_Serializer(tax_info, data=tax_update, partial=True)

                if tax_serializer.is_valid():
                    tax_serializer.save()
                    self.log_changes(user_id, category, su_id, original_tax_data, tax_serializer.validated_data)
                else:
                    return Response(tax_serializer.errors, status=400)

            return Response({"detail": "Data updated successfully."}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def log_changes(self, user_id, category, su_id, original_data, updated_data):
        changes = []
        for field, new_value in updated_data.items():
            old_value = original_data.get(field)
            if new_value is None:
                new_value = "deleted"
            if old_value is None:
                old_value = "deleted"
            if old_value != new_value:
                changes.append(History_Spartialunit_Attrib_Model(
                    user_id=user_id,
                    su_id_id=su_id,
                    category=category,
                    field_name=field,
                    field_value=new_value
                ))
        if changes:
            History_Spartialunit_Attrib_Model.objects.bulk_create(changes)



#________________________________________________ LA Spatial Unit View __________________________________________________________ not used
class LA_Spatial_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_Spatial_Unit_Model.objects.all()
    serializer_class = LA_Spatial_Unit_Serializer

#________________________________________________ LA_LS_Land_Unit View __________________________________________________________ not used
class LA_LS_Land_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Land_Unit_Model.objects.all()
    serializer_class = LA_LS_Land_Unit_Serializer

#________________________________________________ LA_LS_Build_Unit View _________________________________________________________ not used
class LA_LS_Build_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Build_Unit_Model.objects.all()
    serializer_class = LA_LS_Build_Unit_Serializer

#________________________________________________ LA_LS_Utinet_BU View __________________________________________________________ not used
class LA_LS_Utinet_BU_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Utinet_BU_Model.objects.all()
    serializer_class = LA_LS_Utinet_BU_Serializer

#________________________________________________ LA_LS_Apt_Unit View ___________________________________________________________
class LA_LS_Apt_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Apt_Unit_Model.objects.all()
    serializer_class = LA_LS_Apt_Unit_Serializer

#________________________________________________ LA_LS_Utinet_AU View __________________________________________________________
class LA_LS_Utinet_AU_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Utinet_AU_Model.objects.all()
    serializer_class = LA_LS_Utinet_AU_Serializer

#________________________________________________ LA_LS_Ols_Polygon_Unit View ___________________________________________________ not used
class LA_LS_Ols_Polygon_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Ols_Polygon_Unit_Model.objects.all()
    serializer_class = LA_LS_Ols_Polygon_Unit_Serializer

#________________________________________________ LA_LS_Ols_PointLine_Unit View _________________________________________________ not used
class LA_LS_Ols_PointLine_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Ols_PointLine_Unit_Model.objects.all()
    serializer_class = LA_LS_Ols_PointLine_Unit_Serializer

#________________________________________________ LA_LS_MyLayer_Polygon_Unit View _______________________________________________ not used
class LA_LS_MyLayer_Polygon_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_MyLayer_Polygon_Unit_Model.objects.all()
    serializer_class = LA_LS_MyLayer_Polygon_Unit_Serializer

#________________________________________________ LA_LS_MyLayer_PointLine_Unit View _____________________________________________ not used
class LA_LS_MyLayer_PointLine_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_MyLayer_PointLine_Unit_Model.objects.all()
    serializer_class = LA_LS_MyLayer_PointLine_Unit_Serializer

#________________________________________________ LA_LS_Utinet_Ols View _________________________________________________________ not used
class LA_LS_Utinet_Ols_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Utinet_Ols_Model.objects.all()
    serializer_class = LA_LS_Utinet_Ols_Serializer

#________________________________________________ LA_LS_Ils_Unit View ___________________________________________________________
class LA_LS_Ils_Unit_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Ils_Unit_Model.objects.all()
    serializer_class = LA_LS_Ils_Unit_Serializer

#________________________________________________ LA_LS_Utinet_Ils View _________________________________________________________
class LA_LS_Utinet_Ils_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_LS_Utinet_Ils_Model.objects.all()
    serializer_class = LA_LS_Utinet_Ils_Serializer

#________________________________________________ LA_Spatial_Unit_Sketch_Ref View _______________________________________________
class LA_Spatial_Unit_Sketch_Ref_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_Spatial_Unit_Sketch_Ref_Model.objects.all()
    serializer_class = LA_Spatial_Unit_Sketch_Ref_Serializer

    def perform_create(self, serializer):
        # Save the instance to generate the `admin_source_id`
        instance = serializer.save()

        # Check if a file was uploaded
        if instance.file_path:
            # Get the current file path
            current_path = instance.file_path.path
            # Construct the new file name
            new_file_name = f"{instance.sketch_ref_id}{os.path.splitext(current_path)[1]}"
            new_file_path = os.path.join(os.path.dirname(current_path), new_file_name)

            # Rename the file
            os.rename(current_path, new_file_path)

            # Update the file path in the instance
            instance.file_path.name = os.path.join('documents/sketch_ref', new_file_name)
            # Save the instance again to update the file path in the database
            instance.save(update_fields=['file_path'])

#________________________________________________ SL_Department View ____________________________________________________________
class SL_Department_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = SL_Department_Model.objects.all()
    serializer_class = SL_Department_Serializer

    def perform_create(self, serializer):
       
        user = self.request.user

        if user.user_type not in ['admin', 'super_admin']:
            raise PermissionDenied("Permission denied. Only admins can access this data.")
        
        serializer.save(org_id=user.org_id)

#------------------------------------------------------------------------------
class SL_Department_List_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SL_Department_Serializer

    def get(self, request, *args, **kwargs):
        user = request.user

        if getattr(user, "user_type", None) not in ["admin", "super_admin"]:
            return Response({"error": "Only super admin and admin users can access this resource"}, status=status.HTTP_403_FORBIDDEN,)

        org_id =user.org_id

        departments = SL_Department_Model.objects.filter(org_id=org_id).order_by('dep_name')
        serializer = self.get_serializer(departments, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
#------------------------------------------------------------------------------
class SL_Department_Update_Delete_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['patch', 'delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = SL_Department_Model.objects.all()
    serializer_class = SL_Department_Serializer

    def destroy(self, request, *args, **kwargs):
        department = self.get_object()

        # Check if any users are assigned to this department
        if User.objects.filter(dep_id=department.dep_id).exists():
            raise serializers.ValidationError("User(s) are already assigned, Change their department first.")

        return super().destroy(request, *args, **kwargs)

#________________________________________________ SL_Org_Area_Parent_Bndry View _________________________________________________
class SL_Org_Area_Parent_Bndry_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = SL_Org_Area_Parent_Bndry_Model.objects.all()
    serializer_class = SL_Org_Area_Parent_Bndry_Serializer

#________________________________________________ SL_Org_Area_Child_Bndry View __________________________________________________
class SL_Org_Area_Child_Bndry_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = SL_Org_Area_Child_Bndry_Model.objects.all()
    serializer_class = SL_Org_Area_Child_Bndry_Serializer

#________________________________________________ History_Spartialunit_Attrib View ______________________________________________ not used
class History_Spartialunit_Attrib_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = History_Spartialunit_Attrib_Model.objects.all()
    serializer_class = History_Spartialunit_Attrib_Serializer

#------------------------------------------------------------------------------
class History_Spartialunit_Attrib_View_Filter_field_name(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, suid):
        name_list = History_Spartialunit_Attrib_Model.objects.filter(su_id=suid).values_list('field_name', flat=True).distinct()
        return Response(name_list)
    
#------------------------------------------------------------------------------
class History_Spartialunit_Attrib_View_Filter_SuId_FieldName(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, suid, fieldname):
        records = History_Spartialunit_Attrib_Model.objects.filter(su_id=suid, field_name=fieldname)
        serializer = History_Spartialunit_Attrib_Serializer(records, many=True)
        return Response(serializer.data)
    
#------------------------------------------------------------------------------
class History_Spartialunit_Attrib_View_Filter_username(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):

        user = request.user
        user_id = user.id

        records = History_Spartialunit_Attrib_Model.objects.filter(user_id=user_id)
        serializer = History_Spartialunit_Attrib_Serializer(records, many=True)
        return Response(serializer.data)
    
#------------------------------------------------------------------------------
class History_Spartialunit_Attrib_View_org(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, suid, fieldname):
        try:
            # Fetch the latest record based on id
            latest_record = History_Spartialunit_Attrib_Model.objects.filter(su_id=suid, field_name=fieldname).latest('id')  # Get the record with the max id
            user_table = User.objects.get(id=latest_record.user_id)
            organization_table = SL_Organization_Model.objects.get(org_id=user_table.org_id)

            return Response({"user_id": latest_record.id, "user_email": user_table.email, "active": user_table.is_active, "org_id": user_table.org_id, "org_level": organization_table.org_level})
        
        except History_Spartialunit_Attrib_Model.DoesNotExist:
            return Response({"detail": "No records found."}, status=404)  # Return an empty response if no record matches
        
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404) # Return an empty response if no record matches
        
        except SL_Organization_Model.DoesNotExist:
            return Response({"detail": "Organization not found."}, status=404) # Return an empty response if no record matches
        
#________________________________________________ LA_Spatial_Source View ________________________________________________________
class LA_Spatial_Source_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_Spatial_Source_Model.objects.all()
    serializer_class = LA_Spatial_Source_Serializer

    def perform_create(self, serializer):
        # Save the instance to generate the `admin_source_id`
        instance = serializer.save()

        # Check if a file was uploaded
        if instance.file_path:
            # Get the current file path
            current_path = instance.file_path.path
            # Construct the new file name
            new_file_name = f"{instance.id}{os.path.splitext(current_path)[1]}"
            new_file_path = os.path.join(os.path.dirname(current_path), new_file_name)

            # Rename the file
            os.rename(current_path, new_file_path)

            # Update the file path in the instance
            instance.file_path.name = os.path.join('documents/spatial_source', new_file_name)
            # Save the instance again to update the file path in the database
            instance.save(update_fields=['file_path'])

#------------------------------------------------------------------------------
class LA_Spatial_Source_Retrive_View(ListCreateAPIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, ver_suid):
        record = LA_Spatial_Source_Model.objects.filter(su_id=ver_suid).order_by('-date_created').first()

        if not record:
            return Response({
                "source_id": None, "spatial_source_type": None,
                "description": None, "date_accept": None,
                "surveyor_name": None, "file_url": None,
            }, status=200)

        serializer = LA_Spatial_Source_Retrive_Serializer(record)
        return Response(serializer.data, status=200)

#------------------------------------------------------------------------------
class LA_Spatial_Source_Update_View(APIView):
    """PATCH — update metadata fields on the most recent LA_Spatial_Source record for a parcel.
    Creates a skeleton record (no file) if none exists yet."""
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    ALLOWED_FIELDS = ('spatial_source_type', 'source_id', 'description', 'date_accept', 'surveyor_name')

    def patch(self, request, su_id):
        try:
            record = LA_Spatial_Source_Model.objects.filter(su_id=su_id).order_by('-date_created').first()
            if not record:
                record = LA_Spatial_Source_Model(su_id_id=su_id, file_path='', approval_status=True)

            update_data = {k: v for k, v in request.data.items() if k in self.ALLOWED_FIELDS and v not in ('', None)}
            if not update_data:
                return Response({"detail": "No updatable fields provided."}, status=200)

            serializer = LA_Spatial_Source_Metadata_Serializer(record, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"detail": "Metadata updated."}, status=200)
            return Response(serializer.errors, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

#________________________________________________ Assessment View _______________________________________________________________ not used
class Assessment_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Assessment_Model.objects.all()
    serializer_class = Assessment_Serializer

#________________________________________________ Tax_Info View _________________________________________________________________ not used
class Tax_Info_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Tax_Info_Model.objects.all()
    serializer_class = Tax_Serializer

#________________________________________________ LA_SP_Fire_Rescue View ________________________________________________________
class LA_SP_Fire_Rescue_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = LA_SP_Fire_Rescue_Model.objects.all()
    serializer_class = LA_SP_Fire_Rescue_Serializer



#________________________________________________ Attrib Image Upload View ______________________________________________________
class Attrib_Image_Upload_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Attrib_Image_Model.objects.all()
    serializer_class = Attrib_Image_Serializer

    def perform_create(self, serializer):
        # Save the instance to generate the `id`
        instance = serializer.save()

        # Check if a file was uploaded
        if instance.file_path:
           
            current_path = instance.file_path.path  # Get the current file path
           
            new_file_name = f"{instance.image_id}{os.path.splitext(current_path)[1]}"  # Construct the new file name
            new_file_path = os.path.join(os.path.dirname(current_path), new_file_name)

            os.rename(current_path, new_file_path)  # Rename the file
            instance.file_path.name = os.path.join('documents/images', new_file_name)  # Update the file path in the instance
            instance.save(update_fields=['file_path'])  # Save the instance again to update the file path in the database

#------------------------------------------------------------------------------
class Attrib_Image_Retrive_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, ver_suid):
        # Get the latest image data by su_id
        latest_image_data = Attrib_Image_Model.objects.filter(su_id=ver_suid).order_by('-date_created').first()
        
        if not latest_image_data:
            return Response({"detail": "No record found for the given su_id."}, status=404)

        # Ensure the file exists on the filesystem
        file_path = latest_image_data.file_path.path
        if not os.path.exists(file_path):
            return Response({"detail": "File not found on the server."}, status=404)

        # Set Content-Type to 'image/png' for PNG files
        content_type = "image/png"
        return FileResponse(open(file_path, 'rb'), content_type=content_type, as_attachment=False)

#------------------------------------------------------------------------------
class Attrib_Image_Delete_View(RetrieveUpdateDestroyAPIView):
    http_method_names = ['delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, su_id):
        try:
            # Find the record by su_id
            instance = Attrib_Image_Model.objects.get(su_id=su_id)

            # Delete the file if it exists
            if instance.file_path and os.path.isfile(instance.file_path.path):
                os.remove(instance.file_path.path)

            # Delete the record from the database
            instance.delete()

            return Response({"message": "Image deleted successfully"}, status=200)

        except Attrib_Image_Model.DoesNotExist:
            return Response({"error": "Image not found"}, status=404)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=500)

#________________________________________________ Messages View _________________________________________________________________
class Messages_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Messages_Model.objects.all()
    serializer_class = Messages_Serializer

#________________________________________________ Inquiries View ________________________________________________________________
class Inquiries_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Inquiries_Model.objects.all()
    serializer_class = Inquiries_Serializer

#________________________________________________ Reminders View ________________________________________________________________
class Reminders_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Reminders_Model.objects.all()
    serializer_class = Reminders_Serializer

#________________________________________________ Tags View _____________________________________________________________________
class Tags_View(ListCreateAPIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    queryset = Tags_Model.objects.all()
    serializer_class = Tags_Serializer

#________________________________________________ Assessment Ward View __________________________________________________________
class Assessment_Ward_View(ListCreateAPIView):
    http_method_names = ['get', 'post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = Assessment_Ward_Serializer

    def get_queryset(self):
        user = self.request.user
        return Assessment_Ward_Model.objects.filter(org_id=user.org_id).order_by('ward_name')

    def perform_create(self, serializer): # For POST data to table
        serializer.save(org_id=self.request.user.org_id)

#------------------------------------------------------------------------------
class Assessment_Ward_Update_View(RetrieveUpdateAPIView):
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = Assessment_Ward_Serializer
    queryset = Assessment_Ward_Model.objects.all()

    def get_queryset(self):
        # Ensure users can only update their own organization's data
        user = self.request.user
        return Assessment_Ward_Model.objects.filter(org_id=user.org_id)

    def perform_update(self, serializer):
        # Optionally enforce org_id consistency
        serializer.save(org_id=self.request.user.org_id)


#________________________________________________ RRR Data Save View ____________________________________________________________
class RRR_Data_Save_View(APIView):
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            user_obj = request.user
            user_id = user_obj.id

            data = request.data.copy()
            file = request.FILES.get('file')

            # Permission gate
            su_id = data.get('su_id')
            if su_id:
                perm_id = _rrr_perm_for_su(su_id)
                if not _has_rrr_perm(user_id, perm_id, 'add'):
                    return _rrr_permission_denied()

            # ✅ Parse "parties" JSON string if needed
            parties = data.get('parties', [])
            if isinstance(parties, str):
                try:
                    parties = json.loads(parties)
                except json.JSONDecodeError:
                    return Response(
                        {"error": "Invalid JSON format for 'parties' field"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 1️⃣ Create BA Unit
            ba_unit = SL_BA_Unit_Model.objects.create(
                su_id_id=data['su_id'],
                sl_ba_unit_name=data['sl_ba_unit_name'],
                sl_ba_unit_type=data['sl_ba_unit_type'],
            )

            # 2️⃣ Create Admin Source (file later)
            admin_source = LA_Admin_Source_Model.objects.create(
                admin_source_type=data['admin_source_type'],
                done_by=user_id,
                user_id=user_id,
                file_path=None
            )

            # 3️⃣ Save File with Renaming
            print(f"[RRR_Save] file received: {bool(file)}, name: {getattr(file, 'name', None)}")
            if file:
                folder_path = 'documents/admin_source'
                new_filename = f"{admin_source.admin_source_id}.pdf"
                full_path = os.path.join(folder_path, new_filename)

                saved_path = default_storage.save(full_path, ContentFile(file.read()))
                print(f"[RRR_Save] default_storage.save returned: {saved_path!r}")

                # FIX: assign string directly — do NOT use .file_path.name = ...
                # (file_path was created as None; FieldFile.name assignment is unreliable)
                admin_source.file_path = saved_path
                admin_source.save()
                print(f"[RRR_Save] admin_source.file_path after save: {admin_source.file_path!r}")
                print(f"[RRR_Save] admin_source.file_path.name: {admin_source.file_path.name!r}")
            else:
                print(f"[RRR_Save] no file in request — file_path will remain None")

            # 4️⃣ Create RRR + Party Roles
            created_rrrs = []
            for party in parties:
                rrr = LA_RRR_Model.objects.create(
                    ba_unit_id=ba_unit,
                    admin_source_id=admin_source,
                    pid_id=party['pid'],
                    rrr_type=party.get('rrr_type'),
                    time_begin=party.get('time_begin') or None,
                    time_end=party.get('time_end') or None,
                    description=party.get('description'),
                )
                created_rrrs.append(rrr.rrr_id)

                Party_Roles_Model.objects.create(
                    pid_id=party['pid'],
                    rrr_id=rrr,
                    party_role_type=party['party_role_type'],
                    share_type=party.get('share_type'),
                    share=party.get('share'),
                    done_by=user_id
                )

            return Response({
                "message": "BA Unit data saved successfully",
                "ba_unit_id": ba_unit.ba_unit_id,
                "admin_source_id": admin_source.admin_source_id,
                "created_rrr_ids": created_rrrs,
                "file_saved_as": admin_source.file_path.name if admin_source.file_path else None
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#_______________________________________________ RRR Add/Remove Extra Document Views ___________________________________________________
class RRR_Add_Document_View(APIView):
    """POST /api/user/rrr-add-document/ba_unit_id=<int>/ — upload an extra document to an existing BA unit."""
    http_method_names = ['post']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, ba_unit_id):
        perm_id = _rrr_perm_for_ba(ba_unit_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()
        try:
            ba_unit = SL_BA_Unit_Model.objects.get(ba_unit_id=ba_unit_id)
        except SL_BA_Unit_Model.DoesNotExist:
            return Response({"error": "BA Unit not found"}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get('file')
        admin_source_type = request.data.get('admin_source_type', 'Document')

        admin_source = LA_Admin_Source_Model.objects.create(
            admin_source_type=admin_source_type,
            done_by=request.user.id,
            user_id=request.user.id,
            file_path=None,
        )

        if file:
            folder_path = 'documents/admin_source'
            new_filename = f"{admin_source.admin_source_id}.pdf"
            saved_path = default_storage.save(
                os.path.join(folder_path, new_filename), ContentFile(file.read())
            )
            admin_source.file_path = saved_path
            admin_source.save()

        doc_link = LA_RRR_Document_Model.objects.create(
            ba_unit=ba_unit,
            admin_source=admin_source,
        )

        file_url = request.build_absolute_uri(
            f"/api/user/admin-source/file/{admin_source.admin_source_id}/"
        ) if admin_source.file_path else None

        return Response({
            "doc_link_id": doc_link.id,
            "admin_source_id": admin_source.admin_source_id,
            "admin_source_type": admin_source.admin_source_type,
            "file_url": file_url,
        }, status=status.HTTP_201_CREATED)


class RRR_Remove_Document_View(APIView):
    """DELETE /api/user/rrr-remove-document/<id>/ — remove an extra document link and its admin source."""
    http_method_names = ['delete']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, doc_link_id):
        try:
            doc_link = LA_RRR_Document_Model.objects.select_related('admin_source', 'ba_unit').get(id=doc_link_id)
        except LA_RRR_Document_Model.DoesNotExist:
            return Response({"error": "Document link not found"}, status=status.HTTP_404_NOT_FOUND)

        perm_id = _rrr_perm_for_ba(doc_link.ba_unit_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()

        admin_source = doc_link.admin_source
        doc_link.delete()
        if admin_source:
            if admin_source.file_path:
                default_storage.delete(admin_source.file_path.name)
            admin_source.delete()

        return Response({"message": "Document removed successfully"}, status=status.HTTP_200_OK)


#------------------------------------------------------------------------------
class RRR_Data_get_View(APIView):
    http_method_names = ['get']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        su_id = request.query_params.get('su_id')
        if not su_id:
            return Response({"error": "su_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Permission gate
        perm_id = _rrr_perm_for_su(su_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'view'):
            return _rrr_permission_denied()

        # get parent_id from Survey_Rep_DATA_Model
        survey_data = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).values("parent_id").first()
        parent_id_value = survey_data["parent_id"] if survey_data else None


        try:
            ba_units = SL_BA_Unit_Model.objects.filter(su_id_id=su_id, status=True).order_by('-ba_unit_id')
            response_data = []

            for ba_unit in ba_units:
                rrrs = LA_RRR_Model.objects.filter(ba_unit_id=ba_unit).select_related('admin_source_id', 'pid')

                admin_sources = []
                seen_admin_source_ids = set()
                rrr_list = []

                for rrr in rrrs:
                    # Primary doc (from LA_RRR_Model.admin_source_id)
                    admin_source = rrr.admin_source_id
                    if admin_source and admin_source.admin_source_id not in seen_admin_source_ids:
                        seen_admin_source_ids.add(admin_source.admin_source_id)
                        file_url = request.build_absolute_uri(
                            f"/api/user/admin-source/file/{admin_source.admin_source_id}/"
                        ) if admin_source.file_path else None
                        admin_sources.append({
                            "admin_source_id": admin_source.admin_source_id,
                            "admin_source_type": admin_source.admin_source_type,
                            "file_url": file_url,
                            "doc_link_id": None,  # primary doc has no link id
                        })

                    # Build rrr_list entry here (inside for rrr loop, NOT inside for doc_link loop)
                    party_role = Party_Roles_Model.objects.filter(rrr_id=rrr).first()
                    party_role_type = party_role.party_role_type if party_role else None

                    restrictions = LA_RRR_Restriction_Model.objects.filter(rrr_id=rrr).values(
                        'id', 'rrr_restriction_type', 'description', 'time_begin', 'time_end'
                    )
                    responsibilities = LA_RRR_Responsibility_Model.objects.filter(rrr_id=rrr).values(
                        'id', 'rrr_responsibility_type', 'description', 'time_begin', 'time_end'
                    )

                    rrr_list.append({
                        "rrr_id": rrr.rrr_id,
                        "pid": rrr.pid_id,
                        "party_name": rrr.pid.party_full_name if rrr.pid else None,
                        "share_type": party_role.share_type if party_role else None,
                        "share": float(party_role.share) if party_role and party_role.share is not None else None,
                        "party_role_type": party_role_type,
                        "rrr_type": rrr.rrr_type,
                        "time_begin": str(rrr.time_begin) if rrr.time_begin else None,
                        "time_end": str(rrr.time_end) if rrr.time_end else None,
                        "description": rrr.description,
                        "restrictions": [
                            {**r, "time_begin": str(r["time_begin"]) if r["time_begin"] else None,
                                  "time_end": str(r["time_end"]) if r["time_end"] else None}
                            for r in restrictions
                        ],
                        "responsibilities": [
                            {**r, "time_begin": str(r["time_begin"]) if r["time_begin"] else None,
                                  "time_end": str(r["time_end"]) if r["time_end"] else None}
                            for r in responsibilities
                        ],
                    })

                # Additional docs (from LA_RRR_Document_Model linked to this BA unit)
                for doc_link in LA_RRR_Document_Model.objects.filter(ba_unit=ba_unit).select_related('admin_source'):
                    as2 = doc_link.admin_source
                    if as2.admin_source_id not in seen_admin_source_ids:
                        seen_admin_source_ids.add(as2.admin_source_id)
                        file_url2 = request.build_absolute_uri(
                            f"/api/user/admin-source/file/{as2.admin_source_id}/"
                        ) if as2.file_path else None
                        admin_sources.append({
                            "admin_source_id": as2.admin_source_id,
                            "admin_source_type": as2.admin_source_type,
                            "file_url": file_url2,
                            "doc_link_id": doc_link.id,
                        })

                response_data.append({
                    "ba_unit_id": ba_unit.ba_unit_id,
                    "sl_ba_unit_name": ba_unit.sl_ba_unit_name,
                    "sl_ba_unit_type": ba_unit.sl_ba_unit_type,
                    "admin_sources": admin_sources,
                    "rrrs": rrr_list
                })

            # return Response(result, status=status.HTTP_200_OK)
            return Response({
                "history_su_id": parent_id_value,
                "records": response_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#________________________________________________ SL_BA_Unit update View ________________________________________________________
class SL_BA_Unit_Update_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch']

    def patch(self, request, ba_unit_id):
        # Permission gate
        perm_id = _rrr_perm_for_ba(ba_unit_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()

        try:
            ba_unit = SL_BA_Unit_Model.objects.get(ba_unit_id=ba_unit_id)
        except SL_BA_Unit_Model.DoesNotExist:
            return Response({"error": "BA Unit not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = SL_BA_Unit_Serializer(ba_unit, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#________________________________________________ RRR Update View (PATCH existing entry) _______________________________________
class RRR_Update_View(APIView):
    """PATCH /api/user/rrr/update/<ba_unit_id>/
    Updates an existing LADM RRR entry:
      - SL_BA_Unit_Model (name, type)
      - LA_RRR_Model (time_begin, time_end, description, rrr_type)
      - Party_Roles_Model (share, share_type, party_role_type)
      - LA_Admin_Source_Model (admin_source_type; optional file replacement)
    """
    http_method_names = ['patch']
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, ba_unit_id):
        # Permission gate
        perm_id = _rrr_perm_for_ba(ba_unit_id)
        if not _has_rrr_perm(request.user.id, perm_id, 'edit'):
            return _rrr_permission_denied()

        try:
            ba_unit = SL_BA_Unit_Model.objects.get(ba_unit_id=ba_unit_id)
        except SL_BA_Unit_Model.DoesNotExist:
            return Response({"error": "BA Unit not found"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data

        # --- Update BA Unit ---
        ba_fields = {}
        if 'sl_ba_unit_name' in data:
            ba_fields['sl_ba_unit_name'] = data['sl_ba_unit_name']
        if 'sl_ba_unit_type' in data:
            ba_fields['sl_ba_unit_type'] = data['sl_ba_unit_type']
        if ba_fields:
            for k, v in ba_fields.items():
                setattr(ba_unit, k, v)
            ba_unit.save()

        # --- Update primary RRR record ---
        rrr = LA_RRR_Model.objects.filter(ba_unit_id=ba_unit).first()
        if rrr:
            rrr_fields = {}
            if 'time_begin' in data:
                rrr_fields['time_begin'] = data['time_begin'] or None
            if 'time_end' in data:
                rrr_fields['time_end'] = data['time_end'] or None
            if 'description' in data:
                rrr_fields['description'] = data['description'] or None
            if 'rrr_type' in data:
                rrr_fields['rrr_type'] = data['rrr_type']
            if rrr_fields:
                for k, v in rrr_fields.items():
                    setattr(rrr, k, v)
                rrr.save()

            # --- Update party role ---
            party_role = Party_Roles_Model.objects.filter(rrr_id=rrr).first()
            if party_role:
                pr_fields = {}
                if 'share' in data:
                    pr_fields['share'] = data['share']
                if 'share_type' in data:
                    pr_fields['share_type'] = data['share_type']
                if 'party_role_type' in data:
                    pr_fields['party_role_type'] = data['party_role_type']
                if pr_fields:
                    for k, v in pr_fields.items():
                        setattr(party_role, k, v)
                    party_role.save()

            # --- Update admin source type / replace file ---
            admin_source = rrr.admin_source_id
            if admin_source:
                if 'admin_source_type' in data:
                    admin_source.admin_source_type = data['admin_source_type']
                    admin_source.save()

                file = request.FILES.get('file')
                if file:
                    if admin_source.file_path:
                        try:
                            default_storage.delete(admin_source.file_path.name)
                        except Exception:
                            pass
                    folder_path = 'documents/admin_source'
                    new_filename = f"{admin_source.admin_source_id}.pdf"
                    saved_path = default_storage.save(
                        os.path.join(folder_path, new_filename), ContentFile(file.read())
                    )
                    admin_source.file_path = saved_path
                    admin_source.save()

        return Response({"message": "RRR entry updated successfully"}, status=status.HTTP_200_OK)








#________________________________________________ Import Vector DATA View _______________________________________________________
# class Import_VectorDATA_View(APIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def post(self, request, *args, **kwargs):
       
#         geometries = request.data.get("geometries")
#         if not isinstance(geometries, list):
#             return Response({"error": "Expected 'geometries' as a list"}, status=status.HTTP_400_BAD_REQUEST)

#         # Convert list of geometries into GeometryCollection
#         geometry_collection = {
#             "type": "GeometryCollection",
#             "geometries": geometries
#         }

#         # Construct GeoJSON Feature expected by serializer
#         feature = {
#             "type": "Feature",
#             "geometry": geometry_collection,
#             "properties": {
#                 "user_id": request.data.get("user_id"),
#                 "dataset_name": request.data.get("dataset_name"),
#                 "layer_id": request.data.get("layer_id")
#             }
#         }

#         serializer = Import_VectorDATA_Serializer(data=feature)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         else:
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#------------------------------------------------------------------------------
# class Import_VectorDATA_List_View(ListAPIView):
#     http_method_names = ['get']
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [TokenAuthentication]

#     serializer_class = Import_VectorDATA_List_Serializer
    
#     def get_queryset(self):
#         return Import_VectorDATA_Model.objects.filter(user_id=self.request.user.id)

#------------------------------------------------------------------------------
# class Import_VectorDATA_View_Filter(RetrieveAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     # def get(self, request, Import_ID):
#     #     vector_data = Import_VectorDATA_Model.objects.filter(id=Import_ID)
#     #     serializer = Import_VectorDATA_Serializer(vector_data, many=True)
#     #     return Response(serializer.data)

#     serializer_class = Import_VectorDATA_Serializer
#     queryset = Import_VectorDATA_Model.objects.all()
#     lookup_field = 'id'

#------------------------------------------------------------------------------
# class Import_VectorDATA_View_delete(RetrieveUpdateDestroyAPIView):
#     http_method_names = ['delete']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = Import_VectorDATA_Model.objects.all()
#     serializer_class = Import_VectorDATA_Serializer

#     # custom message return after successful DELETE
#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         self.perform_destroy(instance)
#         return Response({"detail": "Record deleted successfully."}, status=status.HTTP_200_OK)

#________________________________________________ Import Geotif DATA View _______________________________________________________
# class Upload_RasterData_View(APIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def post(self, request, format=None):

#         # print("Incoming POST request:")
#         # print("User:", request.user)
#         # print("Headers:", request.headers)
#         # print("Data:", request.data)
#         # print("Files:", request.FILES)


#         file_obj = request.FILES.get('file_path')
#         if file_obj:
#             ext = os.path.splitext(file_obj.name)[1].lower()
#             if ext not in ['.tif', '.tiff']:
#                 return Response({"error": "Only .tif and .tiff files are allowed."}, status=status.HTTP_400_BAD_REQUEST)

#         data = request.data.copy()
#         data['user_id'] = request.user.id  # Automatically save user_id
#         data['layer_id'] = 93

#         serializer = Import_RasterData_Serializer(data=data)
#         if serializer.is_valid():
#             instance = serializer.save()
            
#             # Rename file to match record ID
#             if instance.file_path:
#                 old_path = instance.file_path.path
#                 ext = os.path.splitext(old_path)[1]
#                 new_filename = f"{instance.id}{ext}"
#                 new_path = os.path.join(settings.MEDIA_ROOT, 'documents/raster_data', new_filename)

#                 os.rename(old_path, new_path)

#                 instance.file_path.name = os.path.join('documents/raster_data', new_filename)
#                 instance.save(update_fields=['file_path'])

#             return Response(Import_RasterData_Serializer(instance).data, status=status.HTTP_201_CREATED)
        
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#------------------------------------------------------------------------------
# class RasterData_List_View(ListAPIView):
#     http_method_names = ['get']
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [TokenAuthentication]

#     serializer_class = RasterData_List_Serializer
    
#     def get_queryset(self):
#         return Import_RasterData_Model.objects.filter(user_id=self.request.user.id)

#------------------------------------------------------------------------------
# class Raster_Meta_data_View(APIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, id):
#         try:
#             instance = Import_RasterData_Model.objects.get(id=id, user_id=request.user.id)
#             serializer = Import_RasterData_Serializer(instance)
#             return Response(serializer.data)
#         except Import_RasterData_Model.DoesNotExist:
#             raise Http404("Record not found.")
        
#------------------------------------------------------------------------------
# class Raster_File_Download_View(APIView):
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, id):
#         try:
#             instance = Import_RasterData_Model.objects.get(id=id, user_id=request.user.id)
#             if not instance.file_path:
#                 raise Http404("File not found.")
#             return FileResponse(open(instance.file_path.path, 'rb'), content_type='image/tiff', filename=instance.file_path.name)
#         except Import_RasterData_Model.DoesNotExist:
#             raise Http404("Record not found.")
#         except FileNotFoundError:
#             raise Http404("File not found on server.")


#________________________________________________ SL Rights & Liabilities View __________________________________________________
# class SL_Rights_Liabilities_View(ListCreateAPIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = SL_Rights_Liabilities_Model.objects.all()
#     serializer_class = SL_Rights_Liabilities_Serializer

#________________________________________________ Admin Annotation View _________________________________________________________
# class Admin_Annotation_View(ListCreateAPIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = Admin_Annotation_Model.objects.all()
#     serializer_class = Admin_Annotation_Serializer

#________________________________________________ SL Admin Restrict View ________________________________________________________
# class SL_Admin_Restrict_View(ListCreateAPIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = SL_Admin_Restrict_Model.objects.all()
#     serializer_class = SL_Admin_Restrict_Serializer

#________________________________________________ LA Mortgage View ______________________________________________________________
# class LA_Mortgage_View(ListCreateAPIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = LA_Mortgage_Model.objects.all()
#     serializer_class = LA_Mortgage_Serializer

#________________________________________________ SL Rights View ________________________________________________________________
# class SL_Rights_View(ListCreateAPIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = SL_Rights_Model.objects.all()
#     serializer_class = SL_Rights_Serializer

#________________________________________________ LA Responsibility View ________________________________________________________
# class LA_Responsibility_View(ListCreateAPIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = LA_Responsibility_Model.objects.all()
#     serializer_class = LA_Responsibility_Serializer

#________________________________________________ LA RRR View ___________________________________________________________________
# class LA_RRR_View(ListCreateAPIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = LA_RRR_Model.objects.all()
#     serializer_class = LA_RRR_Serializer

#________________________________________________ LA Administrative View ________________________________________________________
# class LA_Admin_Source_View(ListCreateAPIView):
#     http_method_names = ['post']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     queryset = LA_Admin_Source_Model.objects.all()
#     serializer_class = LA_Admin_Source_Serializer

#     def perform_create(self, serializer):
#         with transaction.atomic():
#             instance = serializer.save()  # Save instance to generate `admin_source_id`

#             # print("Received JSON data:", self.request.data)

#             # Handle file renaming if a file was uploaded
#             if instance.file_path:
#                 current_path = instance.file_path.path
#                 new_file_name = f"{instance.admin_source_id}{os.path.splitext(current_path)[1]}"
#                 new_file_path = os.path.join(os.path.dirname(current_path), new_file_name)
#                 os.rename(current_path, new_file_path)

#                 # Update the file path in the instance
#                 instance.file_path.name = os.path.join('documents/admin_source', new_file_name)
#                 instance.save(update_fields=['file_path'])
            
#             # Extract additional data from request
#             request_data = self.request.data
#             su_id = request_data.get('su_id')
#             la_ba_unit_type = request_data.get('la_ba_unit_type')
#             code = request_data.get('code')

#             if not su_id or not la_ba_unit_type or not code:
#                 raise serializers.ValidationError({'error': 'su_id, la_ba_unit_type, and code are required.'})

#             # Create a new LA_RRR_Model record
#             la_rrr_instance = LA_RRR_Model.objects.create(
#                 su_id=su_id,
#                 admin_source_id=instance,  # Link the newly created LA_Admin_Source_Model instance
#                 ba_unit_id=instance.ba_unit_id,  # Use the same ba_unit_id from the admin source
#                 la_ba_unit_type=la_ba_unit_type,
#                 code=code,
#                 user_id=instance.user_id
#             )

#             if code == 'la_rrr_sl_rights':
#                 rights_list = request_data.get('rights', [])

#                 if not rights_list:
#                     raise serializers.ValidationError({'error': 'At least one rights entry is required for SL_Rights_Model'})

#                 for right in rights_list:
#                     right_type = right.get('right_type')
#                     description = right.get('description')
#                     time_spec = right.get('time_spec', None)
#                     date_start = right.get('date_start')
#                     date_end = right.get('date_end')
#                     share_type = right.get('share_type')
#                     share = right.get('share')
#                     party_id = right.get('party')  # Ensure this is the ID of an existing Party_Model record
#                     remark = right.get('remark', None)

#                     if not party_id:
#                         raise serializers.ValidationError({'error': 'party is required for each SL_Rights_Model entry'})

#                     # Create an SL_Rights_Model record for each right
#                     SL_Rights_Model.objects.create(
#                         rrr_id=la_rrr_instance,  # Link to LA_RRR_Model instance
#                         share=share,
#                         share_type=share_type,
#                         right_type=right_type,
#                         party_id=party_id,
#                         description=description,
#                         time_spec=time_spec,
#                         date_start=date_start,
#                         date_end=date_end,
#                         remark=remark,
#                         status=True  # Default status
#                     )

#________________________________________________ (Land Tenure) Ownership Rights View (Common for Land and Building) ____________
# class Ownership_Rights_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, ver_suid, *args, **kwargs):
#         # Step 1: Get ba_unit_id from SL_BA_Unit_Model
#         ba_unit_record = SL_BA_Unit_Model.objects.filter(su_id=ver_suid).values('ba_unit_id').first()
#         if not ba_unit_record:
#             return Response({"detail": "No record found in SL_BA_Unit"}, status=404)
        
#         ba_unit_id = ba_unit_record['ba_unit_id']

#         # Step 2: Use ba_unit_id to get admin_source_id, reference_no, and file_path from LA_Admin_Source_Model
#         admin_source_record = LA_Admin_Source_Model.objects.filter(ba_unit_id=ba_unit_id, admin_source_type__in=ADMIN_SOURCE_TYPES).order_by('-acceptance_date').first()

#         if not admin_source_record:
#             return Response({"detail": "No record found in LA_Admin_Source"}, status=404)

#         admin_source_serializer = Ownership_Rights_Serializer(admin_source_record, context={"request": request})  # Pass request context for building absolute URLs

#         admin_source_data = admin_source_serializer.data
#         admin_source_id = admin_source_record.admin_source_id

#         # Step 3: Use ba_unit_id to get rrr_id from LA_RRR_Model
#         rrr_record = LA_RRR_Model.objects.filter(ba_unit_id=ba_unit_id, admin_source_id=admin_source_id, code="la_rrr_sl_rights").values('rrr_id').first()
#         if not rrr_record:
#             return Response({"detail": "No record found in LA_RRR"}, status=404)

#         rrr_id = rrr_record['rrr_id']

#         # Step 4: Get the record in SL_Rights_Model with the maximum share value
#         max_share_record = SL_Rights_Model.objects.filter(rrr_id=rrr_id).order_by('-share').values('share', 'right_type', 'time_spec', 'date_start', 'date_end', 'party').first()
#         if not max_share_record:
#             return Response({"detail": "No records found in SL_Rights_Model."}, status=404)

#         # Step 5: Get the related Party_Model data using the party_id from max_share_record
#         party_record = Party_Model.objects.filter(pid=max_share_record['party']).values("party_name", 'la_party_type', 'sl_party_type', 'ext_pid_type', 'ext_pid', 'pmt_address', 'tp').first()
#         if not party_record:
#             return Response({"detail": "No record found in Party_Model."}, status=404)

#         # Combine the data from max_share_record, party_record, and admin_source_data
#         response_data = {
#             'share': max_share_record['share'],
#             'right_type': max_share_record['right_type'],
#             'time_spec': max_share_record['time_spec'],
#             'date_start': max_share_record['date_start'],
#             'date_end': max_share_record['date_end'],
#             'party_info': party_record,  # Include party details in the response
#             'admin_source_info': admin_source_data  # Include serialized admin source details with file URL
#         }

#         return Response([response_data])

#________________________________________________ Admin_Sources_RRR_Rights View _________________________________________________
# class LA_Admin_Source_RRR_Rights_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     serializer_class = LA_Admin_Source_RRR_Rights_Serializer
    

#     def get(self, request, su_id, *args, **kwargs):

#         ba_unit_record = SL_BA_Unit_Model.objects.filter(su_id=su_id).values('ba_unit_id').first()
#         if not ba_unit_record:
#             return Response({"detail": "No record found in SL_BA_Unit"}, status=404)


#         ba_unit_id = ba_unit_record['ba_unit_id']

#         admin_source_records = LA_Admin_Source_Model.objects.filter(
#             ba_unit_id=ba_unit_id, 
#             admin_source_type__in=ADMIN_SOURCE_TYPES, status=True).order_by('-acceptance_date')

#         if not admin_source_records.exists():
#             return Response({"detail": "No matching records found in LA_Admin_Source"}, status=404)

#         serializer = self.serializer_class(admin_source_records, many=True, context={"request": request})
#         return Response(serializer.data)


#________________________________________________ SL Rights Activity View _______________________________________________________
# class SL_Rights_Activity_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, userID, *args, **kwargs):
#         # Step 1: Get all rrr_id and su_id pairs for the given username and code
#         rrr_records = LA_RRR_Model.objects.filter(user_id=userID, code='la_rrr_sl_rights').values('rrr_id', 'su_id')
#         if not rrr_records:
#             return Response({"detail": "No record found in LA_RRR"}, status=404)

#         # Step 2: Prepare a mapping of rrr_id to su_id
#         rrr_id_to_su_id = {record['rrr_id']: record['su_id'] for record in rrr_records}

#         # Step 3: Query SL_Rights_Model with the rrr_id list
#         rrr_ids = rrr_id_to_su_id.keys()
#         rights_records = SL_Rights_Model.objects.filter(rrr_id__in=rrr_ids).order_by('-id')
#         if not rights_records.exists():
#             return Response({"detail": "No records found in SL_Rights"}, status=404)

#         # Step 4: Serialize the data and add su_id
#         output_data = SL_Rights_Activity_Serializer(rights_records, many=True).data
#         for record in output_data:
#             record['su_id'] = rrr_id_to_su_id.get(record['rrr_id'])

#         return Response(output_data, status=200)
    
#________________________________________________ LA Mortgage Activity View _____________________________________________________
# class LA_Mortgage_Activity_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, userID, *args, **kwargs):
#         # Step 1: Get all rrr_id and su_id pairs for the given username and code
#         rrr_records = LA_RRR_Model.objects.filter(user_id=userID, code='la_rrr_la_mortgage').values('rrr_id', 'su_id')
#         if not rrr_records:
#             return Response({"detail": "No record found in LA_RRR"}, status=404)

#         # Step 2: Prepare a mapping of rrr_id to su_id
#         rrr_id_to_su_id = {record['rrr_id']: record['su_id'] for record in rrr_records}

#         # Step 3: Query LA_Mortgage_Model with the rrr_id list
#         rrr_ids = rrr_id_to_su_id.keys()
#         mortgage_records = LA_Mortgage_Model.objects.filter(rrr_id__in=rrr_ids).order_by('-id')
        
#         if not mortgage_records.exists():
#             return Response({"detail": "No records found in LA_Mortgage"}, status=404)

#         # Step 4: Add su_id to each rights record
#         output_data = LA_Mortgage_Activity_Serializer(mortgage_records, many=True).data
#         for record in output_data:
#             record['su_id'] = rrr_id_to_su_id.get(record['rrr_id'])

#         return Response(output_data, status=200)

#________________________________________________ LA Responsibility Activity View _______________________________________________
# class LA_Responsibility_Activity_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, userID, *args, **kwargs):
#         # Step 1: Get all rrr_id and su_id pairs for the given username and code
#         rrr_records = LA_RRR_Model.objects.filter(user_id=userID, code='la_rrr_la_responsibility').values('rrr_id', 'su_id')
#         if not rrr_records:
#             return Response({"detail": "No record found in LA_RRR"}, status=404)

#         # Step 2: Prepare a mapping of rrr_id to su_id
#         rrr_id_to_su_id = {record['rrr_id']: record['su_id'] for record in rrr_records}

#         # Step 3: Query LA_Responsibility_Model with the rrr_id list
#         rrr_ids = rrr_id_to_su_id.keys()
#         responsibility_records = LA_Responsibility_Model.objects.filter(rrr_id__in=rrr_ids).order_by('-id')
        
#         if not responsibility_records.exists():
#             return Response({"detail": "No records found in LA_Responsibility"}, status=404)

#         # Step 4: Add su_id to each rights record
#         output_data = LA_Responsibility_Activity_Serializer(responsibility_records, many=True).data
#         for record in output_data:
#             record['su_id'] = rrr_id_to_su_id.get(record['rrr_id'])

#         return Response(output_data, status=200)

#________________________________________________ Admin Annotation Activity View ________________________________________________
# class Admin_Annotation_Activity_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, userID, *args, **kwargs):
#         # Step 1: Get all rrr_id and su_id pairs for the given username and code
#         rrr_records = LA_RRR_Model.objects.filter(user_id=userID, code='la_rrr_admin_annotation').values('rrr_id', 'su_id')
#         if not rrr_records:
#             return Response({"detail": "No record found in LA_RRR"}, status=404)

#         # Step 2: Prepare a mapping of rrr_id to su_id
#         rrr_id_to_su_id = {record['rrr_id']: record['su_id'] for record in rrr_records}

#         # Step 3: Query Admin_Annotation_Model with the rrr_id list
#         rrr_ids = rrr_id_to_su_id.keys()
#         annotation_records = Admin_Annotation_Model.objects.filter(rrr_id__in=rrr_ids).order_by('-id')

#         if not annotation_records.exists():
#             return Response({"detail": "No records found in Admin_Annotation"}, status=404)

#         # Step 4: Add su_id to each rights record
#         output_data = Admin_Annotation_Activity_Serializer(annotation_records, many=True).data
#         for record in output_data:
#             record['su_id'] = rrr_id_to_su_id.get(record['rrr_id'])

#         return Response(output_data, status=200)
    
#________________________________________________ SL Admin Restrict Activity View _______________________________________________
# class SL_Admin_Restrict_Activity_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, userID, *args, **kwargs):
#         # Step 1: Get all rrr_id and su_id pairs for the given username and code
#         rrr_records = LA_RRR_Model.objects.filter(user_id=userID, code='la_rrr_sl_admin_restrict').values('rrr_id', 'su_id')
#         if not rrr_records:
#             return Response({"detail": "No record found in LA_RRR"}, status=404)

#         # Step 2: Prepare a mapping of rrr_id to su_id
#         rrr_id_to_su_id = {record['rrr_id']: record['su_id'] for record in rrr_records}

#         # Step 3: Query SL_Admin_Restrict_Model with the rrr_id list
#         rrr_ids = rrr_id_to_su_id.keys()
#         admin_restrict_records = SL_Admin_Restrict_Model.objects.filter(rrr_id__in=rrr_ids).order_by('-id')
        
#         if not admin_restrict_records.exists():
#             return Response({"detail": "No records found in SL_Admin_Restrict"}, status=404)

#         # Step 4: Add su_id to each rights record
#         output_data = SL_Admin_Restrict_Activity_Serializer(admin_restrict_records, many=True).data
#         for record in output_data:
#             record['su_id'] = rrr_id_to_su_id.get(record['rrr_id'])

#         return Response(output_data, status=200)

#________________________________________________ SL Rights & Liabilities Activity View _________________________________________
# class SL_Rights_Liabilities_Activity_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, userID, *args, **kwargs):
#         # Step 1: Get all rrr_id and su_id pairs for the given username and code
#         rrr_records = LA_RRR_Model.objects.filter(user_id=userID, code='la_rrr_sl_rights_lib').values('rrr_id', 'su_id')
#         if not rrr_records:
#             return Response({"detail": "No record found in LA_RRR"}, status=404)

#         # Step 2: Prepare a mapping of rrr_id to su_id
#         rrr_id_to_su_id = {record['rrr_id']: record['su_id'] for record in rrr_records}

#         # Step 3: Query SL_Rights_Liabilities_Model with the rrr_id list
#         rrr_ids = rrr_id_to_su_id.keys()
#         sl_rights_lib_records = SL_Rights_Liabilities_Model.objects.filter(rrr_id__in=rrr_ids).order_by('-id')

#         if not sl_rights_lib_records.exists():
#             return Response({"detail": "No records found in SL_Rights_Liabilities"}, status=404)

#         # Step 4: Add su_id to each rights record
#         output_data = SL_Rights_Liabilities_Activity_Serializer(sl_rights_lib_records, many=True).data
#         for record in output_data:
#             record['su_id'] = rrr_id_to_su_id.get(record['rrr_id'])

#         return Response(output_data, status=200)
    
#________________________________________________ Ownership History View ________________________________________________________
# class Ownership_History_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, ver_suid):
#         # Step 1: Fetch rrr_id and admin_source_id
#         rrr_records = LA_RRR_Model.objects.filter(su_id=ver_suid, code='la_rrr_sl_rights').values('rrr_id', 'admin_source_id')

#         if not rrr_records.exists():
#             return Response({"message": "No records found for the given su_id."}, status=404)

#         # Step 2: Initialize response data
#         combined_data = []

#         for record in rrr_records:
#             rrr_id = record['rrr_id']
#             admin_source_id = record['admin_source_id']

#             # Step 3: Fetch rights data using SL_Rights_History_Serializer
#             rights_queryset = SL_Rights_Model.objects.filter(rrr_id=rrr_id)
#             rights_serializer = SL_Rights_History_Serializer(rights_queryset, many=True)

#             if not rights_queryset.exists():
#                 return Response({"message": "No records found for the given su_id."}, status=404)

#             # Step 4: Fetch the acceptance_date via Admin_Source_Ownership_History_Serializer
#             admin_source_queryset = LA_Admin_Source_Model.objects.filter(admin_source_id=admin_source_id).first()
#             admin_source_serializer = LA_Admin_Source_Serializer(admin_source_queryset)
#             acceptance_date = admin_source_serializer.data.get('acceptance_date')

#             # Step 5: Combine serialized mortgage data with acceptance_date
#             for rights in rights_serializer.data:
#                 combined_entry = {
#                     **rights,  # Include all serialized fields from LA_Mortgage_Serializer
#                     "acceptance_date": acceptance_date,
#                 }
#                 combined_data.append(combined_entry)

#         return Response(combined_data, status=200)

#________________________________________________ Mortgage History View _________________________________________________________
# class Mortgage_History_View(ListCreateAPIView):
#     http_method_names = ['get']
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, ver_suid):
#         # Step 1: Fetch rrr_id and admin_source_id
#         rrr_records = LA_RRR_Model.objects.filter(su_id=ver_suid, code='la_rrr_la_mortgage').values('rrr_id', 'admin_source_id')

#         if not rrr_records.exists():
#             return Response({"message": "No records found for the given su_id."}, status=404)

#         # Step 2: Initialize response data
#         combined_data = []

#         for record in rrr_records:
#             rrr_id = record['rrr_id']
#             admin_source_id = record['admin_source_id']

#             # Step 3: Fetch mortgage data using LA_Mortgage_Serializer
#             mortgage_queryset = LA_Mortgage_Model.objects.filter(rrr_id=rrr_id)
#             mortgage_serializer = LA_Mortgage_Hirtory_Serializer(mortgage_queryset, many=True)

#             if not mortgage_queryset.exists():
#                 return Response({"message": "No records found for the given su_id."}, status=404)

#             # Step 4: Fetch the acceptance_date via Admin_Source_Ownership_History_Serializer
#             admin_source_queryset = LA_Admin_Source_Model.objects.filter(admin_source_id=admin_source_id).first()
#             admin_source_serializer = LA_Admin_Source_Serializer(admin_source_queryset)
#             acceptance_date = admin_source_serializer.data.get('acceptance_date')

#             # Step 5: Combine serialized mortgage data with acceptance_date
#             for mortgage in mortgage_serializer.data:
#                 combined_entry = {
#                     **mortgage,  # Include all serialized fields from LA_Mortgage_Serializer
#                     "acceptance_date": acceptance_date,
#                 }
#                 combined_data.append(combined_entry)

#         return Response(combined_data, status=200)


# __ Dynamic Attribute Views __

class Dynamic_Attribute_View(APIView):
    """
    GET  /dynamic-attribute/?su_id=<id>&section_key=<key>   – list attributes
    POST /dynamic-attribute/  { su_id, section_key, label }  – create attribute
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        su_id = request.query_params.get('su_id')
        section_key = request.query_params.get('section_key')
        if not su_id or not section_key:
            return Response({"error": "su_id and section_key are required."}, status=400)
        attrs = Dynamic_Attribute_Model.objects.filter(su_id=su_id, section_key=section_key, status=True)
        serializer = DynamicAttribute_Serializer(attrs, many=True)
        return Response(serializer.data, status=200)

    def post(self, request):
        su_id = request.data.get('su_id')
        section_key = request.data.get('section_key')
        label = request.data.get('label')
        if not su_id or not section_key or not label:
            return Response({"error": "su_id, section_key, and label are required."}, status=400)
        attr = Dynamic_Attribute_Model.objects.create(
            su_id=su_id,
            section_key=section_key,
            label=label,
            value=None,
            created_by=request.user.id,
        )
        return Response(DynamicAttribute_Serializer(attr).data, status=201)


class Dynamic_Attribute_Value_View(APIView):
    """
    POST /dynamic-attribute-value/  { attribute_id, su_id, value }  – update value
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        attribute_id = request.data.get('attribute_id')
        su_id = request.data.get('su_id')
        value = request.data.get('value', '')
        if not attribute_id or not su_id:
            return Response({"error": "attribute_id and su_id are required."}, status=400)
        attr = Dynamic_Attribute_Model.objects.filter(id=attribute_id, su_id=su_id, status=True).first()
        if not attr:
            return Response({"error": "Attribute not found."}, status=404)
        attr.value = value
        attr.save()
        return Response(DynamicAttribute_Serializer(attr).data, status=200)


class Dynamic_Attribute_Delete_View(APIView):
    """
    DELETE /dynamic-attribute/<id>/
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        attr = Dynamic_Attribute_Model.objects.filter(id=pk, status=True).first()
        if not attr:
            return Response({"error": "Attribute not found."}, status=404)
        attr.status = False
        attr.save()
        return Response({"detail": "Attribute deleted."}, status=200)
