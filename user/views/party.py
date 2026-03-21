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
        possible_match = Party_Model.objects.filter(other_reg__contains=[ext_pid]).first()

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
