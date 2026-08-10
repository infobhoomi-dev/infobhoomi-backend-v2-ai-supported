import os
import django
import sys

# Add project root to sys.path
sys.path.append('c:/Users/nmmil/OneDrive/Programs/InfoBhoomi/InfoBhoomi_Backend_dev2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infobhoomi.settings')
django.setup()

from user.models import sl_gnd_10m_Model

try:
    first = sl_gnd_10m_Model.objects.first()
    if first:
        print(f"First GND GID: {first.gid}")
    else:
        print("No GND data found.")
except Exception as e:
    print(f"Error accessing GND model: {e}")
