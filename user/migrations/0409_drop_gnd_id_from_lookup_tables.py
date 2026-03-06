"""
Migration 0409 — Drop phantom gnd_id from all 41 lookup tables + remark from sl_ba_unit
=========================================================================================
The gnd_id column was added to every lst_* table by a bulk ALTER TABLE script.
It was never declared in any Django model, never read/written in views or serializers,
and makes no logical sense on lookup/reference tables.

sl_ba_unit.remark is 100% NULL across all 54 records and never referenced anywhere.

Uses RunSQL because gnd_id is not in Django's migration state (no corresponding model field).
"""

from django.db import migrations

# All 41 lookup tables that have a phantom gnd_id column
LST_TABLES = [
    'lst_sl_party_type_1',
    'lst_sl_partyroletype_2',
    'lst_sl_education_level_3',
    'lst_sl_race_4',
    'lst_sl_health_status_5',
    'lst_sl_married_status_6',
    'lst_sl_religions_7',
    'lst_sl_gendertype_8',
    'lst_sl_righttype_9',
    'lst_sl_baunittype_10',
    'lst_sl_adminrestrictiontype_11',
    'lst_sl_annotationtype_12',
    'lst_sl_mortgagetype_13',
    'lst_sl_rightsharetype_14',
    'lst_sl_administrativestataustype_15',
    'lst_sl_administrativesourcetype_16',
    'lst_sl_responsibilitytype_17',
    'lst_la_baunittype_18',
    'lst_su_sl_levelcontenttype_19',
    'lst_su_sl_regestertype_20',
    'lst_su_sl_structuretype_21',
    'lst_su_sl_water_22',
    'lst_su_sl_sanitation_23',
    'lst_su_sl_roof_type_24',
    'lst_su_sl_wall_type_25',
    'lst_su_sl_floor_type_26',
    'lst_sr_sl_spatialsourcetypes_27',
    'lst_ec_extlandusetype_28',
    'lst_ec_extlandusesubtype_29',
    'lst_ec_extouterlegalspaceusetype_30',
    'lst_ec_extouterlegalspaceusesubtype_31',
    'lst_ec_extbuildusetype_32',
    'lst_ec_extbuildusesubtype_33',
    'lst_ec_extdivisiontype_34',
    'lst_ec_extfeaturemaintype_35',
    'lst_ec_extfeatureytype_36',
    'lst_ec_extfeaturebuildtype_37',
    'lst_telecom_providers_38',
    'lst_int_providers_39',
    'lst_org_names_40',
    'lst_sl_group_party_type_41',
]

# Build SQL + reverse SQL
forward_sql = '\n'.join(
    f'ALTER TABLE {t} DROP COLUMN IF EXISTS gnd_id;'
    for t in LST_TABLES
)

# Reverse: restore gnd_id columns (remark handled separately by RemoveField)
reverse_sql = '\n'.join(
    f'ALTER TABLE {t} ADD COLUMN gnd_id integer;'
    for t in LST_TABLES
)


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0408_drop_unused_fields_session2'),
    ]

    operations = [
        migrations.RunSQL(
            sql=forward_sql,
            reverse_sql=reverse_sql,
        ),
        # Also remove remark from Django model state
        migrations.RemoveField(
            model_name='sl_ba_unit_model',
            name='remark',
        ),
    ]
