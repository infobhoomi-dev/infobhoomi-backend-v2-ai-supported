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
