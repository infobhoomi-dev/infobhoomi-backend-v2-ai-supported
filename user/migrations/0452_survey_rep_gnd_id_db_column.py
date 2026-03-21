from django.db import migrations, models


class Migration(migrations.Migration):
    """State-only migration: tells Django the DB column is 'gndid', not 'gnd_id'.
    No DDL is run — the column already exists with this name in the database."""

    dependencies = [
        ('user', '0451_rrr_remove_nullable_required_fks'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='survey_rep_data_model',
                    name='gnd_id',
                    field=models.IntegerField(null=False, db_index=True, db_column='gndid'),
                ),
            ],
        ),
    ]
