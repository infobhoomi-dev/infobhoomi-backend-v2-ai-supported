from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ SL BA Unit Model _______________________________________________________________
class SL_BA_Unit_Model(models.Model):
    ba_unit_id = models.AutoField(primary_key=True)

    # Issue #7 fix: PROTECT prevents accidental cascade deletion of a parcel that has title records.
    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.PROTECT, db_column='su_id', to_field='su_id')

    sl_ba_unit_type = models.CharField(max_length=30, null=False)
    sl_ba_unit_name = models.TextField(null=False)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'sl_ba_unit'

#_______________________________________________ LA Admin Source Model __________________________________________________________
class LA_Admin_Source_Model(models.Model):
    admin_source_id = models.AutoField(primary_key=True)
    admin_source_type = models.CharField(max_length=255, null=False)

    # Issue #4 fix: fields that were captured in the frontend form but never persisted.
    reference_no     = models.CharField(max_length=255, null=True)   # document reference number
    acceptance_date  = models.DateField(null=True)                    # date document was accepted
    exte_arch_ref    = models.CharField(max_length=255, null=True)   # external archive reference
    source_description = models.TextField(null=True)                  # free-text description

    done_by = models.IntegerField(null=True)
    user_id = models.IntegerField(null=False)
    file_path = models.FileField(upload_to='documents/admin_source', null=True)

    status = models.BooleanField(null=False, default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'la_admin_source'

#_______________________________________________ LA RRR Model ___________________________________________________________________
class LA_RRR_Model(models.Model):
    rrr_id = models.AutoField(primary_key=True)

    # Issue #7 fix: PROTECT so BA unit deletion is blocked while RRRs exist.
    # Issue #10 fix: null removed — every RRR must belong to a BA unit (state-only; DB column stays nullable
    #                until a data-cleanup confirms no null rows exist).
    ba_unit_id = models.ForeignKey('SL_BA_Unit_Model', on_delete=models.PROTECT, db_column='ba_unit_id')
    # Issue #7 fix: SET_NULL so removing a document doesn't delete the right itself.
    # admin_source_id is intentionally nullable — a right can outlive its document.
    admin_source_id = models.ForeignKey('LA_Admin_Source_Model', on_delete=models.SET_NULL, db_column='admin_source_id', null=True)

    # Party link is intentionally on Party_Roles_Model only (via sl_party_roles.rrr_id).
    # Having pid here too was redundant — see Issue #1 fix, migration 0445.

    # LADM ISO 19152 – LA_RRR required attributes
    # Issue #10 fix: null removed — every RRR must have a type (state-only enforcement).
    rrr_type    = models.CharField(max_length=50)              # RIGHT / RESTRICTION / RESPONSIBILITY
    time_begin  = models.DateField(null=True)                   # validFrom
    time_end    = models.DateField(null=True)                   # validTo
    description = models.TextField(null=True)
    # Issue #7 fix: soft-delete flag — set False to terminate a right without erasing history.
    status      = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_rrr'

#_______________________________________________ LA Mortgage Model ______________________________________________________________
class LA_Mortgage_Model(models.Model):
    """Issue #6 fix: structured storage for mortgage-specific fields.
    One-to-one with LA_RRR_Model — only created when rrr_type is 'Mortgage'."""
    id = models.AutoField(primary_key=True)
    rrr_id = models.OneToOneField(
        'LA_RRR_Model', on_delete=models.CASCADE,
        db_column='rrr_id', related_name='mortgage'
    )
    amount          = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    interest        = models.DecimalField(max_digits=7, decimal_places=4, null=True)  # % rate
    ranking         = models.IntegerField(null=True)
    mortgage_type   = models.CharField(max_length=100, null=True)
    mortgage_ref_id = models.CharField(max_length=255, null=True)  # external mortgage ID
    mortgagee       = models.CharField(max_length=255, null=True)  # name/entity of lender

    class Meta:
        managed = True
        db_table = 'la_mortgage'

#_______________________________________________ LA RRR Document Model (additional docs per BA unit) ___________________________________
class LA_RRR_Document_Model(models.Model):
    """Links additional admin-source documents to a BA unit (beyond the primary admin_source_id on LA_RRR_Model)."""
    id = models.AutoField(primary_key=True)
    ba_unit = models.ForeignKey('SL_BA_Unit_Model', on_delete=models.CASCADE, db_column='ba_unit_id')
    admin_source = models.ForeignKey('LA_Admin_Source_Model', on_delete=models.CASCADE, db_column='admin_source_id')

    class Meta:
        managed = True
        db_table = 'la_rrr_document'

#_______________________________________________ LA RRR Restriction Model _______________________________________________________________
class LA_RRR_Restriction_Model(models.Model):
    id = models.AutoField(primary_key=True)
    # Issue #3 fix: restrictions apply to the property (BA unit), not to a specific right.
    # Issue #7 fix: PROTECT so BA unit deletion is blocked while restrictions exist.
    ba_unit_id = models.ForeignKey('SL_BA_Unit_Model', on_delete=models.PROTECT, db_column='ba_unit_id', related_name='restrictions')
    rrr_restriction_type = models.CharField(max_length=20, null=False)  # RES_EAS/RES_COV/RES_HGT/RES_HER/RES_ENV
    description = models.TextField(null=True)
    time_begin  = models.DateField(null=True)
    time_end    = models.DateField(null=True)

    class Meta:
        managed = True
        db_table = 'la_rrr_restriction'

#_______________________________________________ LA RRR Responsibility Model ____________________________________________________________
class LA_RRR_Responsibility_Model(models.Model):
    id = models.AutoField(primary_key=True)
    # Issue #3 fix: responsibilities apply to the property (BA unit), not to a specific right.
    # Issue #7 fix: PROTECT so BA unit deletion is blocked while responsibilities exist.
    ba_unit_id = models.ForeignKey('SL_BA_Unit_Model', on_delete=models.PROTECT, db_column='ba_unit_id', related_name='responsibilities')
    rrr_responsibility_type = models.CharField(max_length=20, null=False)  # RSP_MAINT/RSP_TAX/RSP_INS
    description = models.TextField(null=True)
    time_begin  = models.DateField(null=True)
    time_end    = models.DateField(null=True)

    class Meta:
        managed = True
        db_table = 'la_rrr_responsibility'

#_______________________________________________ LA RRR Audit Model _______________________________________________________________
class LA_RRR_Audit_Model(models.Model):
    """Issue #8 fix: immutable audit log for every RRR state change.
    rrr_id is a plain IntegerField (not FK) so records survive even if the RRR row is hard-deleted."""
    CREATE    = 'CREATE'
    TERMINATE = 'TERMINATE'
    UPDATE    = 'UPDATE'
    ACTION_CHOICES = [(CREATE, 'Create'), (TERMINATE, 'Terminate'), (UPDATE, 'Update')]

    id             = models.AutoField(primary_key=True)
    rrr_id         = models.IntegerField()                        # intentionally not a FK
    ba_unit_id     = models.IntegerField(null=True)
    su_id          = models.IntegerField(null=True)
    action         = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changed_by     = models.IntegerField()                        # user.id
    changed_by_name= models.CharField(max_length=255, null=True)  # denormalized for display
    changed_at     = models.DateTimeField(auto_now_add=True)
    snapshot       = models.JSONField()                           # full RRR state at time of action

    class Meta:
        managed  = True
        db_table = 'la_rrr_audit'
        ordering = ['-changed_at']

#_______________________________________________ Party Roles Model ____________________________________________________________________
class Party_Roles_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # Issue #10 fix: null removed — a party role without a party or RRR is meaningless
    #                (state-only enforcement; DB columns stay nullable until data cleanup).
    pid    = models.ForeignKey('Party_Model',    on_delete=models.CASCADE, db_column='pid')
    rrr_id = models.ForeignKey('LA_RRR_Model',   on_delete=models.CASCADE, db_column='rrr_id')

    party_role_type = models.CharField(max_length=255, null=False)
    # LADM: share belongs to the party's participation in the RRR, not to the RRR itself
    share_type = models.CharField(max_length=100, null=True, blank=True)
    share = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    done_by = models.IntegerField(null=False) # person who add the record

    class Meta:
        managed = True
        db_table = 'sl_party_roles'
