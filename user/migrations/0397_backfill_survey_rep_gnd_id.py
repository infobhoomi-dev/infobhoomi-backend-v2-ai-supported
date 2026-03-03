# Generated manually 2026-03-03
# Back-fills null gnd_id on survey_rep rows for land parcels (layer_id IN (1, 6))
# by spatially intersecting each parcel geometry against sl_gnd_10m.
# Non-land-parcel rows are left untouched — null gnd_id is valid for them.

from django.db import migrations


def backfill_gnd_id(apps, schema_editor):
    schema_editor.execute(
        """
        UPDATE survey_rep sr
        SET    gnd_id = (
                   SELECT g.gid
                   FROM   sl_gnd_10m g
                   WHERE  ST_Intersects(sr.geom, g.geom)
                   ORDER  BY ST_Area(ST_Intersection(sr.geom, g.geom)) DESC
                   LIMIT  1
               )
        WHERE  sr.layer_id IN (1, 6)
          AND  sr.gnd_id IS NULL
          AND  sr.geom IS NOT NULL;
        """
    )


def reverse_backfill(apps, schema_editor):
    # Reversing to null is safe — original state was null
    schema_editor.execute(
        """
        -- No-op: we cannot know which rows were originally NULL vs already set.
        -- Reverse migration is intentionally left as a no-op.
        SELECT 1;
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0396_la_rrr_document_model'),
    ]

    operations = [
        migrations.RunPython(backfill_gnd_id, reverse_backfill),
    ]
