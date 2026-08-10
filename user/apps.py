from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'

    def ready(self):
        import user.signals

        from django.db.models.signals import post_migrate
        post_migrate.connect(_ensure_gnd_geom_column, sender=self)


def _ensure_gnd_geom_column(sender, **kwargs):
    """
    Guarantee sl_gnd_10m.geom exists after every migrate run.

    Some GND imports/restores leave the geometry column named "geom " or
    "geom\\xa0". Django must see a clean "geom" column for spatial lookups.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("""
            DO $$
            DECLARE
                bad_geom_name text;
            BEGIN
                SELECT column_name INTO bad_geom_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'sl_gnd_10m'
                  AND column_name <> 'geom'
                  AND column_name <> 'geom_ladm'
                  AND regexp_replace(column_name, '[[:space:]\\u00A0]+$', '', 'g') = 'geom'
                ORDER BY ordinal_position
                LIMIT 1;

                IF bad_geom_name IS NOT NULL THEN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'sl_gnd_10m'
                          AND column_name = 'geom'
                    ) THEN
                        EXECUTE format(
                            'UPDATE sl_gnd_10m SET geom = COALESCE(geom, %I) WHERE geom IS NULL',
                            bad_geom_name
                        );
                        EXECUTE format('ALTER TABLE sl_gnd_10m DROP COLUMN %I', bad_geom_name);
                    ELSE
                        EXECUTE format('ALTER TABLE sl_gnd_10m RENAME COLUMN %I TO geom', bad_geom_name);
                    END IF;
                END IF;
            END$$;

            ALTER TABLE sl_gnd_10m
            ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326);

            CREATE INDEX IF NOT EXISTS sl_gnd_10m_geom_gist ON sl_gnd_10m USING GIST (geom);
        """)
