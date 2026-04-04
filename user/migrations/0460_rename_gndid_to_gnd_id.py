"""
Migration 0460 — Permanently rename survey_rep.gndid → survey_rep.gnd_id
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0457_survey_rep_su_id_trigger'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$ BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name  = 'survey_rep'
                          AND column_name = 'gndid'
                    ) THEN
                        ALTER TABLE survey_rep RENAME COLUMN gndid TO gnd_id;
                        RAISE NOTICE 'survey_rep: renamed gndid to gnd_id';
                    ELSE
                        RAISE NOTICE 'survey_rep: gndid not found, nothing to rename';
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$ BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name  = 'survey_rep'
                          AND column_name = 'gnd_id'
                    ) THEN
                        ALTER TABLE survey_rep RENAME COLUMN gnd_id TO gndid;
                    END IF;
                END $$;
            """,
        ),

        migrations.AlterField(
            model_name='survey_rep_data_model',
            name='gnd_id',
            field=models.IntegerField(null=True, blank=True, db_index=True),
        ),
    ]