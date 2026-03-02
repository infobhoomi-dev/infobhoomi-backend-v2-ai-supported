"""
Management command: seed_land_data
====================================
Populates LA_LS_Land_Unit_Model and Assessment_Model with realistic arbitrary
data for all existing land-layer Survey_Rep records, and computes actual areas
from the stored geometries.

Usage:
    python manage.py seed_land_data
    python manage.py seed_land_data --org-id 2       # target a specific org
    python manage.py seed_land_data --dry-run         # show stats without writing
"""

import random
import datetime
from django.core.management.base import BaseCommand
from django.db import connection
from user.models import Survey_Rep_DATA_Model, LA_LS_Land_Unit_Model, Assessment_Model

# ── Realistic Sri Lankan data pools ──────────────────────────────────────────

LAND_TYPES = [
    'Residential',
    'Residential',
    'Residential',   # weighted heavier
    'Commercial',
    'Commercial',
    'Industrial',
    'Agricultural',
    'Agricultural',
    'Mixed Use',
    'Vacant',
]

STREETS = [
    'Kandy Road', 'Peradeniya Road', 'Colombo Road', 'Rajapihilla Mawatha',
    'Dalada Veediya', 'Trincomalee Street', 'Sandagala Road', 'Temple Road',
    'Main Street', 'Station Road', 'Hospital Road', 'DS Senanayake Veediya',
    'Ampitiya Road', 'Dharmaraja Road', 'Torrington Avenue', 'Yatinuwara Road',
    'Buwelikada Road', 'Katugastota Road', 'Wattegama Road', 'Galaha Road',
    'Lady Gordon Drive', 'Madawala Road', 'Lewella Road', 'Teldeniya Road',
]

CITIES = [
    'Kandy', 'Kandy', 'Kandy',   # weighted
    'Peradeniya', 'Katugastota', 'Kundasale', 'Ampitiya',
    'Gampola', 'Nawalapitiya', 'Matale', 'Dambulla',
    'Pilimathalawa', 'Theldeniya', 'Akurana', 'Wattegama',
    'Daulagala', 'Madawala', 'Digana', 'Rajawella',
]

LOCAL_AUTHS = [
    'Kandy Municipal Council',
    'Kandy Municipal Council',
    'Kandy Municipal Council',   # dominant
    'Kundasale Pradeshiya Sabha',
    'Peradeniya Pradeshiya Sabha',
    'Katugastota Urban Council',
    'Gampola Municipal Council',
    'Akurana Urban Council',
    'Pilimathalawa Pradeshiya Sabha',
    'Wattegama Pradeshiya Sabha',
    'Harispattuwa Pradeshiya Sabha',
    'Yatinuwara Pradeshiya Sabha',
]

FAMILY_NAMES = [
    'Perera', 'Silva', 'Fernando', 'Rajapaksa', 'Bandara', 'Jayawardena',
    'Gunawardena', 'Herath', 'Wickramasinghe', 'Dissanayake', 'Weerasinghe',
    'Rathnayake', 'Kumarasinghe', 'Seneviratne', 'Wijesinghe', 'Pathirana',
    'Karunanayake', 'Madushan', 'Gamage', 'Hettiarachchi', 'Amarasinghe',
    'Thilakaratne', 'Samaraweera', 'Liyanage', 'Premaratne', 'Mendis',
]

LAND_SUFFIXES = [
    'Gardens', 'Estate', 'Residence', 'Holdings', 'Farm', 'Property',
    'Land', 'Plot', 'Villa', 'Plantation', 'Homestead', 'Lot',
]

EXT_LANDUSE_TYPES = [
    'Residential', 'Commercial', 'Industrial', 'Agricultural', 'Institutional',
    'Mixed Use', 'Recreational', 'Conservation',
]

EXT_LANDUSE_SUBTYPES = {
    'Residential':   ['Low Density', 'Medium Density', 'High Density', 'Apartment'],
    'Commercial':    ['Retail', 'Office', 'Hotel', 'Mixed Commercial'],
    'Industrial':    ['Light Industry', 'Heavy Industry', 'Warehouse', 'Agro-Industry'],
    'Agricultural':  ['Paddy', 'Home Garden', 'Tea Estate', 'Rubber', 'Mixed Crops'],
    'Institutional': ['School', 'Hospital', 'Government', 'Religious'],
    'Mixed Use':     ['Residential-Commercial', 'Residential-Agricultural'],
    'Recreational':  ['Park', 'Sports Ground', 'Open Space'],
    'Conservation':  ['Forest', 'Wetland', 'Buffer Zone'],
}

