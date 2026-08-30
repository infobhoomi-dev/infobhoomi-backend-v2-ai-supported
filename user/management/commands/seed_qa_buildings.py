"""
Management command: seed_qa_buildings
======================================
Additive-only QA fixture for the GIS Query Console "Buildings" category and the
building-related "FAR / Coverage Violations" / "Revenue & Tax" queries.

Does NOT touch any existing row. Creates a fixed, easily-removable batch of
fully-wired building records (survey_rep -> la_spatial_unit -> la_ls_build_unit
-> assessment) with su_id in the reserved range 90001-90020, so it is safe to
run against a live database and trivial to clean up again.

Usage:
    python manage.py seed_qa_buildings              # create the batch
    python manage.py seed_qa_buildings --cleanup     # remove exactly this batch
    python manage.py seed_qa_buildings --org-id 2 --user-id 113
"""

from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry

from user.models import (
    Survey_Rep_DATA_Model,
    LA_Spatial_Unit_Model,
    LA_LS_Build_Unit_Model,
    Assessment_Model,
    Tax_Info_Model,
)

SU_ID_START = 90001  # reserved block, clear of any real data (max real su_id ~15859)

# lon, lat placed just east of the existing Kandy test cluster so it never overlaps
BASE_LON = 80.6420
BASE_LAT = 7.2910
STEP_LON = 0.00060

# Each row: (building_name, no_floors, condition, area_m2, far, coverage_pct,
#            market_value, assessment_annual_value, tax_status, structure_type)
BUILDINGS = [
    ("QA Tower Alpha",       9,  "GOOD",      650,  2.8, 72,  15_000_000, 620_000,  "paid",    "STEEL_FRM"),
    ("QA Residence Beta",    2,  "POOR",      180,  1.2, 45,   4_500_000, 190_000,  "overdue", "MASONRY"),
    ("QA Complex Gamma",     12, "EXCELLENT", 1200, 3.5, 80,  45_000_000, 1_850_000, "paid",   "CONC_REINF"),
    ("QA Villa Delta",       1,  "FAIR",      220,  0.8, 35,   6_000_000, 260_000,  "pending", "TIMBER"),
    ("QA Mansion Epsilon",   3,  "DILAPID",   310,  1.5, 55,   3_200_000, 140_000,  "overdue", "MASONRY"),
    ("QA Highrise Zeta",     15, "GOOD",      2000, 4.0, 85,  80_000_000, 3_300_000, "paid",   "STEEL_FRM"),
    ("QA Cottage Eta",       1,  "EXCELLENT", 95,   0.4, 20,   2_100_000, 30_000,   "paid",    "TIMBER"),
    ("QA Apartments Theta",  6,  "FAIR",      780,  2.6, 68,  22_000_000, 910_000,  "overdue", "COMPOSITE"),
    ("QA Office Iota",       5,  "GOOD",      560,  2.9, 70,  18_500_000, 760_000,  "pending", "STEEL_FRM"),
    ("QA Shed Kappa",        1,  "POOR",      45,   0.2, 15,     850_000, 12_000,   "overdue", "TIMBER"),
    ("QA Tower Lambda",      20, "EXCELLENT", 3200, 5.2, 90, 120_000_000, 4_950_000, "paid",   "CONC_REINF"),
    ("QA Bungalow Mu",       1,  "GOOD",      140,  0.6, 30,   3_800_000, 165_000,  "paid",    "MASONRY"),
]

# Approx metres-per-degree at this latitude (Kandy)
M_PER_DEG_LON = 109_690
M_PER_DEG_LAT = 110_574


