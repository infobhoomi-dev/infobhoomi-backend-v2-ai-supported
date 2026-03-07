from django.db import migrations, models


class Migration(migrations.Migration):
    """
    The DB column `user_id` already exists in `la_admin_source` (NOT NULL).
    Also relax `done_by` to nullable to match current DB state.
    SeparateDatabaseAndState is used so no DDL is executed against the existing column.
    """

    dependencies = [
        ('user', '0423_add_land_unit_relationship_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='la_admin_source_model',
                    name='user_id',
                    field=models.IntegerField(),
                ),
                migrations.AlterField(
                    model_name='la_admin_source_model',
                    name='done_by',
                    field=models.IntegerField(null=True),
                ),
            ],
            database_operations=[],  # column already exists — no DDL needed
        ),
    ]
