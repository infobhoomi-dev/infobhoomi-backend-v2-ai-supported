import os
import django
import sys

# Add project root to sys.path
sys.path.append('c:/Users/nmmil/OneDrive/Programs/InfoBhoomi/InfoBhoomi_Backend_dev2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infobhoomi.settings')
django.setup()

from django.db import connection

def fix_db():
    with connection.cursor() as cursor:
        # 1. Rename columns with trailing non-breaking spaces
        print("Checking for columns with trailing non-breaking spaces in sl_gnd_10m...")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'sl_gnd_10m'")
        columns = [row[0] for row in cursor.fetchall()]
        
        for col in columns:
            if col.endswith('\xa0'):
                new_col = col.replace('\xa0', '').strip()
                print(f"Renaming column '{col!r}' to '{new_col}'...")
                # We need to use double quotes to handle the weird character
                cursor.execute(f'ALTER TABLE sl_gnd_10m RENAME COLUMN "{col}" TO "{new_col}";')
                print(f"Renamed {col!r} to {new_col}")

        # 2. Add GIST indexes
        print("Checking for GIST index on sl_gnd_10m.geom...")
        cursor.execute("""
            SELECT count(*) 
            FROM pg_indexes 
            WHERE tablename = 'sl_gnd_10m' AND indexname = 'sl_gnd_10m_geom_gist';
        """)
        if cursor.fetchone()[0] == 0:
            print("Adding GIST index on sl_gnd_10m.geom...")
            cursor.execute("CREATE INDEX sl_gnd_10m_geom_gist ON sl_gnd_10m USING GIST (geom);")
            print("Index added.")
        else:
            print("Index already exists.")

        print("Checking for GIST index on survey_rep.geom...")
        cursor.execute("""
            SELECT count(*) 
            FROM pg_indexes 
            WHERE tablename = 'survey_rep' AND indexname = 'survey_rep_geom_gist';
        """)
        if cursor.fetchone()[0] == 0:
            print("Adding GIST index on survey_rep.geom...")
            cursor.execute("CREATE INDEX survey_rep_geom_gist ON survey_rep USING GIST (geom);")
            print("Index added.")
        else:
            print("Index already exists.")

if __name__ == "__main__":
    try:
        fix_db()
        print("DB optimization and fix completed.")
    except Exception as e:
        print(f"Error fixing DB: {e}")