PROPERTY_TYPES = ['Land', 'Land', 'Land', 'Land and Buildings', 'Agricultural']

TAX_WEIGHTS = ['paid'] * 60 + ['pending'] * 25 + ['overdue'] * 15


class Command(BaseCommand):
    help = 'Seed arbitrary land parcel data for all parcels in land layers (1, 6)'

    def add_arguments(self, parser):
        parser.add_argument('--org-id', type=int, default=None,
                            help='Only process parcels for this org (default: all)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Print summary without writing to DB')
        parser.add_argument('--seed', type=int, default=42,
                            help='Random seed for reproducibility (default: 42)')

    def handle(self, *args, **options):
        org_id = options['org_id']
        dry_run = options['dry_run']
        random.seed(options['seed'])

        # ── Step 1: Compute areas from actual geometry ─────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('Step 1: Computing areas from geometry…'))
        if not dry_run:
            org_filter = f"AND org_id = {org_id}" if org_id else ""
            with connection.cursor() as cur:
                cur.execute(f"""
                    UPDATE survey_rep
                    SET area = ST_Area(ST_Transform(geom::geometry, 32644))
                    WHERE layer_id IN (1, 6)
                      AND status = true
                      AND geom IS NOT NULL
                      {org_filter}
                """)
                updated_area = cur.rowcount
            self.stdout.write(f'  OK: Updated area for {updated_area} survey records')
        else:
            self.stdout.write('  (dry-run — skip)')

        # ── Step 2: Load existing records ──────────────────────────────────────
        qs = Survey_Rep_DATA_Model.objects.filter(layer_id__in=[1, 6], status=True)
        if org_id:
            qs = qs.filter(org_id=org_id)

        surveys = list(qs.values('id', 'su_id_id', 'area', 'org_id'))
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Step 2: Processing {len(surveys)} land parcel records…'))

        existing_lu = {lu.su_id_id: lu for lu in LA_LS_Land_Unit_Model.objects.all()}
        existing_ass = {a.su_id_id: a for a in Assessment_Model.objects.all()}

        lu_to_update, lu_to_create = [], []
        ass_to_update, ass_to_create = [], []

        for survey in surveys:
            su_id = survey['su_id_id']
            if su_id is None:
                continue

            # Use su_id as local random seed for deterministic results
            r = random.Random(su_id)

            # ── Land Unit attributes ───────────────────────────────────────────
            land_type = r.choice(LAND_TYPES)
            ext_type = r.choice(EXT_LANDUSE_TYPES)
            ext_subtype = r.choice(EXT_LANDUSE_SUBTYPES[ext_type])
            street_no = r.randint(1, 250)
            street = r.choice(STREETS)
            city = r.choice(CITIES)
            postal = f'{street_no}, {street}, {city}'
            land_name = f'{r.choice(FAMILY_NAMES)} {r.choice(LAND_SUFFIXES)}'
            local_auth = r.choice(LOCAL_AUTHS)
            access_road = 'Yes' if r.random() > 0.2 else 'No'
            reg_year = r.randint(1995, 2022)
            reg_month = r.randint(1, 12)
            reg_day = r.randint(1, 28)
            reg_date = datetime.date(reg_year, reg_month, reg_day)

            if su_id in existing_lu:
                lu = existing_lu[su_id]
                lu.sl_land_type = land_type
                lu.land_name = land_name
                lu.postal_ad_lnd = postal
                lu.local_auth = local_auth
                lu.access_road = access_road
                lu.ext_landuse_type = ext_type
                lu.ext_landuse_sub_type = ext_subtype
                lu.registration_date = reg_date
                lu_to_update.append(lu)
            else:
                lu_to_create.append(LA_LS_Land_Unit_Model(
                    su_id_id=su_id,
                    sl_land_type=land_type,
                    land_name=land_name,
                    postal_ad_lnd=postal,
                    local_auth=local_auth,
                    access_road=access_road,
                    ext_landuse_type=ext_type,
                    ext_landuse_sub_type=ext_subtype,
                    registration_date=reg_date,
                    status=True,
                ))

            # ── Assessment attributes ──────────────────────────────────────────
            area_m2 = float(survey['area'] or 0) or r.uniform(200, 2000)  # fallback if area=0
            # Market value: LKR/m² depends on land type and a random multiplier
            rate_lkr_per_m2 = {
                'Residential':   r.uniform(8_000, 45_000),
                'Commercial':    r.uniform(25_000, 120_000),
                'Industrial':    r.uniform(10_000, 50_000),
                'Agricultural':  r.uniform(1_500, 8_000),
                'Mixed Use':     r.uniform(15_000, 60_000),
                'Vacant':        r.uniform(3_000, 15_000),
            }.get(land_type, r.uniform(5_000, 30_000))

            market_value = round(area_m2 * rate_lkr_per_m2, 2)
            # Clamp to realistic range: LKR 300k – 150M
            market_value = max(300_000.0, min(150_000_000.0, market_value))
            land_value = round(market_value * r.uniform(0.70, 0.85), 2)
            assessment_value = round(market_value * r.uniform(0.04, 0.07), 2)
            tax_status = r.choice(TAX_WEIGHTS)
            prop_type = r.choice(PROPERTY_TYPES)
            ass_no = f'ASS-{su_id:06d}'
            val_year = r.randint(2015, 2022)
            ass_year = str(r.randint(val_year, 2023))

            if su_id in existing_ass:
                a = existing_ass[su_id]
                a.assessment_no = ass_no
                a.ass_road = postal
                a.assessment_annual_value = assessment_value
                a.assessment_percentage = round(r.uniform(4.0, 7.0), 2)
                a.market_value = market_value
                a.land_value = land_value
                a.tax_status = tax_status
                a.assessment_name = land_name
                a.property_type = prop_type
                a.year_of_assessment = ass_year
                a.date_of_valuation = datetime.date(val_year, r.randint(1, 12), r.randint(1, 28))
                a.external_ass_id = f'EXT-{su_id:06d}'
                ass_to_update.append(a)
            else:
                ass_to_create.append(Assessment_Model(
                    su_id_id=su_id,
                    assessment_no=ass_no,
                    ass_road=postal,
                    assessment_annual_value=assessment_value,
                    assessment_percentage=round(r.uniform(4.0, 7.0), 2),
                    market_value=market_value,
                    land_value=land_value,
                    tax_status=tax_status,
                    assessment_name=land_name,
                    property_type=prop_type,
                    year_of_assessment=ass_year,
                    date_of_valuation=datetime.date(val_year, r.randint(1, 12), r.randint(1, 28)),
                    external_ass_id=f'EXT-{su_id:06d}',
                ))

        # ── Step 3: Write to database ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('Step 3: Writing to database…'))

        lu_update_fields = [
            'sl_land_type', 'land_name', 'postal_ad_lnd', 'local_auth',
            'access_road', 'ext_landuse_type', 'ext_landuse_sub_type', 'registration_date',
        ]
        ass_update_fields = [
            'assessment_no', 'ass_road', 'assessment_annual_value', 'assessment_percentage',
            'market_value', 'land_value', 'tax_status', 'assessment_name',
            'property_type', 'year_of_assessment', 'date_of_valuation', 'external_ass_id',
        ]

        if not dry_run:
            if lu_to_update:
                LA_LS_Land_Unit_Model.objects.bulk_update(lu_to_update, lu_update_fields, batch_size=500)
            if lu_to_create:
                LA_LS_Land_Unit_Model.objects.bulk_create(lu_to_create, batch_size=500)
            if ass_to_update:
                Assessment_Model.objects.bulk_update(ass_to_update, ass_update_fields, batch_size=500)
            if ass_to_create:
                Assessment_Model.objects.bulk_create(ass_to_create, batch_size=500)

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Done!'))
        self.stdout.write(f'  Land units  — updated: {len(lu_to_update)}, created: {len(lu_to_create)}')
        self.stdout.write(f'  Assessments — updated: {len(ass_to_update)}, created: {len(ass_to_create)}')

        # Print verification stats
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Verification preview:'))
        from django.db.models import Count
        if not dry_run:
            for row in LA_LS_Land_Unit_Model.objects.values('sl_land_type').annotate(n=Count('id')).order_by('-n'):
                self.stdout.write(f'  sl_land_type={row["sl_land_type"]!r:20s}  count={row["n"]}')
            self.stdout.write('')
            for row in Assessment_Model.objects.values('tax_status').annotate(n=Count('id')).order_by('-n'):
                self.stdout.write(f'  tax_status={row["tax_status"]!r:12s}  count={row["n"]}')
