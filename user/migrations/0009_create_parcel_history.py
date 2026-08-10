from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0008_physical_env_lookups'),
    ]

    operations = [
        migrations.CreateModel(
            name='Parcel_History_Model',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('su_id', models.IntegerField(db_index=True)),
                ('record_type', models.CharField(db_index=True, max_length=30)),
                ('action', models.CharField(db_index=True, max_length=30)),
                ('category', models.CharField(blank=True, max_length=80, null=True)),
                ('field_name', models.CharField(blank=True, max_length=255, null=True)),
                ('old_value', models.TextField(blank=True, null=True)),
                ('new_value', models.TextField(blank=True, null=True)),
                ('change_summary', models.TextField()),
                ('changed_by', models.IntegerField(blank=True, null=True)),
                ('changed_by_name', models.CharField(blank=True, max_length=255, null=True)),
                ('changed_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('snapshot', models.JSONField(blank=True, null=True)),
                ('can_restore', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'parcel_history',
                'ordering': ['-changed_at', '-id'],
                'managed': True,
            },
        ),
    ]
