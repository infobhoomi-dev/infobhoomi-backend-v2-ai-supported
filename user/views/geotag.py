from django.contrib.gis.geos import Point
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import GeoTag_Model


def _user_name(user):
    full_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    return full_name or getattr(user, "email", None) or getattr(user, "username", "")


def _tag_row(tag):
    return {
        "id": tag.id,
        "tag_type": tag.tag_type,
        "label": tag.label,
        "note": tag.note,
        "longitude": tag.geom.x if tag.geom else None,
        "latitude": tag.geom.y if tag.geom else None,
        "status": tag.status,
        "deleted": tag.deleted,
        "created_by": tag.created_by,
        "created_by_name": tag.created_by_name,
        "date_created": tag.date_created,
        "date_modified": tag.date_modified,
    }


class GeoTag_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tags = GeoTag_Model.objects.filter(deleted=False)
        org_id = getattr(request.user, "org_id", None)
        if org_id:
            tags = tags.filter(org_id=org_id)
        return Response([_tag_row(tag) for tag in tags])

    def post(self, request):
        data = request.data or {}
        try:
            longitude = float(data.get("longitude"))
            latitude = float(data.get("latitude"))
        except (TypeError, ValueError):
            return Response({"error": "longitude and latitude are required."}, status=400)

        tag_type = data.get("tag_type") or "other"
        label = data.get("label") or dict(GeoTag_Model.TAG_CHOICES).get(tag_type, "Other")
        tag = GeoTag_Model.objects.create(
            tag_type=tag_type,
            label=label,
            note=data.get("note") or None,
            geom=Point(longitude, latitude, srid=4326),
            org_id=getattr(request.user, "org_id", None),
            created_by=request.user.id,
            created_by_name=_user_name(request.user),
        )
        return Response(_tag_row(tag), status=201)


class GeoTag_Detail_View(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, tag_id):
        tag = GeoTag_Model.objects.filter(id=tag_id, deleted=False).first()
        if not tag:
            return Response({"error": "GeoTag not found."}, status=404)
        data = request.data or {}
        if "status" in data:
            tag.status = bool(data.get("status"))
        if "note" in data:
            tag.note = data.get("note") or None
        tag.save(update_fields=["status", "note", "date_modified"])
        return Response(_tag_row(tag))

    def delete(self, request, tag_id):
        tag = GeoTag_Model.objects.filter(id=tag_id, deleted=False).first()
        if not tag:
            return Response({"error": "GeoTag not found."}, status=404)
        tag.deleted = True
        tag.status = False
        tag.save(update_fields=["deleted", "status", "date_modified"])
        return Response({"detail": "GeoTag deleted."})
