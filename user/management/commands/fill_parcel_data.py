"""
Management command: fill_parcel_data
-------------------------------------
Fills attribute data for the 40 land parcels (su_ids 1004-1043) that already
exist as geometry-only records in survey_rep / la_spatial_unit, and creates
10 building footprints (one per every 4th parcel).

Nothing is truncated — existing skeleton records are updated in place and
missing related records are created.

Usage:
    python manage.py fill_parcel_data          # prompts for confirmation
    python manage.py fill_parcel_data --yes    # skips confirmation
"""

import random
from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry, Polygon

from user.models import (
    User,
    LA_Spatial_Unit_Model,
    LA_LS_Land_Unit_Model,
    LA_LS_Build_Unit_Model,
    LA_LS_Utinet_BU_Model,
    LA_LS_Zoning_Model,
    LA_LS_Physical_Env_Model,
    Survey_Rep_DATA_Model,
    Assessment_Model,
    Tax_Info_Model,
    SL_BA_Unit_Model,
    LA_Admin_Source_Model,
    LA_RRR_Model,
    Party_Model,
)

# ---------- target land parcel su_ids ------------------------------------------
LAND_SU_IDS = list(range(1004, 1044))          # 40 parcels
BLDG_SU_START = 5001                            # safe above current max (4542)
BUILDING_PARCEL_IDXS = {0, 4, 8, 12, 16, 20, 24, 28, 32, 36}   # 10 buildings

# ---------- lookup choices -----------------------------------------------------
LAND_NAMES = [
    "Perera Gardens",        "Lotus Meadow",          "Kandy View Plot",
    "Highland Terrace",      "River Valley Land",      "Green Pastures",
    "Summit Property",       "Palm Estate",            "Meadow Land",
    "Sunrise Plot",          "City Boundary Land",     "Rock Field",
    "Forest Edge Plot",      "Hill Top Land",          "Valley View Estate",
    "Old Town Parcel",       "Bridge View Land",       "Temple Surrounds",
    "Market Corner Plot",    "School Road Land",       "Heritage Property",
    "Lakeside Terrace",      "Garden Estate",          "Mountain View Land",
    "Town Centre Plot",      "Civic Quarter",          "Agricultural Reserve",
    "Commercial Frontage",   "Residential Block",      "Industrial Zone Plot",
    "Riverside Property",    "Central Park Plot",      "East Village Land",
    "West End Estate",       "North Gate Parcel",      "South Hill Land",
    "Harbour View Plot",     "Coconut Grove Estate",   "Bamboo Lane Property",
    "Firefly Meadow",
]

BUILDING_NAMES = [
    "Perera Residence",   "Green Villa",       "Kandy House",
    "Hillside Home",      "Valley View Bldg",  "Sunrise Apartments",
    "Garden House",       "Mountain Lodge",    "Lotus Building",
    "Heritage House",
]

ADDRESSES = [
    "12, Kandy Road, Peradeniya",
    "45, Temple Street, Kandy",
    "8, Hill View Road, Katugastota",
    "23, Rajapihilla Mawatha, Kandy",
    "67, Vihara Lane, Kandy",
    "3, Lake Drive, Kandy",
    "18, Queen Street, Kandy",
    "56, Hospital Road, Kandy",
]

LAND_TYPES      = ['Freehold', 'Leasehold', 'State_Land', 'Private']
LANDUSE_TYPES   = ['Residential', 'Commercial', 'Agricultural', 'Mixed']
ZONING_CATS     = ['R1', 'R2', 'C1', 'C2', 'MU']
SOIL_TYPES      = ['CLAY', 'SAND', 'LOAM', 'SILT', 'ROCK']
STRUCTURE_TYPES = ['CONC_REINF', 'MASONRY', 'TIMBER', 'STEEL_FRM', 'COMPOSITE']
CONDITIONS      = ['EXCELLENT', 'GOOD', 'FAIR', 'POOR']
ROOF_TYPES      = ['FLAT', 'GABLE', 'HIP', 'SHED']
WALL_TYPES      = ['BRICK', 'CONCRETE', 'TIMBER']
TAX_STATUSES    = ['paid', 'paid', 'paid', 'pending', 'overdue']
LOCAL_AUTHS     = [
    'Kandy Municipal Council',
    'Katugastota Urban Council',
    'Peradeniya Pradeshiya Sabha',
    'Kundasale Pradeshiya Sabha',
    'Gampola Municipal Council',
]


