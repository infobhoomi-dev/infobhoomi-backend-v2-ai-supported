from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'

    def ready(self):

        import user.signals  # ←  registers pre_delete signal

        from django.db.models.signals import post_migrate
        post_migrate.connect(_ensure_gnd_geom_column, sender=self)


def _ensure_gnd_geom_column(sender, **kwargs):
    """
    Guarantee sl_gnd_10m.geom exists after every migrate run.

    Migration 0415 adds this column via RunSQL, but if the DB was restored
    from a backup where the migration was already marked 'applied' (yet the
    ALTER TABLE never actually ran on that source DB), the column will be
    missing.  This signal acts as a safety net — it is a no-op when the
    column already exists.
    """
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE sl_gnd_10m
            ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326);
        """)
