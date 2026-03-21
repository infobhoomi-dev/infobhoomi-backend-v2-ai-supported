# Generated 2026-03-21
#
# Issue #8 fix: create la_rrr_audit table for immutable RRR change history.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0449_rrr_protect_fks_and_soft_delete'),
    ]

    operations = [
        migrations.CreateModel(
            name='LA_RRR_Audit_Model',
            fields=[
                ('id',              models.AutoField(primary_key=True, serialize=False)),
                ('rrr_id',          models.IntegerField()),
                ('ba_unit_id',      models.IntegerField(null=True)),
                ('su_id',           models.IntegerField(null=True)),
                ('action',          models.CharField(max_length=20, choices=[
                                        ('CREATE', 'Create'),
                                        ('TERMINATE', 'Terminate'),
                                        ('UPDATE', 'Update'),
                                    ])),
                ('changed_by',      models.IntegerField()),
                ('changed_by_name', models.CharField(max_length=255, null=True)),
                ('changed_at',      models.DateTimeField(auto_now_add=True)),
                ('snapshot',        models.JSONField()),
            ],
            options={
                'db_table': 'la_rrr_audit',
                'managed': True,
                'ordering': ['-changed_at'],
            },
        ),
    ]
