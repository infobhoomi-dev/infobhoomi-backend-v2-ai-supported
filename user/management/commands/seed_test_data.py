"""
Management command: seed_test_data
----------------------------------
Clears all parcel / spatial data from the database and seeds:
  - 30 land parcels arranged in a 6x5 grid around Kandy, Sri Lanka
  - 10 buildings placed inside selected parcels
  - Full attribute data for every entity (assessment, tax, RRR, zoning, etc.)

Usage:
    python manage.py seed_test_data          # prompts for confirmation
    python manage.py seed_test_data --yes    # skips confirmation
"""

import random
from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.contrib.gis.geos import GEOSGeometry

from user.models import (
    LA_Spatial_Unit_Model,
    LA_LS_Land_Unit_Model,
    LA_LS_Build_Unit_Model,
    LA_LS_Utinet_BU_Model,
    Survey_Rep_DATA_Model,
    Assessment_Model,
    Tax_Info_Model,
    SL_BA_Unit_Model,
    LA_Admin_Source_Model,
    LA_RRR_Model,
    Party_Model,
    LA_LS_Zoning_Model,
    LA_LS_Physical_Env_Model,
)

# ---- Grid layout --------------------------------------------------------------------------------------------------------------------------
# Base location: Kandy, Sri Lanka  (lon, lat - WGS84 / SRID 4326)
BASE_LON = 80.6340
BASE_LAT = 7.2910

PARCEL_W = 0.00015   # ~16.5 m width per parcel
PARCEL_H = 0.00018   # ~19.9 m height per parcel
GAP      = 0.00003   # ~3.3 m lane/alley between parcels

COLS = 6
ROWS = 5
NUM_PARCELS = COLS * ROWS   # 30

# Approximate metres-per-degree at this latitude
M_PER_DEG_LON = 109_690   # cos(7.29 ) x 111,320
M_PER_DEG_LAT = 110_574

# Indices of parcels (0-based) that will also receive a building footprint
BUILDING_PARCEL_IDXS = {0, 2, 5, 8, 11, 14, 17, 20, 23, 26}   # 10 buildings

# Starting su_ids (well above zero to avoid clashing with any existing data)
LAND_SU_START = 1001
BLDG_SU_START = 2001

# ---- Lookup choices ----------------------------------------------------------------------------------------------------------------------
LAND_NAMES = [
    "Perera Gardens", "Lotus Meadow", "Kandy View Plot", "Highland Terrace",
    "River Valley Land", "Green Pastures", "Summit Property", "Palm Estate",
    "Meadow Land", "Sunrise Plot", "City Boundary Land", "Rock Field",
    "Forest Edge Plot", "Hill Top Land", "Valley View Estate", "Old Town Parcel",
    "Bridge View Land", "Temple Surrounds", "Market Corner Plot", "School Road Land",
    "Heritage Property", "Lakeside Terrace", "Garden Estate", "Mountain View Land",
    "Town Centre Plot", "Civic Quarter", "Agricultural Reserve", "Commercial Frontage",
    "Residential Block", "Industrial Zone Plot",
]

BUILDING_NAMES = [
    "Perera Residence", "Green Villa", "Kandy House", "Hillside Home",
    "Valley View Building", "Sunrise Apartments", "Garden House", "Mountain Lodge",
    "Lotus Building", "Heritage House",
]

ADDRESSES = [
    "12, Kandy Road, Peradeniya",
    "45, Temple Street, Kandy",
    "8, Hill View Road, Katugastota",
    "23, Rajapihilla Mawatha, Kandy",
    "67, Vihara Lane, Kandy",
]

LAND_TYPES    = ['Freehold', 'Leasehold', 'State_Land', 'Private']
LANDUSE_TYPES = ['Residential', 'Commercial', 'Agricultural', 'Mixed']
ZONING_CATS   = ['R1', 'R2', 'C1', 'C2', 'MU']
SOIL_TYPES    = ['CLAY', 'SAND', 'LOAM', 'SILT', 'ROCK']
STRUCTURE_TYPES = ['CONC_REINF', 'MASONRY', 'TIMBER', 'STEEL_FRM', 'COMPOSITE']
CONDITIONS    = ['EXCELLENT', 'GOOD', 'FAIR', 'POOR']
ROOF_TYPES    = ['FLAT', 'GABLE', 'HIP', 'SHED']
WALL_TYPES    = ['BRICK', 'CONCRETE', 'TIMBER']
TAX_STATUSES  = ['paid', 'paid', 'paid', 'pending', 'overdue']

