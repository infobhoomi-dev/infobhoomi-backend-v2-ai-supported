# Generated manually — adds strata/apartment unit fields to la_ls_build_unit
# These fields are populated for layer_id=12 child spatial units (apartment units)
# geom_3d stores the 3D solid geometry shared with the 3D Cadastre project

from django.db import migrations, models
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_fix_zoning_and_flood_zone_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='la_ls_build_unit_model',
            name='floor_no',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='la_ls_build_unit_model',
            name='floor_area',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='la_ls_build_unit_model',
            name='apt_name',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='la_ls_build_unit_model',
            name='geom_3d',
            field=django.contrib.gis.db.models.fields.GeometryField(dim=3, null=True, srid=4326),
        ),
    ]
