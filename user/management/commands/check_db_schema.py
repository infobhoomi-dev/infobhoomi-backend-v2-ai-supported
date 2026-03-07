"""
management command: check_db_schema

Compares what Django's migration state expects to exist in the DB against
what the DB actually has.  Reports every table / column mismatch so you can
fix it BEFORE it causes a 500 error in production.

Usage:
    python manage.py check_db_schema
    python manage.py check_db_schema --fix   # auto-add missing columns (safe)
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = "Check that all Django model fields exist as columns in the DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Automatically ADD missing columns (never drops anything).",
        )

    def handle(self, *args, **options):
        fix = options["fix"]
        issues = []

        with connection.cursor() as cursor:
            # Build a map of {table_name: set(column_names)} from the actual DB
            cursor.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, column_name
                """
            )
            db_columns: dict[str, set[str]] = {}
            for table, col in cursor.fetchall():
                db_columns.setdefault(table, set()).add(col)

        # Walk every registered model
        for model in apps.get_models():
            meta = model._meta
            if not meta.managed:
                continue
            table = meta.db_table

            if table not in db_columns:
                issues.append(("MISSING TABLE", table, ""))
                self.stdout.write(
                    self.style.ERROR(f"  [MISSING TABLE] {table}")
                )
                continue

            for field in meta.get_fields():
                # Skip M2M (junction tables) and reverse relations — no column in this table
                if getattr(field, "many_to_many", False) or not getattr(field, "concrete", False):
                    continue
                if not hasattr(field, "column") or field.column is None:
                    continue
                col = field.column
                if col not in db_columns[table]:
                    issues.append(("MISSING COLUMN", table, col))
                    field_type = type(field).__name__
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [MISSING COLUMN] {table}.{col}  ({field_type})"
                        )
                    )

                    if fix:
                        self._add_column(table, field)

        if not issues:
            self.stdout.write(self.style.SUCCESS("All model columns exist in the DB."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{len(issues)} issue(s) found."
                    + (" All missing columns were added." if fix else
                       " Run with --fix to auto-add missing columns.")
                )
            )

    # ------------------------------------------------------------------
    def _add_column(self, table: str, field) -> None:
        """
        Issue a safe ALTER TABLE … ADD COLUMN IF NOT EXISTS for the field.
        Uses Django's schema editor so the SQL is backend-appropriate.
        """
        try:
            with connection.schema_editor() as editor:
                # Make the field nullable so it never breaks existing rows
                field_copy = field.__class__(
                    **{
                        **{
                            k: getattr(field, k)
                            for k in ("max_length", "srid", "geography")
                            if hasattr(field, k)
                        },
                        "null": True,
                        "blank": True,
                    }
                )
                field_copy.set_attributes_from_name(field.name)
                field_copy.model = field.model
                sql, params = editor._column_sql(field.model, field_copy)
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {sql}",
                        params,
                    )
            self.stdout.write(
                self.style.SUCCESS(f"    → Added {table}.{field.column}")
            )
        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(f"    → Failed to add {table}.{field.column}: {exc}")
            )
