from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Extend parcel_delete_archive to capture the full legal-space set removed
    when a land parcel is cascade-deleted (buildings, strata/apartment units,
    OLS/ILS legal spaces and their utility networks), plus the relationship
    metadata that ties each archived legal space back to its parent parcel.

    All columns are nullable/additive — existing rows and the parcel's own
    archive row are unaffected.
    """

    dependencies = [
        ('user', '0017_backfill_3d_role_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='apt_unit_data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='ols_polygon_data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='ols_pointline_data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='ils_unit_data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='utility_au_data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='utility_ols_data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='parent_su_id',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='space_kind',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name='parcel_delete_archive_model',
            name='layer_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
