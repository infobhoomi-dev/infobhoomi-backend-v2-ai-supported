# Generated for InfoBhoomi on 2026-05-12
#
# Adds five new lookup tables for the Physical & Environmental section
# of the Land side panel:
#   - lst_su_sl_vegetation_42
#   - lst_su_sl_electricity_43
#   - lst_su_sl_drainage_44
#   - lst_su_sl_gully_45
#   - lst_su_sl_garbage_46
#
# Water and Sanitation reuse the existing lst_su_sl_water_22 and
# lst_su_sl_sanitation_23 tables. Initial data seeding is handled by the
# `seed_physical_lookups` management command (idempotent get_or_create).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0007_normalize_sl_gnd_10m_hidden_whitespace"),
    ]

    operations = [
        migrations.CreateModel(
            name='Lst_SU_SL_Vegetation_42_Model',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'lst_su_sl_vegetation_42',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Lst_SU_SL_Electricity_43_Model',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'lst_su_sl_electricity_43',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Lst_SU_SL_Drainage_44_Model',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'lst_su_sl_drainage_44',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Lst_SU_SL_Gully_45_Model',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'lst_su_sl_gully_45',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Lst_SU_SL_Garbage_46_Model',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'lst_su_sl_garbage_46',
                'managed': True,
            },
        ),
    ]
