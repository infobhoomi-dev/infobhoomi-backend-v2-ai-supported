"""
Migration 0420 — Fix missing columns detected by check_db_schema.

These columns exist in Django's migration state (added by earlier migrations)
but were never created in the local DB instance due to DB/migration state drift.

Tables fixed:
  - survey_rep_geom_history : geom, reference_coordinate
  - la_admin_source          : done_by
  - sl_org_area_parent_bndry : geom, reference_coordinate
  - sl_org_area_child_bndry  : geom, reference_coordinate

All geometry columns use ADD COLUMN IF NOT EXISTS so this migration is
safe to re-run and safe against future dump restores.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0419_add_geom_to_org_location'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- survey_rep_geom_history
                ALTER TABLE survey_rep_geom_history
                    ADD COLUMN IF NOT EXISTS geom                 geometry(Geometry, 4326),
                    ADD COLUMN IF NOT EXISTS reference_coordinate geometry(Geometry, 4326);

                -- la_admin_source
                ALTER TABLE la_admin_source
                    ADD COLUMN IF NOT EXISTS done_by integer;

                -- sl_org_area_parent_bndry
                ALTER TABLE sl_org_area_parent_bndry
                    ADD COLUMN IF NOT EXISTS geom                 geometry(Geometry, 4326),
                    ADD COLUMN IF NOT EXISTS reference_coordinate geometry(Geometry, 4326);

                -- sl_org_area_child_bndry
                ALTER TABLE sl_org_area_child_bndry
                    ADD COLUMN IF NOT EXISTS geom                 geometry(Geometry, 4326),
                    ADD COLUMN IF NOT EXISTS reference_coordinate geometry(Geometry, 4326);
            """,
            reverse_sql="""
                ALTER TABLE survey_rep_geom_history
                    DROP COLUMN IF EXISTS geom,
                    DROP COLUMN IF EXISTS reference_coordinate;

                ALTER TABLE la_admin_source
                    DROP COLUMN IF EXISTS done_by;

                ALTER TABLE sl_org_area_parent_bndry
                    DROP COLUMN IF EXISTS geom,
                    DROP COLUMN IF EXISTS reference_coordinate;

                ALTER TABLE sl_org_area_child_bndry
                    DROP COLUMN IF EXISTS geom,
                    DROP COLUMN IF EXISTS reference_coordinate;
            """,
        ),
    ]
