"""
Management command: fix_sequences
Resets all PostgreSQL identity/serial sequences to MAX(id) + 1 so that
new inserts never hit duplicate-key errors.

Usage:
    python manage.py fix_sequences
"""
from django.core.management.base import BaseCommand
from django.db import connection


# Every table whose PK sequence needs to stay in sync.
# Format: (table_name, pk_column)
SEQUENCES = [
    ("survey_rep",              "id"),
    ("survey_rep_geom_history", "id"),
    ("survey_rep_func_history", "id"),
    ("la_spatial_unit",         "id"),
    ("la_ls_land_unit",         "id"),
    ("la_ls_build_unit",        "id"),
    ("sl_party_roles",          "id"),
    ("la_spatial_source",       "id"),
    ("assessment",              "id"),
    ("la_ls_physical_env",      "id"),
    ("la_ls_zoning",            "id"),
    ("la_ls_utinet_lu",         "id"),
    ("la_ls_utinet_bu",         "id"),
    ("la_rrr",                  "rrr_id"),
    ("sl_ba_unit",              "ba_unit_id"),
    ("sl_party",                "pid"),
    ("la_admin_source",         "admin_source_id"),
    ("history_spatialunit_attrib", "id"),
    ("la_rrr_responsibility",   "id"),
    ("la_rrr_restriction",      "id"),
    ("tax_info",                "id"),
    ("user_user",               "id"),
    ("user_roles",              "role_id"),
    ("permission_list",         "permission_id"),
    ("role_permission",         "id"),
    ("layers",                  "layer_id"),
]


class Command(BaseCommand):
    help = "Reset all PK sequences to MAX(pk) so new inserts never duplicate."

    def handle(self, *args, **options):
        fixed = []
        skipped = []

        with connection.cursor() as cur:
            for table, col in SEQUENCES:
                try:
                    # Get the sequence name for this column
                    cur.execute(
                        "SELECT pg_get_serial_sequence(%s, %s)",
                        [table, col],
                    )
                    row = cur.fetchone()
                    seq_name = row[0] if row else None

                    if not seq_name:
                        skipped.append(f"{table}.{col} (no sequence found)")
                        continue

                    # Set sequence to MAX(pk), is_called=true → next value = MAX+1
                    cur.execute(
                        f'SELECT setval(%s, COALESCE(MAX("{col}"), 1), true) FROM "{table}"',
                        [seq_name],
                    )
                    new_val = cur.fetchone()[0]
                    fixed.append(f"{table}.{col} -> next id will be {new_val + 1}")

                except Exception as e:
                    skipped.append(f"{table}.{col} ({e})")

        self.stdout.write(self.style.SUCCESS("Fixed sequences:"))
        for line in fixed:
            self.stdout.write(f"  [OK] {line}")

        if skipped:
            self.stdout.write(self.style.WARNING("Skipped:"))
            for line in skipped:
                self.stdout.write(f"  [SKIP] {line}")
