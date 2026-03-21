# Generated 2026-03-21
#
# Issue #4 fix: Add reference_no, acceptance_date, exte_arch_ref, source_description
# to la_admin_source. These fields were collected by the frontend form but were
# silently dropped because the model had no columns for them.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0446_rrr_restriction_responsibility_fk_to_ba_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='la_admin_source_model',
            name='reference_no',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='la_admin_source_model',
            name='acceptance_date',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='la_admin_source_model',
            name='exte_arch_ref',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='la_admin_source_model',
            name='source_description',
            field=models.TextField(null=True),
        ),
    ]
