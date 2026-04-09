from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_baseline_schema'),
    ]

    operations = [
        # SeparateDatabaseAndState:
        #   state_operations=[]  → Django already knows about the model from 0002 (faked)
        #   database_operations  → actually creates the table which the fake skipped
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE IF NOT EXISTS parcel_delete_archive (
                            id          SERIAL PRIMARY KEY,
                            su_id       INTEGER NOT NULL,
                            label       VARCHAR(255),
                            parcel_status VARCHAR(50),
                            deleted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            deleted_by  INTEGER,
                            land_unit_data    JSONB,
                            assessment_data   JSONB,
                            tax_info_data     JSONB,
                            utility_lu_data   JSONB,
                            zoning_data       JSONB,
                            physical_env_data JSONB,
                            build_unit_data   JSONB,
                            utility_bu_data   JSONB
                        );
                        CREATE INDEX IF NOT EXISTS parcel_delete_archive_su_id_idx
                            ON parcel_delete_archive (su_id);
                        CREATE INDEX IF NOT EXISTS parcel_delete_archive_deleted_at_idx
                            ON parcel_delete_archive (deleted_at DESC);
                    """,
                    reverse_sql="DROP TABLE IF EXISTS parcel_delete_archive;",
                ),
            ],
        ),
    ]