class Command(BaseCommand):
    help = 'Additive QA fixture: fully-wired building records for the Query Console "Buildings" category'

    def add_arguments(self, parser):
        parser.add_argument('--org-id', type=int, default=2)
        parser.add_argument('--user-id', type=int, default=None,
                             help='Defaults to the first user found in --org-id')
        parser.add_argument('--cleanup', action='store_true',
                             help='Delete exactly the su_id range this command creates, then exit')

    def handle(self, *args, **options):
        org_id = options['org_id']
        su_ids = list(range(SU_ID_START, SU_ID_START + len(BUILDINGS)))

        if options['cleanup']:
            self._cleanup(su_ids)
            return

        user_id = options['user_id']
        if user_id is None:
            from user.models import User
            u = User.objects.filter(org_id=org_id).order_by('id').first()
            if not u:
                self.stdout.write(self.style.ERROR(f'No users found with org_id={org_id}'))
                return
            user_id = u.id
            self.stdout.write(f'Using user_id={user_id} ({u.username}) for org_id={org_id}')

        existing = set(LA_Spatial_Unit_Model.objects.filter(su_id__in=su_ids).values_list('su_id', flat=True))
        if existing:
            self.stdout.write(self.style.WARNING(
                f'su_ids already present, skipping to avoid duplicates: {sorted(existing)}\n'
                f'Run with --cleanup first if you want to reseed.'
            ))
            return

        with transaction.atomic():
            for i, (name, floors, condition, area, far, coverage, market_val, ass_val, tax_status, structure) in enumerate(BUILDINGS):
                su_id = SU_ID_START + i
                geom, real_area = self._footprint(i, area)

                su = LA_Spatial_Unit_Model.objects.create(
                    su_id=su_id,
                    status=True,
                    label=name,
                )

                Survey_Rep_DATA_Model.objects.create(
                    su_id_id=su_id,
                    user_id=user_id,
                    layer_id=3,
                    geom_type='Polygon',
                    calculated_area=Decimal(str(round(real_area, 4))),
                    dimension_2d_3d='2D',
                    geom=geom,
                    status=True,
                    org_id=org_id,
                )

                LA_LS_Build_Unit_Model.objects.create(
                    su_id=su,
                    building_name=name,
                    no_floors=floors,
                    condition=condition,
                    structure_type=structure,
                    floor_area_ratio=Decimal(str(far)),
                    plot_coverage=Decimal(str(coverage)),
                    construction_year=2000 + i,
                    roof_type='FLAT',
                    wall_type='BRICK',
                    ext_builduse_type='Residential' if 'Residence' in name or 'Villa' in name or 'Cottage' in name or 'Bungalow' in name else 'Commercial',
                    hight=Decimal(str(floors * 3)),
                    registration_date=date(2000 + i, (i % 12) + 1, 10),
                    status=True,
                )

                Assessment_Model.objects.create(
                    su_id=su,
                    assessment_no=f'QA-ASS-{su_id}',
                    assessment_annual_value=Decimal(str(ass_val)),
                    assessment_percentage=Decimal('4.00'),
                    date_of_valuation=date(2023, 1, 1),
                    year_of_assessment='2023',
                    property_type='Building',
                    assessment_name=name,
                    market_value=Decimal(str(market_val)),
                    tax_status=tax_status,
                    user_id=user_id,
                )

                Tax_Info_Model.objects.create(
                    su_id=su,
                    tax_annual_value=(Decimal(str(market_val)) * Decimal('0.01')).quantize(Decimal('0.01')),
                    tax_percentage=Decimal('1.00'),
                    tax_date=date(2024, 1, 1),
                    tax_type='Building Tax',
                )

                self.stdout.write(f'  su_id={su_id}  {name}  floors={floors} cond={condition} '
                                   f'area={real_area:.0f}m2 far={far} cov={coverage}% tax={tax_status}')

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Seeded {len(BUILDINGS)} QA buildings for org_id={org_id}, su_id {su_ids[0]}-{su_ids[-1]}.\n'
            f'Remove again with: python manage.py seed_qa_buildings --cleanup'
        ))

    def _cleanup(self, su_ids):
        self.stdout.write(f'Removing QA buildings su_id {su_ids[0]}-{su_ids[-1]} ...')
        with transaction.atomic():
            n1 = Assessment_Model.objects.filter(su_id_id__in=su_ids).delete()[0]
            n2 = Tax_Info_Model.objects.filter(su_id_id__in=su_ids).delete()[0]
            n3 = LA_LS_Build_Unit_Model.objects.filter(su_id_id__in=su_ids).delete()[0]
            n4 = Survey_Rep_DATA_Model.objects.filter(su_id_id__in=su_ids).delete()[0]
            n5 = LA_Spatial_Unit_Model.objects.filter(su_id__in=su_ids).delete()[0]
        self.stdout.write(self.style.SUCCESS(
            f'[OK] Removed: {n1} assessment, {n2} tax_info, {n3} build_unit, {n4} survey_rep, {n5} spatial_unit rows.'
        ))

    def _footprint(self, idx, area_m2):
        """Square footprint of the requested area, placed along a line east of the real cluster."""
        side_deg_lon = (area_m2 ** 0.5) / M_PER_DEG_LON
        side_deg_lat = (area_m2 ** 0.5) / M_PER_DEG_LAT
        min_lon = BASE_LON + idx * STEP_LON
        min_lat = BASE_LAT
        max_lon = min_lon + side_deg_lon
        max_lat = min_lat + side_deg_lat
        wkt = (
            f'SRID=4326;POLYGON(('
            f'{min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, '
            f'{min_lon} {max_lat}, {min_lon} {min_lat}'
            f'))'
        )
        real_area_m2 = (side_deg_lon * M_PER_DEG_LON) * (side_deg_lat * M_PER_DEG_LAT)
        return GEOSGeometry(wkt), real_area_m2
