from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ LA Spatial Unit Model __________________________________________________________
class LA_Spatial_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.IntegerField(null=False, unique=True)

    status = models.BooleanField(null=False, default=True)
    label = models.CharField(max_length=255, null=True)
    parcel_status = models.CharField(max_length=30, null=True)

    class Meta:
            managed = True
            db_table = 'la_spatial_unit'

#_______________________________________________ LA_LS_Land_Unit Model __________________________________________________________
class LA_LS_Land_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    access_road = models.CharField(max_length=255, null=True)
    postal_ad_lnd = models.CharField(max_length=255, null=True)
    local_auth = models.CharField(max_length=255, null=True, blank=True)
    ext_landuse_type = models.CharField(max_length=100, null=True)
    ext_landuse_sub_type = models.CharField(max_length=100, null=True)
    sl_land_type = models.CharField(max_length=30, null=True)
    land_name = models.CharField(max_length=255, null=True)
    registration_date = models.DateField(null=True)

    tenure_type = models.CharField(max_length=30, null=True)

    # Parcel relationship fields
    adjacent_parcels = models.CharField(max_length=500, null=True)
    parent_parcel = models.CharField(max_length=100, null=True)
    child_parcels = models.CharField(max_length=500, null=True)
    part_of_estate = models.CharField(max_length=255, null=True)

    # LADM ISO 19152 – LA_SpatialUnit spatial geometry attributes
    area = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    perimeter = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    dimension_2d_3d = models.CharField(max_length=3, null=True)
    boundary_type = models.CharField(max_length=30, null=True)
    crs = models.CharField(max_length=20, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_land_unit'

#_______________________________________________ LA_LS_Zoning Model _____________________________________________________________
class LA_LS_Zoning_Model(models.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.OneToOneField(
        'LA_Spatial_Unit_Model', on_delete=models.CASCADE,
        db_column='su_id', to_field='su_id'
    )
    zoning_category     = models.CharField(max_length=10, null=True)
    max_building_height = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    max_coverage        = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    max_far             = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    setback_front       = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    setback_rear        = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    setback_side        = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    special_overlay     = models.CharField(max_length=255, null=True)

    class Meta:
        managed = True
        db_table = 'la_ls_zoning'

#_______________________________________________ LA_LS_Physical_Env Model _______________________________________________________
class LA_LS_Physical_Env_Model(models.Model):
    id = models.AutoField(primary_key=True)
    su_id = models.OneToOneField(
        'LA_Spatial_Unit_Model', on_delete=models.CASCADE,
        db_column='su_id', to_field='su_id'
    )
    elevation        = models.DecimalField(max_digits=10, decimal_places=3, null=True)  # metres
    slope            = models.DecimalField(max_digits=5, decimal_places=2, null=True)   # degrees
    soil_type        = models.CharField(max_length=20, null=True)  # CLAY/SAND/LOAM/SILT/ROCK/PEAT/FILL
    flood_zone       = models.BooleanField(null=True)
    vegetation_cover = models.CharField(max_length=255, null=True)

    class Meta:
        managed = True
        db_table = 'la_ls_physical_env'

#_______________________________________________ LA_BAUnit_SpatialUnit (M:M) Model ______________________________________________
class LA_BAUnit_SpatialUnit_Model(models.Model):
    """LADM ISO 19152 – explicit M:M relationship between BA units and spatial units.
    One BA unit can reference multiple spatial units (e.g. a right spanning several parcels)
    and one spatial unit can belong to multiple BA units."""
    id = models.AutoField(primary_key=True)
    ba_unit = models.ForeignKey(
        'SL_BA_Unit_Model', on_delete=models.CASCADE, db_column='ba_unit_id'
    )
    su = models.ForeignKey(
        'LA_Spatial_Unit_Model', on_delete=models.CASCADE,
        db_column='su_id', to_field='su_id'
    )
    # PRIMARY = main parcel, SECONDARY = appurtenant, PART_OF = strata / sub-unit
    relation_type = models.CharField(max_length=20, null=True, default='PRIMARY')

    class Meta:
        managed = True
        db_table = 'la_ba_unit_spatial_unit'
        unique_together = [('ba_unit', 'su')]

#_______________________________________________ LA_LS_Utinet_LU Model __________________________________________________________
class LA_LS_Utinet_LU_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    water = models.CharField(max_length=50, null=True)
    elec = models.CharField(max_length=50, null=True)
    drainage = models.CharField(max_length=50, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    sani_gully = models.CharField(max_length=50, null=True)
    garbage_dispose = models.CharField(max_length=50, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_lu'

#_______________________________________________ LA_LS_Build_Unit Model _________________________________________________________
class LA_LS_Build_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)
    postal_ad_build = models.CharField(max_length=255, null=True)
    house_hold_no = models.CharField(max_length=25, null=True)
    no_floors = models.IntegerField(null=True)

    ext_builduse_type = models.CharField(max_length=100, null=True)
    ext_builduse_sub_type = models.CharField(max_length=100, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    roof_type = models.CharField(max_length=20, null=True)
    wall_type = models.CharField(max_length=20, null=True)
    building_name = models.CharField(max_length=255, null=True)
    bld_property_type = models.CharField(max_length=255, null=True)

    registration_date  = models.DateField(null=True)
    construction_year  = models.IntegerField(null=True)
    structure_type     = models.CharField(max_length=30, null=True)  # CONC_REINF/STEEL_FRM/MASONRY/TIMBER/COMPOSITE
    condition          = models.CharField(max_length=20, null=True)  # EXCELLENT/GOOD/FAIR/POOR/DILAPID

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_build_unit'

#_______________________________________________ LA_LS_Utinet_BU Model __________________________________________________________
class LA_LS_Utinet_BU_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    water = models.CharField(max_length=15, null=True)
    water_drink = models.CharField(max_length=15, null=True)
    elec = models.CharField(max_length=15, null=True)
    tele = models.CharField(max_length=15, null=True)
    internet = models.CharField(max_length=15, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    sani_gully = models.CharField(max_length=50, null=True)
    garbage_dispose = models.CharField(max_length=15, null=True)
    drainage = models.CharField(max_length=100, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_bu'

#_______________________________________________ LA_LS_Apt_Unit Model ___________________________________________________________
class LA_LS_Apt_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    ref_id = models.OneToOneField('LA_LS_Ils_Unit_Model', on_delete=models.CASCADE, db_column='ref_id', to_field='id')

    postal_ad_apt = models.CharField(max_length=255, null=True)
    floor_no = models.IntegerField(null=True)
    house_hold_no = models.CharField(max_length=25, null=True)
    specific_id = models.CharField(max_length=25, null=True)
    ext_div_type = models.CharField(max_length=100, null=True)
    floor_area = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    ext_aptuse_type = models.CharField(max_length=100, null=True)
    ext_aptuse_sub_type = models.CharField(max_length=100, null=True)
    surface_relation = models.CharField(max_length=20, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    roof_type = models.CharField(max_length=20, null=True)
    wall_type = models.CharField(max_length=20, null=True)
    floor_type = models.CharField(max_length=20, null=True)
    apt_name = models.CharField(max_length=255, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_apt_unit'

#_______________________________________________ LA_LS_Utinet_AU Model __________________________________________________________
class LA_LS_Utinet_AU_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    ref_id = models.OneToOneField('LA_LS_Ils_Unit_Model', on_delete=models.CASCADE, db_column='ref_id', to_field='id')

    water = models.CharField(max_length=15, null=True)
    water_drink = models.CharField(max_length=15, null=True)
    elec = models.CharField(max_length=15, null=True)
    tele = models.CharField(max_length=15, null=True)
    internet = models.CharField(max_length=15, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    garbage_dispose = models.CharField(max_length=15, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_au'

#_______________________________________________ LA_LS_Ols_Polygon_Unit Model ___________________________________________________
class LA_LS_Ols_Polygon_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)
    postal_ad_ols = models.CharField(max_length=255, null=True)

    ols_main_type = models.CharField(max_length=100, null=True)
    ext_olsuse_type = models.CharField(max_length=100, null=True)
    ext_olsuse_sub_type = models.CharField(max_length=100, null=True)
    ols_x_type = models.CharField(max_length=100, null=True)
    ols_build_type = models.CharField(max_length=100, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    grade = models.CharField(max_length=10, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    status = models.BooleanField(null=False, default=True)
    ols_poly_name = models.CharField(max_length=255, null=True)

    class Meta:
            managed = True
            db_table = 'la_ls_ols_unit'

#_______________________________________________ LA_LS_Ols_PointLine_Unit Model _________________________________________________
class LA_LS_Ols_PointLine_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)

    ols_made_type = models.CharField(max_length=100, null=True)
    ols_main_type = models.CharField(max_length=100, null=True)
    ols_x_type = models.CharField(max_length=100, null=True)
    ols_build_type = models.CharField(max_length=100, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    grade = models.CharField(max_length=10, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    status = models.BooleanField(null=False, default=True)
    ols_point_line_name = models.CharField(max_length=255, null=True)

    class Meta:
            managed = True
            db_table = 'la_ls_ols_pointline_unit'

#_______________________________________________ LA_LS_MyLayer_Polygon_Unit Model _______________________________________________
class LA_LS_MyLayer_Polygon_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)
    postal_ad_ols = models.CharField(max_length=255, null=True)

    ols_main_type = models.CharField(max_length=100, null=True)
    ext_olsuse_type = models.CharField(max_length=100, null=True)
    ext_olsuse_sub_type = models.CharField(max_length=100, null=True)
    ols_x_type = models.CharField(max_length=100, null=True)
    ols_build_type = models.CharField(max_length=100, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    grade = models.CharField(max_length=10, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_mylayer_unit'

#_______________________________________________ LA_LS_MyLayer_PointLine_Unit Model _____________________________________________
class LA_LS_MyLayer_PointLine_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    access_road = models.CharField(max_length=255, null=True)

    ols_made_type = models.CharField(max_length=100, null=True)
    ols_main_type = models.CharField(max_length=100, null=True)
    ols_x_type = models.CharField(max_length=100, null=True)
    ols_build_type = models.CharField(max_length=100, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    grade = models.CharField(max_length=10, null=True)

    surface_relation = models.CharField(max_length=20, null=True)
    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_mylayer_pointline_unit'

#_______________________________________________ LA_LS_Utinet_Ols Model _________________________________________________________
class LA_LS_Utinet_Ols_Model(models.Model):
    id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    water = models.CharField(max_length=15, null=True)
    water_drink = models.CharField(max_length=15, null=True)
    elec = models.CharField(max_length=15, null=True)
    tele = models.CharField(max_length=15, null=True)
    internet = models.CharField(max_length=15, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    sani_gully = models.CharField(max_length=15, null=True)
    drainage = models.CharField(max_length=15, null=True)
    garbage_dispose = models.CharField(max_length=15, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_ols'

#_______________________________________________ LA_LS_Ils_Unit Model ___________________________________________________________
class LA_LS_Ils_Unit_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    ref_id = models.OneToOneField('LA_LS_Build_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    postal_ad_ils = models.CharField(max_length=255, null=True)
    floor_no = models.IntegerField(null=True)
    house_hold_no = models.CharField(max_length=25, null=True)
    floor_area = models.DecimalField(max_digits=8, decimal_places=2, null=True)

    ext_ilsuse_type = models.CharField(max_length=100, null=True)
    ext_ilsuse_sub_type = models.CharField(max_length=100, null=True)
    surface_relation = models.CharField(max_length=20, null=True)

    hight = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    roof_type = models.CharField(max_length=20, null=True)
    wall_type = models.CharField(max_length=20, null=True)
    floor_type = models.CharField(max_length=20, null=True)
    ils_name = models.CharField(max_length=255, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_ils_unit'

#_______________________________________________ LA_LS_Utinet_Ils Model _________________________________________________________
class LA_LS_Utinet_Ils_Model(models.Model):
    id = models.AutoField(primary_key=True)

    # su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')
    ref_id = models.OneToOneField('LA_LS_Build_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    water = models.CharField(max_length=15, null=True)
    water_drink = models.CharField(max_length=15, null=True)
    elec = models.CharField(max_length=15, null=True)
    tele = models.CharField(max_length=15, null=True)
    internet = models.CharField(max_length=15, null=True)
    sani_sewer = models.CharField(max_length=50, null=True)
    garbage_dispose = models.CharField(max_length=15, null=True)

    status = models.BooleanField(null=False, default=True)

    class Meta:
            managed = True
            db_table = 'la_ls_utinet_ils'

#_______________________________________________ LA_Spatial_Unit_Sketch_Ref Model _______________________________________________
class LA_Spatial_Unit_Sketch_Ref_Model(models.Model):
    sketch_ref_id = models.AutoField(primary_key=True)
    sketch_ref_type = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    approval_status = models.BooleanField(null=False, default=True)
    avl_status = models.BooleanField(null=False, default=True)

    file_path = models.FileField(upload_to='documents/sketch_ref', null=True)

    doc_owner = models.ForeignKey('Party_Model', on_delete=models.CASCADE, db_column='doc_owner', to_field='pid', null=True)

    status = models.BooleanField(null=False, default=True)
    remark = models.CharField(max_length=255, null=True)

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'la_spatial_unit_sketch_ref'
