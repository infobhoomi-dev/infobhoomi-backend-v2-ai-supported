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
