"""
Migration 0457 — Add BEFORE INSERT trigger on survey_rep to auto-set su_id = id.

Previously the view did a second UPDATE after every INSERT to set su_id to the
row's own primary key.  A BEFORE INSERT trigger eliminates that round-trip:
PostgreSQL applies column DEFAULTs (including the serial sequence for 'id')
before a BEFORE trigger fires, so NEW.id is already populated when the trigger
runs.

The IF NEW.su_id IS NULL guard preserves any explicitly-supplied value (e.g.
during data migrations or direct DB inserts).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0456_fix_survey_rep_gndid_column_name'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION fn_survey_rep_set_su_id()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NEW.su_id IS NULL THEN
                        NEW.su_id = NEW.id;
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                DROP TRIGGER IF EXISTS trg_survey_rep_su_id ON survey_rep;

                CREATE TRIGGER trg_survey_rep_su_id
                BEFORE INSERT ON survey_rep
                FOR EACH ROW EXECUTE FUNCTION fn_survey_rep_set_su_id();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS trg_survey_rep_su_id ON survey_rep;
                DROP FUNCTION IF EXISTS fn_survey_rep_set_su_id();
            """,
        ),
    ]
