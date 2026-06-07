"""
Seed the seven lookup tables used by the Land panel's
Physical & Environmental section.

Idempotent: uses get_or_create so re-runs add only missing values.

    python manage.py seed_physical_lookups
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from user.models import (
    Lst_SU_SL_Water_22_Model,
    Lst_SU_SL_Sanitation_23_Model,
    Lst_SU_SL_Vegetation_42_Model,
    Lst_SU_SL_Electricity_43_Model,
    Lst_SU_SL_Drainage_44_Model,
    Lst_SU_SL_Gully_45_Model,
    Lst_SU_SL_Garbage_46_Model,
)


SEED_DATA = {
    # Existing tables — top up with anything that's missing
    Lst_SU_SL_Water_22_Model: [
        "Pipe",
        "Safety Well",
        "Unsafty Well",
        "Tube Well",
        "Borehole",
        "Rainwater Harvesting",
        "Bowser",
        "None",
        "Other",
    ],
    Lst_SU_SL_Sanitation_23_Model: [
        "Water Seal Tank",
        "Non-Sealant",
        "Water Seal Sewerage",
        "Pit",
        "Municipal Sewer",
        "None",
        "Other",
    ],
    # New tables
    Lst_SU_SL_Vegetation_42_Model: [
        "None",
        "Grass",
        "Shrubs",
        "Trees",
        "Mixed (Grass + Trees)",
        "Forest",
        "Cultivated / Crops",
        "Paddy",
        "Other",
    ],
    Lst_SU_SL_Electricity_43_Model: [
        "CEB Grid",
        "LECO Grid",
        "Solar",
        "Generator",
        "Hybrid (Grid + Solar)",
        "None",
        "Other",
    ],
    Lst_SU_SL_Drainage_44_Model: [
        "Storm Drain",
        "Surface Channel",
        "Underground Pipe",
        "Natural Watercourse",
        "Soakaway",
        "None",
        "Other",
    ],
    Lst_SU_SL_Gully_45_Model: [
        "Gully Bowser Service",
        "Direct to Septic",
        "Manual Emptying",
        "None",
        "Other",
    ],
    Lst_SU_SL_Garbage_46_Model: [
        "Municipal Collection",
        "Private Collector",
        "Composting",
        "Burning",
        "Dumping",
        "None",
        "Other",
    ],
}


class Command(BaseCommand):
    help = "Seed/top-up lookup tables used by the Physical & Environmental panel."

    def handle(self, *args, **options):
        total_created = 0
        total_existing = 0

        with transaction.atomic():
            for model, names in SEED_DATA.items():
                table = model._meta.db_table
                self.stdout.write(self.style.MIGRATE_HEADING(f"-> {table}"))
                for name in names:
                    _, created = model.objects.get_or_create(name=name)
                    if created:
                        total_created += 1
                        self.stdout.write(f"   + {name}")
                    else:
                        total_existing += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. {total_created} new row(s) inserted, {total_existing} already present."
        ))
