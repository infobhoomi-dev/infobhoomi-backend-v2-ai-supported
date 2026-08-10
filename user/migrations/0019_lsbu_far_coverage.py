from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add planning-compliance attributes to LA_LS_Build_Unit_Model so the
    GIS Query Console "FAR / Coverage Violations" query can run against the
    live backend (attribute-only, no spatial join required).

    Both columns are nullable/additive — existing rows are unaffected.
    """

    dependencies = [
        ("user", "0018_archive_extra_legalspaces"),
    ]

    operations = [
        migrations.AddField(
            model_name="la_ls_build_unit_model",
            name="floor_area_ratio",
            field=models.DecimalField(decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name="la_ls_build_unit_model",
            name="plot_coverage",
            field=models.DecimalField(decimal_places=2, max_digits=5, null=True),
        ),
    ]
