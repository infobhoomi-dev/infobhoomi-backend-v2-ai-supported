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
