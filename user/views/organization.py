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
