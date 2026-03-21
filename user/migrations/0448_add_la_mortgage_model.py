# Generated 2026-03-21
#
# Issue #6 fix: creates the la_mortgage table to store mortgage-specific
# fields (amount, interest, ranking, mortgage_type, mortgage_ref_id, mortgagee)
# that were previously lost because the model had no columns for them.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0447_la_admin_source_add_missing_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='LA_Mortgage_Model',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('rrr_id', models.OneToOneField(
                    db_column='rrr_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mortgage',
                    to='user.la_rrr_model',
                )),
                ('amount',          models.DecimalField(decimal_places=2, max_digits=15, null=True)),
                ('interest',        models.DecimalField(decimal_places=4, max_digits=7, null=True)),
                ('ranking',         models.IntegerField(null=True)),
                ('mortgage_type',   models.CharField(max_length=100, null=True)),
                ('mortgage_ref_id', models.CharField(max_length=255, null=True)),
                ('mortgagee',       models.CharField(max_length=255, null=True)),
            ],
            options={
                'db_table': 'la_mortgage',
                'managed': True,
            },
        ),
    ]
