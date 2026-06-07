from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0014_cityjson_su_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="la_ls_build_unit_model",
            name="building_unit_type",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="la_ls_build_unit_model",
            name="cadastral_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="la_ls_build_unit_model",
            name="component_units",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="la_ls_build_unit_model",
            index=models.Index(fields=["building_unit_type"], name="lsbu_type_idx"),
        ),
        migrations.AddIndex(
            model_name="la_ls_build_unit_model",
            index=models.Index(fields=["cadastral_id"], name="lsbu_cadastral_idx"),
        ),
    ]
