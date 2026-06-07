# user/signals.py
"""
Django signals for InfoBhoomi — LADM parcel lifecycle.

pre_delete on LA_Spatial_Unit_Model:
    Snapshots all attribute sub-tables to Parcel_Delete_Archive_Model
    before the CASCADE deletes fire.  This gives a complete recoverable
    record of every field that was set on the parcel.

Note: SL_BA_Unit_Model uses on_delete=PROTECT so a parcel that still
has a title/RRR record CANNOT be deleted at all — the signal only fires
when the delete is genuinely possible.
"""

import decimal

from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver


def _snapshot(instance):
    """
    Convert a Django model instance to a plain JSON-serialisable dict.
    Handles: datetime, date, Decimal, GEOSGeometry (→ WKT), and related-
    manager objects (skipped).  Returns None if instance is None.
    """
    if instance is None:
        return None

    result = {}
    for field in instance._meta.concrete_fields:
        value = getattr(instance, field.attname, None)

        if value is None:
            result[field.name] = None
        elif isinstance(value, decimal.Decimal):
            result[field.name] = float(value)
        elif hasattr(value, 'isoformat'):          # datetime / date
            result[field.name] = value.isoformat()
        elif hasattr(value, 'wkt'):                # GEOSGeometry
            result[field.name] = value.wkt
        else:
            # For FK fields attname ends with _id; use the raw DB column value
            result[field.name] = value

    return result


def _safe_get_oto(related_manager_name, instance):
    """
    Safely fetch a OneToOne reverse relation.
    Returns the related object, or None if it doesn't exist.
    """
    try:
        return getattr(instance, related_manager_name)
    except Exception:
        return None


@receiver(pre_delete, sender='user.LA_Spatial_Unit_Model')
def archive_parcel_before_delete(sender, instance, **kwargs):
    """
    Fired by Django before a LA_Spatial_Unit_Model row is deleted.

    Imports are kept local so the signal module can be imported at app
    startup without circular-import issues.
    """
    from .models.history import Parcel_Delete_Archive_Model
    from .models.assessments import Assessment_Model, Tax_Info_Model

    # ── OneToOne attribute sub-tables ──────────────────────────────────────────
    # The reverse accessor names come from the OneToOneField definitions.
    # Adjust the accessor names below if your related_name= differs.
    land_unit    = _safe_get_oto('la_ls_land_unit_model',     instance)
    utility_lu   = _safe_get_oto('la_ls_utinet_lu_model',     instance)
    zoning       = _safe_get_oto('la_ls_zoning_model',        instance)
    physical_env = _safe_get_oto('la_ls_physical_env_model',  instance)
    build_unit   = _safe_get_oto('la_ls_build_unit_model',    instance)
    utility_bu   = _safe_get_oto('la_ls_utinet_bu_model',     instance)

    # ── ForeignKey attribute sub-tables ───────────────────────────────────────
    # Assessment and Tax can have multiple rows per parcel — take the latest.
    assessment = (
        Assessment_Model.objects
        .filter(su_id=instance.su_id)
        .order_by('-id')
        .first()
    )
    tax_info = (
        Tax_Info_Model.objects
        .filter(su_id=instance.su_id)
        .order_by('-id')
        .first()
    )

    # ── Write archive row ──────────────────────────────────────────────────────
    # deleted_by is not available here automatically — pass it via
    # instance._deleted_by before calling .delete() in your view:
    #     parcel._deleted_by = request.user.id
    #     parcel.delete()
    Parcel_Delete_Archive_Model.objects.create(
        su_id         = instance.su_id,
        label         = getattr(instance, 'label', None),
        parcel_status = getattr(instance, 'parcel_status', None),
        deleted_by    = getattr(instance, '_deleted_by', None),

        land_unit_data    = _snapshot(land_unit),
        assessment_data   = _snapshot(assessment),
        tax_info_data     = _snapshot(tax_info),
        utility_lu_data   = _snapshot(utility_lu),
        zoning_data       = _snapshot(zoning),
        physical_env_data = _snapshot(physical_env),
        build_unit_data   = _snapshot(build_unit),
        utility_bu_data   = _snapshot(utility_bu),
    )


@receiver(post_save, sender='user.LA_Spatial_Unit_Model')
def create_attribute_placeholders(sender, instance, created, **kwargs):
    """
    LADM — auto-create blank attribute records the moment a new spatial unit
    is saved so all update views always find an existing row.

    Uses transaction.on_commit so the placeholder inserts run AFTER the
    parent survey_rep transaction commits — this avoids the 16-second delay
    caused by lock contention when querying survey_rep inside the same
    open transaction.
    """
    if not created:
        return

    from django.db import transaction

    def _create_placeholders():
        from .models.spatial_units import (
            LA_LS_Land_Unit_Model,
            LA_LS_Zoning_Model,
            LA_LS_Physical_Env_Model,
            LA_LS_Utinet_LU_Model,
        )
        from .models.assessments import Assessment_Model, Tax_Info_Model

        try:
            LA_LS_Land_Unit_Model.objects.get_or_create(su_id=instance)
            LA_LS_Zoning_Model.objects.get_or_create(su_id=instance)
            LA_LS_Physical_Env_Model.objects.get_or_create(su_id=instance)
            LA_LS_Utinet_LU_Model.objects.get_or_create(su_id=instance)
            Assessment_Model.objects.get_or_create(su_id=instance)
            Tax_Info_Model.objects.get_or_create(su_id=instance)
        except Exception:
            pass  # never block a save due to placeholder creation failure

    transaction.on_commit(_create_placeholders)