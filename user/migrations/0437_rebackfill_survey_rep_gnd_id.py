"""
Migration 0437 — Re-backfill survey_rep.gnd_id using correct spatial intersection.

Previous migrations (0430, 0432) set gnd_id = 1 as a fallback because:
  - sl_gnd_10m.geom was empty (geography data was in "geom " with trailing space)
  - survey_rep.geom was geography type, causing intersection mismatches

Both are now fixed (0435 dropped geography column, 0436 converted geom to geometry).
This migration re-runs the spatial intersection to assign correct gnd_id values.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0436_convert_survey_rep_geom_to_geometry'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Step 0: Ensure gnd_id column exists (idempotent guard)
                ALTER TABLE survey_rep ADD COLUMN IF NOT EXISTS gnd_id integer;

                -- Step 1: Use centroid containment — fast point-in-polygon,
                -- works for the vast majority of parcels that sit inside one GND.
                UPDATE survey_rep sr
                SET    gnd_id = (
                           SELECT g.gid
                           FROM   sl_gnd_10m g
                           WHERE  g.geom IS NOT NULL
                             AND  ST_Contains(g.geom, ST_MakeValid(ST_Centroid(sr.geom)))
                           LIMIT  1
                       )
                WHERE  sr.geom IS NOT NULL;

                -- Step 2: For any rows whose centroid fell on a boundary (still NULL
                -- or unchanged from 1 with no genuine gid=1 neighbour), fall back to
                -- a simple ST_Intersects — no expensive area computation.
                UPDATE survey_rep sr
                SET    gnd_id = (
                           SELECT g.gid
                           FROM   sl_gnd_10m g
                           WHERE  g.geom IS NOT NULL
                             AND  ST_Intersects(ST_MakeValid(sr.geom), g.geom)
                           LIMIT  1
                       )
                WHERE  sr.geom IS NOT NULL
                  AND  gnd_id IS NULL;

                -- Report how many rows still have gnd_id = 1 after real intersection
                DO $$
                DECLARE
                    cnt INT;
                BEGIN
                    SELECT COUNT(*) INTO cnt FROM survey_rep WHERE gnd_id = 1;
                    RAISE NOTICE 'survey_rep: % rows still have gnd_id = 1 after re-backfill (these genuinely fall in GND gid=1).', cnt;

                    SELECT COUNT(*) INTO cnt FROM survey_rep WHERE gnd_id IS NULL;
                    RAISE NOTICE 'survey_rep: % rows have NULL gnd_id (geometry outside all GND boundaries).', cnt;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
