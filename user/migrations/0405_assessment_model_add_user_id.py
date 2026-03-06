from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0404_drop_sl_party_user_id'),
    ]

    operations = [
        # Column already exists in DB as NOT NULL — only update Django's model state.
        # The RunSQL makes the column nullable to match the model definition (null=True).
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='assessment_model',
                    name='user_id',
                    field=models.IntegerField(null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_name = 'assessment' AND column_name = 'user_id'
                            ) THEN
                                ALTER TABLE assessment ALTER COLUMN user_id DROP NOT NULL;
                            ELSE
                                ALTER TABLE assessment ADD COLUMN user_id integer NULL;
                            END IF;
                        END;
                        $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
