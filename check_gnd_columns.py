import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infobhoomi.settings')
django.setup()

from django.db import connection
with connection.cursor() as c:
    c.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'survey_rep'
        ORDER BY indexname
    """)
    rows = c.fetchall()
    for row in rows:
        print(row)
