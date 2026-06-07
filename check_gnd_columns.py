import os
import django
import sys

# Add project root to sys.path
sys.path.append('c:/Users/nmmil/OneDrive/Programs/InfoBhoomi/InfoBhoomi_Backend_dev2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infobhoomi.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'sl_gnd_10m'")
    rows = cursor.fetchall()
    print("Columns in sl_gnd_10m (repr):")
    for row in rows:
        print(f"{row[0]!r}")