class Command(BaseCommand):
    help = 'Fill attribute data for 40 existing land parcels and add 10 buildings'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')

    def handle(self, *args, **options):
        if not options['yes']:
            self.stdout.write(self.style.WARNING(
                '\nThis will UPDATE all null fields on the 40 land parcels (su_ids 1004-1043)\n'
                'and CREATE 10 building records (su_ids 5001-5010).\n'
                'No existing geometry or spatial records are deleted.\n'
            ))
            confirm = input('Type  YES  to continue: ').strip()
            if confirm != 'YES':
                self.stdout.write('Aborted — nothing changed.')
                return

        first_user = User.objects.order_by('id').first()
        if not first_user:
            self.stdout.write(self.style.ERROR(
                'No users found. Create a superuser first:\n'
                '  python manage.py createsuperuser'
            ))
            return

        user_id = first_user.id
        org_id  = int(getattr(first_user, 'org_id', None) or 1)
        self.stdout.write(f'\nUsing user_id={user_id}, org_id={org_id}  ({first_user.username})\n')

        # Reuse the 5 existing seed parties; create if somehow missing
        parties = list(Party_Model.objects.order_by('pid')[:5])
        if not parties:
            self.stdout.write(self.style.ERROR(
                'No Party records found. Run seed_test_data first to create owner parties.'
            ))
            return
        self.stdout.write(f'Using {len(parties)} existing party records.\n')

        with transaction.atomic():
            self._fill_land_parcels(parties, user_id, org_id)

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Done! 40 land parcels updated, 10 buildings created.\n'
            f'  Building su_ids: {BLDG_SU_START} – {BLDG_SU_START + 9}\n'
        ))

    # -------------------------------------------------------------------------
    def _fill_land_parcels(self, parties, user_id, org_id):
        bldg_counter = 0

        for idx, su_id in enumerate(LAND_SU_IDS):
            rng   = random.Random(su_id)
            owner = parties[idx % len(parties)]

            # -- la_spatial_unit (must already exist) -------------------------
            try:
                su = LA_Spatial_Unit_Model.objects.get(su_id=su_id)
            except LA_Spatial_Unit_Model.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  [SKIP] la_spatial_unit su_id={su_id} not found'))
                continue

            # -- la_ls_land_unit (update existing) ----------------------------
            land_name = LAND_NAMES[idx]
            LA_LS_Land_Unit_Model.objects.filter(su_id=su).update(
                access_road=rng.choice(['Yes', 'Yes', 'Yes', 'No']),
                postal_ad_lnd=ADDRESSES[idx % len(ADDRESSES)],
                local_auth=rng.choice(LOCAL_AUTHS),
                ext_landuse_type=rng.choice(LANDUSE_TYPES),
                ext_landuse_sub_type=rng.choice(['High Density', 'Low Density', 'Medium Density', 'Mixed Use']),
                sl_land_type=rng.choice(LAND_TYPES),
                land_name=land_name,
                registration_date=date(
                    rng.randint(2000, 2023),
                    rng.randint(1, 12),
                    rng.randint(1, 28),
                ),
                status=True,
            )

            # -- la_ls_zoning (create if missing) ----------------------------
            LA_LS_Zoning_Model.objects.get_or_create(
                su_id=su,
                defaults=dict(
                    zoning_category=rng.choice(ZONING_CATS),
                    max_building_height=Decimal(str(rng.randint(6, 20))),
                    max_coverage=Decimal(str(round(rng.uniform(0.40, 0.80), 2))),
                    max_far=Decimal(str(round(rng.uniform(0.5, 3.0), 2))),
                    setback_front=Decimal(str(rng.randint(2, 6))),
                    setback_rear=Decimal(str(rng.randint(1, 4))),
                    setback_side=Decimal(str(rng.randint(1, 3))),
                    special_overlay=rng.choice([None, 'Heritage Overlay', 'Flood Risk Zone', 'Scenic Corridor']),
                ),
            )

            # -- la_ls_physical_env (create if missing) ----------------------
            LA_LS_Physical_Env_Model.objects.get_or_create(
                su_id=su,
                defaults=dict(
                    elevation=Decimal(str(round(rng.uniform(450, 600), 1))),
                    slope=Decimal(str(round(rng.uniform(0.0, 18.0), 1))),
                    soil_type=rng.choice(SOIL_TYPES),
                    flood_zone=rng.random() < 0.12,
                    vegetation_cover=rng.choice(['Dense', 'Sparse', 'None', 'Moderate', 'Cultivated']),
                ),
            )

            # -- assessment (update existing) --------------------------------
            land_val   = Decimal(str(rng.randint(3_000_000, 15_000_000)))
            market_val = (land_val * Decimal('1.20')).quantize(Decimal('0.01'))
            ann_val    = (land_val * Decimal('0.05')).quantize(Decimal('0.01'))
            Assessment_Model.objects.filter(su_id=su).update(
                assessment_no=f'ASS-{su_id}',
                ass_road=ADDRESSES[idx % len(ADDRESSES)],
                assessment_annual_value=ann_val,
                assessment_percentage=Decimal('5.00'),
                date_of_valuation=date(rng.randint(2018, 2024), rng.randint(1, 12), 1),
                year_of_assessment=str(rng.randint(2020, 2024)),
                property_type='Land',
                assessment_name=land_name,
                land_value=land_val,
                market_value=market_val,
                tax_status=rng.choice(TAX_STATUSES),
            )

            # -- tax_info (update existing) ----------------------------------
            tax_val = (land_val * Decimal('0.03')).quantize(Decimal('0.01'))
            Tax_Info_Model.objects.filter(su_id=su).update(
                tax_no=f'TAX-{su_id}',
                tax_annual_value=tax_val,
                tax_percentage=Decimal('3.00'),
                tax_date=date(rng.randint(2020, 2025), 1, 1),
                tax_type='Property Tax',
                tax_name=land_name,
            )

            # -- sl_ba_unit (create if missing) ------------------------------
            ba, _ = SL_BA_Unit_Model.objects.get_or_create(
                su_id=su,
                defaults=dict(
                    sl_ba_unit_type='BasicPropertyUnit',
                    sl_ba_unit_name=land_name,
                    status=True,
                ),
            )

            # -- la_admin_source + la_rrr (create once if no RRR yet) --------
            if not LA_RRR_Model.objects.filter(ba_unit_id=ba).exists():
                adm_src = LA_Admin_Source_Model.objects.create(
                    admin_source_type='DeedOfTransfer',
                    done_by=user_id,
                    status=True,
                )
                LA_RRR_Model.objects.create(
                    ba_unit_id=ba,
                    admin_source_id=adm_src,
                    pid=owner,
                    share_type='FULL',
                    share=Decimal('1.00'),
                    rrr_type='RIGHT',
                    time_begin=date(rng.randint(2000, 2023), 1, 1),
                    description=f'Freehold ownership of {land_name}',
                )

            # -- building (every 4th parcel) ---------------------------------
            if idx in BUILDING_PARCEL_IDXS:
                self._create_building(
                    bldg_idx=bldg_counter,
                    su_id=su_id,
                    parent_su=su,
                    owner=owner,
                    user_id=user_id,
                    org_id=org_id,
                )
                bldg_counter += 1

            self.stdout.write(
                f'  [{idx + 1:2d}/40] su_id={su_id}  land_name="{land_name}"'
                + (f'  +building' if idx in BUILDING_PARCEL_IDXS else '')
            )

        self.stdout.write(f'\n  [OK] 40 land parcels filled, {bldg_counter} buildings created.')

    # -------------------------------------------------------------------------
    def _create_building(self, bldg_idx, su_id, parent_su, owner, user_id, org_id):
        bsu_id = BLDG_SU_START + bldg_idx
        rng    = random.Random(bsu_id)
        bname  = BUILDING_NAMES[bldg_idx]

        # Skip if building already exists
        if Survey_Rep_DATA_Model.objects.filter(su_id=bsu_id).exists():
            self.stdout.write(f'       +- [SKIP] Building su_id={bsu_id} already exists')
            return

        # Derive building polygon from parent parcel extent (inner 60%, centred)
        parent_sr = Survey_Rep_DATA_Model.objects.filter(su_id=su_id).first()
        if parent_sr:
            ext = parent_sr.geom.extent   # (min_lon, min_lat, max_lon, max_lat)
            w   = ext[2] - ext[0]
            h   = ext[3] - ext[1]
            inset_x, inset_y = w * 0.20, h * 0.20
            bmin_lon = ext[0] + inset_x
            bmin_lat = ext[1] + inset_y
            bmax_lon = ext[2] - inset_x
            bmax_lat = ext[3] - inset_y
            bldg_geom = GEOSGeometry(
                f'SRID=4326;POLYGON(('
                f'{bmin_lon} {bmin_lat}, {bmax_lon} {bmin_lat}, {bmax_lon} {bmax_lat}, '
                f'{bmin_lon} {bmax_lat}, {bmin_lon} {bmin_lat}'
                f'))',
                srid=4326,
            )
            bldg_area = round(w * 0.60 * 109_690 * h * 0.60 * 110_574, 4)
        else:
            # Fallback: tiny polygon near Kandy centre
            bldg_geom = GEOSGeometry(
                'SRID=4326;POLYGON((80.988 6.826, 80.9881 6.826, 80.9881 6.8261, 80.988 6.8261, 80.988 6.826))',
                srid=4326,
            )
            bldg_area = 0.0

        floors = rng.randint(1, 4)

        # survey_rep
        Survey_Rep_DATA_Model.objects.create(
            su_id=bsu_id,
            user_id=user_id,
            layer_id=3,
            infobhoomi_id=f'BU-{bsu_id}',
            geom_type='Polygon',
            area=Decimal(str(round(bldg_area, 4))),
            dimension_2d_3d='2D',
            reference_coordinate=GEOSGeometry(
                f'SRID=4326;POINT({(bldg_geom.extent[0] + bldg_geom.extent[2]) / 2} '
                f'{(bldg_geom.extent[1] + bldg_geom.extent[3]) / 2})',
                srid=4326,
            ),
            geom=bldg_geom,
            status=True,
            ref_id=parent_su.su_id,
            gnd_id=None,
            org_id=org_id,
        )

        # la_spatial_unit
        bsu = LA_Spatial_Unit_Model.objects.create(
            su_id=bsu_id,
            status=True,
            ladm_value='BuildingUnit',
            label=f'BU-{bsu_id}',
            util_obj_id=bsu_id,
            util_obj_code='BLDG',
        )

        # la_ls_build_unit
        LA_LS_Build_Unit_Model.objects.create(
            su_id=bsu,
            access_road='Yes',
            postal_ad_build=ADDRESSES[bldg_idx % len(ADDRESSES)],
            house_hold_no=f'H-{bsu_id}',
            no_floors=floors,
            ext_builduse_type=rng.choice(['Residential', 'Commercial', 'Mixed']),
            ext_builduse_sub_type=rng.choice(['Single Family', 'Multi Family', 'Office', 'Retail', 'Mixed Use']),
            surface_relation='OnSurface',
            hight=Decimal(str(floors * 3)),
            roof_type=rng.choice(ROOF_TYPES),
            wall_type=rng.choice(WALL_TYPES),
            building_name=bname,
            bld_property_type=rng.choice(['Residential', 'Commercial', 'Mixed']),
            registration_date=date(rng.randint(2005, 2022), rng.randint(1, 12), rng.randint(1, 28)),
            construction_year=rng.randint(2000, 2022),
            structure_type=rng.choice(STRUCTURE_TYPES),
            condition=rng.choice(CONDITIONS),
            status=True,
        )

        # assessment
        bld_val    = Decimal(str(rng.randint(5_000_000, 25_000_000)))
        market_val = (bld_val * Decimal('1.15')).quantize(Decimal('0.01'))
        Assessment_Model.objects.create(
            su_id=bsu,
            assessment_no=f'ASS-{bsu_id}',
            assessment_annual_value=(bld_val * Decimal('0.04')).quantize(Decimal('0.01')),
            assessment_percentage=Decimal('4.00'),
            date_of_valuation=date(rng.randint(2018, 2024), rng.randint(1, 12), 1),
            year_of_assessment=str(rng.randint(2020, 2024)),
            property_type='Building',
            assessment_name=bname,
            land_value=bld_val,
            market_value=market_val,
            tax_status=rng.choice(['paid', 'paid', 'pending', 'overdue']),
        )

        # tax_info
        Tax_Info_Model.objects.create(
            su_id=bsu,
            tax_no=f'TAX-{bsu_id}',
            tax_annual_value=(bld_val * Decimal('0.025')).quantize(Decimal('0.01')),
            tax_percentage=Decimal('2.50'),
            tax_date=date(rng.randint(2020, 2025), 1, 1),
            tax_type='Building Tax',
            tax_name=bname,
        )

        # sl_ba_unit + la_rrr
        b_ba = SL_BA_Unit_Model.objects.create(
            su_id=bsu,
            sl_ba_unit_type='BuildingUnit',
            sl_ba_unit_name=bname,
            status=True,
        )

        b_adm_src = LA_Admin_Source_Model.objects.create(
            admin_source_type='BuildingPermit',
            done_by=user_id,
            status=True,
        )

        LA_RRR_Model.objects.create(
            ba_unit_id=b_ba,
            admin_source_id=b_adm_src,
            pid=owner,
            share_type='FULL',
            share=Decimal('1.00'),
            rrr_type='RIGHT',
            time_begin=date(rng.randint(2005, 2022), 1, 1),
            description=f'Ownership of {bname}',
        )

        # la_ls_utinet_bu
        LA_LS_Utinet_BU_Model.objects.create(
            su_id=bsu,
            water=rng.choice(['Connected', 'Connected', 'Not Connected']),
            water_drink=rng.choice(['Connected', 'Not Connected']),
            elec=rng.choice(['Connected', 'Connected', 'Not Connected']),
            tele=rng.choice(['Connected', 'Not Connected']),
            internet=rng.choice(['Connected', 'Not Connected', 'Not Connected']),
            sani_sewer=rng.choice(['Sewer', 'Septic Tank', 'None']),
            sani_gully=rng.choice(['Pit Latrine', 'Septic Tank', 'None']),
            garbage_dispose=rng.choice(['Municipal', 'Private', 'Burning']),
            drainage=rng.choice(['Storm Drain', 'Open Channel', 'No Drainage']),
            status=True,
        )

        self.stdout.write(f'       +- Building su_id={bsu_id}  "{bname}"  floors={floors}')
