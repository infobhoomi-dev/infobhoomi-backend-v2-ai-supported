import os
import django
import sys

# Add project root to sys.path
sys.path.append('c:/Users/nmmil/OneDrive/Programs/InfoBhoomi/InfoBhoomi_Backend_dev2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infobhoomi.settings')
django.setup()

from django.db import connection

def check_triggers():
    with connection.cursor() as cursor:
        print("--- Triggers on survey_rep ---")
        cursor.execute("""
            SELECT trigger_name, event_manipulation, action_statement, action_timing
            FROM information_schema.triggers 
            WHERE event_object_table = 'survey_rep';
        """)
        for row in cursor.fetchall():
            print(f"Trigger: {row[0]}, Event: {row[1]}, Timing: {row[3]}")
            # print(f"Action: {row[2]}")

        print("\n--- Function definition for ladm_anti_conflict ---")
        cursor.execute("""
            SELECT prosrc 
            FROM pg_proc 
            WHERE proname = 'ladm_anti_conflict';
        """)
        row = cursor.fetchone()
        if row:
            print(row[0])
        else:
            print("Function not found.")

if __name__ == "__main__":
    check_triggers()
