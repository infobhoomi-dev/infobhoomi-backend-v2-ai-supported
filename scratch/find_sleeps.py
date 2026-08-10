import os
import django
import sys

# Add project root to sys.path
sys.path.append('c:/Users/nmmil/OneDrive/Programs/InfoBhoomi/InfoBhoomi_Backend_dev2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infobhoomi.settings')
django.setup()

from django.db import connection

def find_sleeps():
    with connection.cursor() as cursor:
        print("--- Functions with pg_sleep ---")
        cursor.execute("""
            SELECT proname, prosrc 
            FROM pg_proc 
            WHERE prosrc LIKE '%pg_sleep%';
        """)
        for row in cursor.fetchall():
            print(f"Function: {row[0]}\nSource:\n{row[1]}\n")

if __name__ == "__main__":
    find_sleeps()
