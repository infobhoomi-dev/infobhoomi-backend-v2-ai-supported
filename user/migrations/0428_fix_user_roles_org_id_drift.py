"""
Migration 0428 — Fix missing org_id column in user_roles table.

Root cause: DB/migration state drift. Migration 0286 (which adds org_id to
user_roles) is marked as applied in django_migrations, but the actual database
column was never created — likely because the DB was restored from a backup
taken before 0286 ran, while the migration table already recorded it as done.

Fix: Add org_id column using IF NOT EXISTS (safe to re-run), populate values
from existing role_type / users data, then enforce NOT NULL.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0427_rename_area_survey_rep_data_model_calculated_area_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Step 1: Add org_id column if missing (safe, idempotent)
                ALTER TABLE user_roles
                    ADD COLUMN IF NOT EXISTS org_id integer;

                -- Step 2: Set org_id = 0 for super_admin and admin roles
                --         (they span all organisations)
                UPDATE user_roles
                SET org_id = 0
                WHERE role_type IN ('super_admin', 'admin')
                  AND org_id IS NULL;

                -- Step 3: For user-type roles, infer org_id from the first
                --         member user's org_id
                UPDATE user_roles r
                SET org_id = (
                    SELECT u.org_id
                    FROM user_user u
                    WHERE u.id = ANY(r.users)
                    LIMIT 1
                )
                WHERE role_type = 'user'
                  AND org_id IS NULL
                  AND r.users IS NOT NULL
                  AND array_length(r.users, 1) > 0;

                -- Step 4: Fallback — any remaining NULL rows default to 1
                UPDATE user_roles
                SET org_id = 1
                WHERE org_id IS NULL;

                -- Step 5: Enforce NOT NULL (matches model definition)
                ALTER TABLE user_roles
                    ALTER COLUMN org_id SET NOT NULL;
            """,
            reverse_sql="""
                ALTER TABLE user_roles
                    DROP COLUMN IF EXISTS org_id;
            """,
        ),
    ]
