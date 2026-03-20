"""
Migration 0431 — Populate sl_gnd_10m.geom (geometry) from "geom " (geography).

Root cause: The sl_gnd_10m table has two similarly-named columns:
  - "geom " (trailing space) — geography type — contains the real GND polygons
  - "geom"                   — geometry type  — empty, used by Django ORM

Migration 0415 added the geometry 'geom' column but never populated it.
Because it was empty, all PostGIS intersection queries failed and migration
0430's fallback set gnd_id = 1 for every survey_rep row.

Fix steps:
  1. Cast "geom " (geography) to geometry and write into "geom".
  2. Create a GIST spatial index on "geom".
  3. Re-backfill survey_rep.gnd_id via correct spatial intersection,
     overwriting the wrong gnd_id = 1 values from migration 0430.
  4. Drop the stale "geom " (geography) column to avoid future confusion.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0430_fix_survey_rep_gnd_id_column'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- ── Step 1: Copy "geom " (geography) → "geom" (geometry) ─────────────────
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_attribute a
                        JOIN pg_class c ON c.oid = a.attrelid
                        WHERE c.relname = 'sl_gnd_10m'
                          AND a.attname = 'geom '
                          AND NOT a.attisdropped
                    ) THEN
                        EXECUTE $q$
                            UPDATE sl_gnd_10m
                            SET    geom = "geom "::geometry
                            WHERE  "geom " IS NOT NULL
                        $q$;
                        RAISE NOTICE 'sl_gnd_10m: copied "geom " (geography) into geom (geometry).';
                    ELSE
                        RAISE NOTICE 'sl_gnd_10m: column "geom " not found — skipping copy.';
                    END IF;
                END $$;

                -- ── Step 2: Spatial index on geom ────────────────────────────────────────
                CREATE INDEX IF NOT EXISTS sl_gnd_10m_geom_gist_idx
                    ON sl_gnd_10m USING GIST (geom);

                -- ── Step 3: Re-backfill survey_rep.gnd_id ────────────────────────────────
                UPDATE survey_rep sr
                SET    gnd_id = (
                           SELECT g.gid
                           FROM   sl_gnd_10m g
                           WHERE  g.geom IS NOT NULL
                             AND  ST_Intersects(sr.geom, g.geom)
                           ORDER  BY ST_Area(ST_Intersection(sr.geom::geometry, g.geom)) DESC
                           LIMIT  1
                       )
                WHERE  sr.geom IS NOT NULL
                  AND  EXISTS (SELECT 1 FROM sl_gnd_10m WHERE geom IS NOT NULL LIMIT 1);

                -- ── Step 4: Drop the stale geography column ───────────────────────────────
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_attribute a
                        JOIN pg_class c ON c.oid = a.attrelid
                        WHERE c.relname = 'sl_gnd_10m'
                          AND a.attname = 'geom '
                          AND NOT a.attisdropped
                    ) THEN
                        EXECUTE 'ALTER TABLE sl_gnd_10m DROP COLUMN "geom "';
                        RAISE NOTICE 'sl_gnd_10m: dropped stale "geom " (geography) column.';
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS sl_gnd_10m_geom_gist_idx;
                -- Data cannot be restored; geography column was intentionally dropped.
            """,
        ),
    ]
