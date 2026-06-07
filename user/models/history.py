from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ History_Spartial_Unit_Attrib Model _____________________________________________
class History_Spartialunit_Attrib_Model(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(null=False)
    # LADM ISO 19152 – soft FK so audit records survive spatial unit deletion
    su_id = models.ForeignKey(
        'LA_Spatial_Unit_Model', on_delete=models.SET_NULL,
        null=True, db_column='su_id', to_field='su_id', db_constraint=False
    )
    category = models.CharField(max_length=255, null=False)
    field_name = models.CharField(max_length=255, null=False)
    field_value = models.CharField(max_length=255, null=False)
    date_created = models.DateTimeField(auto_now_add=True)


    class Meta:
        managed = True
        db_table = 'history_spatialunit_attrib'

#_______________________________________________ LA_Spatial_Source Model ________________________________________________________
class LA_Spatial_Source_Model(models.Model):
    id = models.AutoField(primary_key=True)
    spatial_source_type = models.CharField(max_length=255, null=True)
    source_id = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    approval_status = models.BooleanField(null=False, default=True)
    date_accept = models.DateField(null=True)
    file_path = models.FileField(upload_to='documents/spatial_source', null=False)

    surveyor_name = models.CharField(max_length=255, null=True)

    status = models.BooleanField(null=False, default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'la_spatial_source'
# ─── ADD TO BOTTOM OF user/models/history.py ──────────────────────────────────

class Parcel_Delete_Archive_Model(models.Model):
    """
    LADM ISO 19152 — Parcel deletion archive.

    When a LA_Spatial_Unit record is deleted the pre_delete signal in
    user/signals.py snapshots all attribute sub-tables here as JSON before
    the CASCADE deletes fire.  Because the spatial unit is gone the su_id
    column is a plain IntegerField (no FK) so the archive is permanent.
    """
    id            = models.AutoField(primary_key=True)

    # Identity of the deleted parcel — plain int, no FK (parcel no longer exists)
    su_id         = models.IntegerField(db_index=True)
    label         = models.CharField(max_length=255, null=True, blank=True)
    parcel_status = models.CharField(max_length=50,  null=True, blank=True)

    deleted_at    = models.DateTimeField(auto_now_add=True, db_index=True)
    deleted_by    = models.IntegerField(null=True, blank=True)   # user_id of actor

    # JSON snapshots of each attribute sub-table at time of deletion
    # null means the sub-table record did not exist (tab was never saved)
    land_unit_data    = models.JSONField(null=True, blank=True)  # LA_LS_Land_Unit_Model
    assessment_data   = models.JSONField(null=True, blank=True)  # Assessment_Model
    tax_info_data     = models.JSONField(null=True, blank=True)  # Tax_Info_Model
    utility_lu_data   = models.JSONField(null=True, blank=True)  # LA_LS_Utinet_LU_Model
    zoning_data       = models.JSONField(null=True, blank=True)  # LA_LS_Zoning_Model
    physical_env_data = models.JSONField(null=True, blank=True)  # LA_LS_Physical_Env_Model
    build_unit_data   = models.JSONField(null=True, blank=True)  # LA_LS_Build_Unit_Model
    utility_bu_data   = models.JSONField(null=True, blank=True)  # LA_LS_Utinet_BU_Model

    # Extra legal-space snapshots captured on cascade delete (added 2026-06-06)
    apt_unit_data     = models.JSONField(null=True, blank=True)  # LA_LS_Apt_Unit_Model
    ols_polygon_data  = models.JSONField(null=True, blank=True)  # LA_LS_Ols_Polygon_Unit_Model
    ols_pointline_data= models.JSONField(null=True, blank=True)  # LA_LS_Ols_PointLine_Unit_Model
    ils_unit_data     = models.JSONField(null=True, blank=True)  # LA_LS_Ils_Unit_Model
    utility_au_data   = models.JSONField(null=True, blank=True)  # LA_LS_Utinet_AU_Model
    utility_ols_data  = models.JSONField(null=True, blank=True)  # LA_LS_Utinet_Ols_Model

    # Relationship to the parcel this legal space was deleted with.
    # null on the parcel's own archive row; set to the parent parcel su_id for
    # buildings/units/legal spaces removed by the cascade.
    parent_su_id      = models.IntegerField(null=True, blank=True, db_index=True)
    space_kind        = models.CharField(max_length=40, null=True, blank=True)  # parcel/building/unit/legal_space
    layer_id          = models.IntegerField(null=True, blank=True)

    class Meta:
        managed  = True
        db_table = 'parcel_delete_archive'
        ordering = ['-deleted_at']


class Parcel_History_Model(models.Model):
    """Unified parcel/building audit log for UI history and safe restore."""

    RECORD_ATTRIBUTE = 'attribute'
    RECORD_GEOMETRY = 'geometry'
    RECORD_RRR = 'rrr'
    RECORD_RELATIONSHIP = 'relationship'
    RECORD_LEGAL_SPACE = 'legal_space'   # building/unit/legal-space removed or right terminated on parcel delete

    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_RESTORE = 'restore'
    ACTION_TERMINATE = 'terminate'

    id = models.AutoField(primary_key=True)
    su_id = models.IntegerField(db_index=True)
    record_type = models.CharField(max_length=30, db_index=True)
    action = models.CharField(max_length=30, db_index=True)
    category = models.CharField(max_length=80, null=True, blank=True)
    field_name = models.CharField(max_length=255, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    change_summary = models.TextField()
    changed_by = models.IntegerField(null=True, blank=True)
    changed_by_name = models.CharField(max_length=255, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    snapshot = models.JSONField(null=True, blank=True)
    can_restore = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'parcel_history'
        ordering = ['-changed_at', '-id']


class Parcel_Event_Model(models.Model):
    """Legal event stack for parcel history rectification."""

    TYPE_ATTRIBUTE = 'attribute'
    TYPE_GEOMETRY = 'geometry'
    TYPE_RRR = 'rrr'
    TYPE_RELATIONSHIP = 'relationship'
    TYPE_SPLIT = 'split'
    TYPE_MERGE = 'merge'
    TYPE_RECTIFICATION = 'rectification'

    STATUS_ACTIVE = 'active'
    STATUS_RECTIFIED = 'rectified'
    STATUS_REAPPLIED = 'reapplied'
    STATUS_RECORDED = 'recorded'
    STATUS_BLOCKED = 'blocked'

    id = models.AutoField(primary_key=True)
    primary_su_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=40, db_index=True)
    summary = models.TextField()
    status = models.CharField(max_length=30, default=STATUS_ACTIVE, db_index=True)
    affected_parcel_ids = ArrayField(models.IntegerField(), null=True, blank=True)
    source_history_id = models.IntegerField(null=True, blank=True, db_index=True)
    source_event_id = models.IntegerField(null=True, blank=True, db_index=True)
    before_snapshot = models.JSONField(null=True, blank=True)
    after_snapshot = models.JSONField(null=True, blank=True)
    rectification_reason = models.TextField(null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_by_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    rectified_by = models.IntegerField(null=True, blank=True)
    rectified_at = models.DateTimeField(null=True, blank=True)
    can_rectify = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'parcel_event'
        ordering = ['-created_at', '-id']
