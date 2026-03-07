from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0417_drop_gnd_id_from_la_ls_utinet_lu'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE sl_ba_unit DROP COLUMN IF EXISTS org_id;
                ALTER TABLE sl_ba_unit DROP COLUMN IF EXISTS role_type;
            """,
            reverse_sql="""
                ALTER TABLE sl_ba_unit ADD COLUMN org_id integer NOT NULL DEFAULT 1;
                ALTER TABLE sl_ba_unit ADD COLUMN role_type character varying(20) NOT NULL DEFAULT 'user';
            """,
        ),
    ]