# Five synthetic owner records
OWNER_DATA = [
    ('K. Perera',       'Kamal Sunil Perera',        'NIC', '891234567V', 'kamal.perera@seed.lk',    '1989-03-15', 'Male'),
    ('S. Fernando',     'Sunil Asanga Fernando',      'NIC', '781234567V', 'sunil.fernando@seed.lk',  '1978-07-22', 'Male'),
    ('R. Silva',        'Ranjith Kumar Silva',        'NIC', '901234567V', 'ranjith.silva@seed.lk',   '1990-11-05', 'Male'),
    ('A. Bandara',      'Anusha Kumari Bandara',      'NIC', '851234567V', 'anusha.bandara@seed.lk',  '1985-04-18', 'Female'),
    ('M. Jayawardena',  'Mahesh Priya Jayawardena',   'NIC', '921234567V', 'mahesh.j@seed.lk',        '1992-09-30', 'Male'),
]


class Command(BaseCommand):
    help = 'Clear parcel data and seed 30 test land parcels + 10 buildings around Kandy, Sri Lanka'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes', action='store_true',
            help='Skip the confirmation prompt',
        )

    # ---- Entry point --------------------------------------------------------------------------------------------------------------------
    def handle(self, *args, **options):
        if not options['yes']:
            self.stdout.write(self.style.WARNING(
                '\nWARNING: This will TRUNCATE all spatial / parcel data:\n'
                '  survey_rep, la_spatial_unit (cascade), sl_party, la_admin_source,\n'
                '  assessment, tax_info, la_rrr, sl_ba_unit, la_ls_land_unit,\n'
                '  la_ls_build_unit, la_ls_zoning, la_ls_physical_env, and more.\n'
            ))
            confirm = input('Type  YES  to continue: ').strip()
            if confirm != 'YES':
                self.stdout.write('Aborted - nothing was changed.')
                return

        # Need a real user_id and org_id for survey_rep records
        try:
            from user.models import User
        except ImportError:
            from django.contrib.auth import get_user_model
            User = get_user_model()

        first_user = User.objects.order_by('id').first()
        if not first_user:
            self.stdout.write(self.style.ERROR(
                'No users found in the database. Create a superuser first:\n'
                '  python manage.py createsuperuser'
            ))
            return

        user_id = first_user.id
        org_id  = int(getattr(first_user, 'org_id', None) or 1)
        self.stdout.write(f'Using user_id={user_id}, org_id={org_id}  ({first_user.username})\n')

        with transaction.atomic():
            self._clear_data()
            parties = self._create_parties(user_id)
            self._create_parcels(parties, user_id, org_id)

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Done!  {NUM_PARCELS} land parcels and {len(BUILDING_PARCEL_IDXS)} buildings created.\n'
            f'  Location: Kandy, Sri Lanka  ({BASE_LAT:.4f}N, {BASE_LON:.4f}E)\n'
            f'  Land su_ids : {LAND_SU_START} to {LAND_SU_START + NUM_PARCELS - 1}\n'
            f'  Bldg su_ids : {BLDG_SU_START} to {BLDG_SU_START + len(BUILDING_PARCEL_IDXS) - 1}\n'
        ))

    # ---- Step 1 - clear --------------------------------------------------------------------------------------------------------------
    def _clear_data(self):
        self.stdout.write('Clearing existing spatial data ...')
        tables = [
            'la_rrr_restriction',
            'la_rrr_responsibility',
            'la_rrr',
            'sl_party_roles',
            'residence_info',
            'la_admin_source',
            'sl_ba_unit',
            'assessment',
            'tax_info',
            'la_ls_land_unit',
            'la_ls_build_unit',
            'la_ls_zoning',
            'la_ls_physical_env',
            'survey_rep',
            'la_spatial_unit',
            'sl_party',
        ]
        with connection.cursor() as cur:
            cur.execute(
                'TRUNCATE TABLE {} RESTART IDENTITY CASCADE'.format(
                    ', '.join(f'"{t}"' for t in tables)
                )
            )
        self.stdout.write('  [OK] All tables cleared.\n')

    # ---- Step 2 - parties ----------------------------------------------------------------------------------------------------------
    def _create_parties(self, done_by):
        self.stdout.write('Creating owner parties ...')
        parties = []
        for name, full_name, pid_type, pid_val, email, dob, gender in OWNER_DATA:
            p = Party_Model.objects.create(
                party_name=name,
                party_full_name=full_name,
                la_party_type='NATURAL',
                sl_party_type='INDIVIDUAL',
                ext_pid_type=pid_type,
                ext_pid=pid_val,
                email=email,
                date_of_birth=date.fromisoformat(dob),
                gender=gender,
                done_by=done_by,
            )
            parties.append(p)
        self.stdout.write(f'  [OK] {len(parties)} parties created.\n')
        return parties

    # ---- Step 3 - parcels ----------------------------------------------------------------------------------------------------------
    def _create_parcels(self, parties, user_id, org_id):
        self.stdout.write('Creating land parcels ...')
        bldg_counter = 0

        for i in range(NUM_PARCELS):
            col   = i % COLS
            row   = i // COLS
            su_id = LAND_SU_START + i
            owner = parties[i % len(parties)]
            rng   = random.Random(i)   # deterministic per parcel index

            # ---- geometry --------------------------------------------------------------------------------------------------------
            parcel_geom, area_m2, clon, clat = self._parcel_polygon(col, row)

            # ---- survey_rep ----------------------------------------------------------------------------------------------------
            Survey_Rep_DATA_Model.objects.create(
                su_id=su_id,
                user_id=user_id,
                layer_id=1,
                infobhoomi_id=f'LP-{su_id}',
                geom_type='Polygon',
                area=Decimal(str(round(area_m2, 4))),
                dimension_2d_3d='2D',
                reference_coordinate=GEOSGeometry(f'SRID=4326;POINT({clon} {clat})'),
                geom=parcel_geom,
                status=True,
                gnd_id=None,
                org_id=org_id,
            )

            # ---- la_spatial_unit ------------------------------------------------------------------------------------------
            su = LA_Spatial_Unit_Model.objects.create(
                su_id=su_id,
                status=True,
                ladm_value='LandParcel',
                label=f'LP-{su_id}',
                util_obj_id=su_id,
                util_obj_code='LAND',
            )

            # ---- la_ls_land_unit ------------------------------------------------------------------------------------------
            LA_LS_Land_Unit_Model.objects.create(
                su_id=su,
                access_road=rng.choice(['Yes', 'Yes', 'Yes', 'No']),
                postal_ad_lnd=ADDRESSES[i % len(ADDRESSES)],
                local_auth='Kandy Municipal Council',
                ext_landuse_type=rng.choice(LANDUSE_TYPES),
                sl_land_type=rng.choice(LAND_TYPES),
                land_name=LAND_NAMES[i],
                registration_date=date(
                    rng.randint(2000, 2023),
                    rng.randint(1, 12),
                    rng.randint(1, 28),
                ),
                status=True,
            )

            # ---- la_ls_zoning ------------------------------------------------------------------------------------------------
            LA_LS_Zoning_Model.objects.create(
                su_id=su,
                zoning_category=rng.choice(ZONING_CATS),
                max_building_height=Decimal(str(rng.randint(6, 20))),
                max_coverage=Decimal(str(round(rng.uniform(0.40, 0.80), 2))),
                max_far=Decimal(str(round(rng.uniform(0.5, 3.0), 2))),
                setback_front=Decimal(str(rng.randint(2, 6))),
                setback_rear=Decimal(str(rng.randint(1, 4))),
                setback_side=Decimal(str(rng.randint(1, 3))),
            )

            # ---- la_ls_physical_env ------------------------------------------------------------------------------------
            LA_LS_Physical_Env_Model.objects.create(
                su_id=su,
                elevation=Decimal(str(round(rng.uniform(450, 530), 1))),
                slope=Decimal(str(round(rng.uniform(0, 15), 1))),
                soil_type=rng.choice(SOIL_TYPES),
                flood_zone=rng.random() < 0.1,   # 10% chance
                vegetation_cover=rng.choice(['Dense', 'Sparse', 'None', 'Moderate']),
            )

            # ---- assessment ----------------------------------------------------------------------------------------------------
            land_val   = Decimal(str(rng.randint(3_000_000, 15_000_000)))
            market_val = (land_val * Decimal('1.2')).quantize(Decimal('0.01'))
            Assessment_Model.objects.create(
                su_id=su,
                assessment_no=f'ASS-{su_id}',
                ass_road=ADDRESSES[i % len(ADDRESSES)],
                assessment_annual_value=(land_val * Decimal('0.05')).quantize(Decimal('0.01')),
                assessment_percentage=Decimal('5.00'),
                date_of_valuation=date(rng.randint(2018, 2024), rng.randint(1, 12), 1),
                year_of_assessment=str(rng.randint(2020, 2024)),
                property_type='Land',
                assessment_name=LAND_NAMES[i],
                land_value=land_val,
                market_value=market_val,
                tax_status=rng.choice(TAX_STATUSES),
            )

            # ---- tax_info --------------------------------------------------------------------------------------------------------
            Tax_Info_Model.objects.create(
                su_id=su,
                tax_no=f'TAX-{su_id}',
                tax_annual_value=(land_val * Decimal('0.03')).quantize(Decimal('0.01')),
                tax_percentage=Decimal('3.00'),
                tax_date=date(rng.randint(2020, 2025), 1, 1),
                tax_type='Property Tax',
                tax_name=LAND_NAMES[i],
            )

            # ---- sl_ba_unit ----------------------------------------------------------------------------------------------------
            ba = SL_BA_Unit_Model.objects.create(
                su_id=su,
                sl_ba_unit_type='BasicPropertyUnit',
                sl_ba_unit_name=LAND_NAMES[i],
                status=True,
            )

            # ---- la_admin_source ------------------------------------------------------------------------------------------
            adm_src = LA_Admin_Source_Model.objects.create(
                admin_source_type='DeedOfTransfer',
                done_by=user_id,
                status=True,
            )

            # ---- la_rrr ------------------------------------------------------------------------------------------------------------
            LA_RRR_Model.objects.create(
                ba_unit_id=ba,
                admin_source_id=adm_src,
                pid=owner,
                share_type='FULL',
                share=Decimal('1.00'),
                rrr_type='RIGHT',
                time_begin=date(rng.randint(2000, 2023), 1, 1),
                description=f'Freehold ownership of {LAND_NAMES[i]}',
            )

            # ---- building (for selected parcels) ----------------------------------------------------------
            if i in BUILDING_PARCEL_IDXS:
                self._create_building(
                    bldg_idx=bldg_counter,
                    col=col, row=row,
                    parent_su=su,
                    owner=owner,
                    user_id=user_id,
                    org_id=org_id,
                )
                bldg_counter += 1

            self.stdout.write(f'  Parcel {i + 1:2d}/{NUM_PARCELS}  su_id={su_id}  {LAND_NAMES[i]}')

        self.stdout.write(f'\n  [OK] {NUM_PARCELS} land parcels created.')

    # ---- Helper - building --------------------------------------------------------------------------------------------------------
    def _create_building(self, bldg_idx, col, row, parent_su, owner, user_id, org_id):
        bsu_id = BLDG_SU_START + bldg_idx
        rng    = random.Random(1000 + bldg_idx)

        bldg_geom, bldg_area = self._building_polygon(col, row)

        Survey_Rep_DATA_Model.objects.create(
            su_id=bsu_id,
            user_id=user_id,
            layer_id=3,
            infobhoomi_id=f'BU-{bsu_id}',
            geom_type='Polygon',
            area=Decimal(str(round(bldg_area, 4))),
            dimension_2d_3d='2D',
            geom=bldg_geom,
            status=True,
            ref_id=parent_su.su_id,   # link to parent land parcel
            gnd_id=None,
            org_id=org_id,
        )

        bsu = LA_Spatial_Unit_Model.objects.create(
            su_id=bsu_id,
            status=True,
            ladm_value='BuildingUnit',
            label=f'BU-{bsu_id}',
            util_obj_id=bsu_id,
            util_obj_code='BLDG',
        )

        floors = rng.randint(1, 4)
        LA_LS_Build_Unit_Model.objects.create(
            su_id=bsu,
            access_road='Yes',
            postal_ad_build=ADDRESSES[bldg_idx % len(ADDRESSES)],
            house_hold_no=f'H-{bsu_id}',
            no_floors=floors,
            ext_builduse_type=rng.choice(['Residential', 'Commercial', 'Mixed']),
            surface_relation='OnSurface',
            hight=Decimal(str(floors * 3)),
            roof_type=rng.choice(ROOF_TYPES),
            wall_type=rng.choice(WALL_TYPES),
            building_name=BUILDING_NAMES[bldg_idx],
            bld_property_type=rng.choice(['Residential', 'Commercial']),
            registration_date=date(rng.randint(2005, 2022), rng.randint(1, 12), rng.randint(1, 28)),
            construction_year=rng.randint(2000, 2022),
            structure_type=rng.choice(STRUCTURE_TYPES),
            condition=rng.choice(CONDITIONS),
            status=True,
        )

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
            assessment_name=BUILDING_NAMES[bldg_idx],
            market_value=market_val,
            tax_status=rng.choice(['paid', 'paid', 'pending']),
        )

        Tax_Info_Model.objects.create(
            su_id=bsu,
            tax_no=f'TAX-{bsu_id}',
            tax_annual_value=(bld_val * Decimal('0.025')).quantize(Decimal('0.01')),
            tax_percentage=Decimal('2.50'),
            tax_date=date(rng.randint(2020, 2025), 1, 1),
            tax_type='Building Tax',
            tax_name=BUILDING_NAMES[bldg_idx],
        )

        b_ba = SL_BA_Unit_Model.objects.create(
            su_id=bsu,
            sl_ba_unit_type='BuildingUnit',
            sl_ba_unit_name=BUILDING_NAMES[bldg_idx],
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
            description=f'Ownership of {BUILDING_NAMES[bldg_idx]}',
        )

        # ---- la_ls_utinet_bu (utility connections) -------------------------
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

        self.stdout.write(f'       +- Building su_id={bsu_id}  {BUILDING_NAMES[bldg_idx]}')

    # ---- Geometry helpers ------------------------------------------------------------------------------------------------------------
    def _parcel_polygon(self, col, row):
        """Return (GEOSGeometry polygon, area_m2, center_lon, center_lat)."""
        min_lon = BASE_LON + col * (PARCEL_W + GAP)
        min_lat = BASE_LAT + row * (PARCEL_H + GAP)
        max_lon = min_lon + PARCEL_W
        max_lat = min_lat + PARCEL_H
        wkt = (
            f'SRID=4326;POLYGON(('
            f'{min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, '
            f'{min_lon} {max_lat}, {min_lon} {min_lat}'
            f'))'
        )
        area_m2 = PARCEL_W * M_PER_DEG_LON * PARCEL_H * M_PER_DEG_LAT
        return (
            GEOSGeometry(wkt),
            area_m2,
            (min_lon + max_lon) / 2,
            (min_lat + max_lat) / 2,
        )

    def _building_polygon(self, col, row):
        """Return (GEOSGeometry polygon, area_m2) - building footprint at 60% of parcel, centred."""
        inset_x = PARCEL_W * 0.20
        inset_y = PARCEL_H * 0.20
        min_lon = BASE_LON + col * (PARCEL_W + GAP) + inset_x
        min_lat = BASE_LAT + row * (PARCEL_H + GAP) + inset_y
        max_lon = min_lon + PARCEL_W * 0.60
        max_lat = min_lat + PARCEL_H * 0.60
        wkt = (
            f'SRID=4326;POLYGON(('
            f'{min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, '
            f'{min_lon} {max_lat}, {min_lon} {min_lat}'
            f'))'
        )
        area_m2 = PARCEL_W * 0.60 * M_PER_DEG_LON * PARCEL_H * 0.60 * M_PER_DEG_LAT
        return GEOSGeometry(wkt), area_m2
