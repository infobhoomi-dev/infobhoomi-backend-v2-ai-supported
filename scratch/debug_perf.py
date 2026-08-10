import os
import django
import sys
import time

# Add project root to sys.path
sys.path.append('c:/Users/nmmil/OneDrive/Programs/InfoBhoomi/InfoBhoomi_Backend_dev2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infobhoomi.settings')
django.setup()

from django.db import connection
from user.models import sl_gnd_10m_Model
from django.contrib.gis.geos import Point

def check_performance():
    with connection.cursor() as cursor:
        print("--- Table Indexes ---")
        cursor.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename IN ('sl_gnd_10m', 'survey_rep');
        """)
        for row in cursor.fetchall():
            print(f"Table: {row[0]}, Index: {row[1]}")

        print("\n--- Table Counts ---")
        cursor.execute("SELECT count(*) FROM sl_gnd_10m;")
        print(f"sl_gnd_10m count: {cursor.fetchone()[0]}")
        cursor.execute("SELECT count(*) FROM survey_rep;")
        print(f"survey_rep count: {cursor.fetchone()[0]}")

    print("\n--- GND Lookup Profiling ---")
    # Colombo area point (roughly)
    test_point = Point(79.86, 6.92, srid=4326)
    
    start = time.perf_counter()
    gnd = sl_gnd_10m_Model.objects.filter(geom__contains=test_point).first()
    end = time.perf_counter()
    print(f"GND lookup for Point(79.86, 6.92) took: {(end-start)*1000:.2f}ms")
    if gnd:
        print(f"Found GND: {gnd.gnd} (ID: {gnd.gid})")
    else:
        print("No GND found at this point.")

    # Try a simple intersection with a small box
    from django.contrib.gis.geos import Polygon
    test_box = Polygon.from_bbox((79.85, 6.91, 79.87, 6.93))
    test_box.srid = 4326
    
    start = time.perf_counter()
    gnds = list(sl_gnd_10m_Model.objects.filter(geom__intersects=test_box))
    end = time.perf_counter()
    print(f"GND lookup for BBOX took: {(end-start)*1000:.2f}ms (Found {len(gnds)})")

if __name__ == "__main__":
    check_performance()
