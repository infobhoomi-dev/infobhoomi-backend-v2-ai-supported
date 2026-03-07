import requests

BASE = 'http://127.0.0.1:8000/api/user'
TOKEN = '9afe80dceedb56cfa6e459a116bb2e0dab16fc13'
SU_ID = 11742
H  = {'Authorization': f'Token {TOKEN}', 'Content-Type': 'application/json'}
HG = {'Authorization': f'Token {TOKEN}'}

PASS, FAIL = [], []

def chk(label, ok, exp, got):
    print(f'   {"OK  " if ok else "FAIL"}  {label}: expected={str(exp)!r}  got={str(got)!r}')
    (PASS if ok else FAIL).append(label)

def get(url):
    r = requests.get(url, headers=HG)
    return r.json() if r.status_code == 200 else {}

def save(label, r):
    ok = r.status_code in (200, 201)
    print(f'  {"OK  " if ok else "FAIL"} [{r.status_code}] {label}' + ('' if ok else ': ' + r.text[:200]))

# ── SAVE ─────────────────────────────────────────────────────
print(f'=== SAVE: su_id={SU_ID} ===')

save('1. Admin info', requests.patch(f'{BASE}/lnd-admin-info/update/su_id={SU_ID}/', headers=H, json={
    'sl_land_type': 'PUBLIC', 'tenure_type': 'LEASEHOLD',
    'land_name': 'TEST-LOT-11742', 'access_road': 'Yes',
    'registration_date': '2023-06-15',
    'local_auth': 'Bandarawela Municipal Council',
    'parcel_status': 'ACTIVE',
    'adjacent_parcels': '11741, 11743', 'parent_parcel': '11700',
    'child_parcels': '', 'part_of_estate': 'TEST-ESTATE-01',
}))
save('2. Overview/spatial', requests.patch(f'{BASE}/land-overview-info/update/su_id={SU_ID}/', headers=H, json={
    'area': 1234.56, 'perimeter': 156.78,
    'ext_landuse_type': 'RESIDENTIAL', 'dimension_2d_3d': '2D',
    'boundary_type': 'FIXED', 'crs': 'EPSG:4326',
    'reference_coordinate': '80.8902,6.8301',
}))
save('3. Zoning', requests.patch(f'{BASE}/lnd-zoning-info/update/su_id={SU_ID}/', headers=H, json={
    'zoning_category': 'RES_LOW', 'max_building_height': 9.0,
    'max_coverage': 60.0, 'max_far': 1.5,
    'setback_front': 3.0, 'setback_rear': 2.0, 'setback_side': 1.5,
    'special_overlay': 'Heritage Zone A',
}))
save('4. Physical env', requests.patch(f'{BASE}/lnd-physical-env/update/su_id={SU_ID}/', headers=H, json={
    'elevation': 312.5, 'slope': 4.2, 'soil_type': 'CLAY',
    'flood_zone': False, 'vegetation_cover': 'Mixed Shrubs',
}))
save('5. Utility network', requests.patch(f'{BASE}/lnd-utinet-info/update/su_id={SU_ID}/', headers=H, json={
    'water_supply': 'Municipal Pipe', 'electricity': 'National Grid',
    'drainage_system': 'Storm Drain', 'sanitation_gully': 'Cesspit',
    'garbage_disposal': 'Municipal Collection',
}))
save('6. Tax/assessment', requests.patch(f'{BASE}/tax-assess-info/update/su_id={SU_ID}/', headers=H, json={
    'land_value': 4500000.00, 'market_value': 5200000.00,
    'tax_annual_value': 18000.00, 'date_of_valuation': '2023-01-10',
    'tax_status': 'PAID',
}))
save('7. Metadata', requests.patch(f'{BASE}/la-spatial-source-update/su_id={SU_ID}/', headers=H, json={
    'spatial_source_type': 'CADASTRAL_SURVEY', 'source_id': 'PLAN/2023/BW/0042',
    'description': 'HIGH', 'date_accept': '2023-06-15',
    'surveyor_name': 'Dept. of Survey - Badulla',
}))

# ── RETRIEVE & VERIFY ────────────────────────────────────────
print(f'\n=== RETRIEVE & VERIFY: su_id={SU_ID} ===')

d = get(f'{BASE}/lnd-admin-info/su_id={SU_ID}/')
print('\n1. Admin Info:')
for k, exp in [
    ('land_name','TEST-LOT-11742'), ('sl_land_type','PUBLIC'), ('tenure_type','LEASEHOLD'),
    ('access_road','Yes'), ('registration_date','2023-06-15'),
    ('local_auth','Bandarawela Municipal Council'), ('parcel_status','ACTIVE'),
    ('adjacent_parcels','11741, 11743'), ('parent_parcel','11700'), ('part_of_estate','TEST-ESTATE-01'),
]:
    chk(k, str(d.get(k)) == str(exp), exp, d.get(k))

d = get(f'{BASE}/land-overview-info/su_id={SU_ID}/')
print('\n2. Overview/Spatial:')
for k, exp in [('ext_landuse_type','RESIDENTIAL'), ('boundary_type','FIXED'), ('crs','EPSG:4326'), ('dimension_2d_3d','2D')]:
    chk(k, str(d.get(k)) == str(exp), exp, d.get(k))
chk('area~1234.56',    abs(float(d.get('area') or 0)      - 1234.56) < 0.01, 1234.56, d.get('area'))
chk('perimeter~156.78',abs(float(d.get('perimeter') or 0) - 156.78)  < 0.01, 156.78,  d.get('perimeter'))

d = get(f'{BASE}/lnd-zoning-info/su_id={SU_ID}/')
print('\n3. Zoning:')
for k, exp in [('zoning_category','RES_LOW'), ('special_overlay','Heritage Zone A')]:
    chk(k, str(d.get(k)) == str(exp), exp, d.get(k))
chk('max_building_height~9.0', abs(float(d.get('max_building_height') or 0) - 9.0)  < 0.01, 9.0,  d.get('max_building_height'))
chk('max_coverage~60.0',       abs(float(d.get('max_coverage') or 0)        - 60.0) < 0.01, 60.0, d.get('max_coverage'))
chk('max_far~1.5',             abs(float(d.get('max_far') or 0)             - 1.5)  < 0.01, 1.5,  d.get('max_far'))

d = get(f'{BASE}/lnd-physical-env/su_id={SU_ID}/')
print('\n4. Physical:')
for k, exp in [('soil_type','CLAY'), ('vegetation_cover','Mixed Shrubs')]:
    chk(k, str(d.get(k)) == str(exp), exp, d.get(k))
chk('elevation~312.5', abs(float(d.get('elevation') or 0) - 312.5) < 0.01, 312.5, d.get('elevation'))
chk('slope~4.2',       abs(float(d.get('slope') or 0)     - 4.2)   < 0.01, 4.2,   d.get('slope'))
chk('flood_zone=False', d.get('flood_zone') == False, False, d.get('flood_zone'))

d = get(f'{BASE}/lnd-utinet-info/su_id={SU_ID}/')
print('\n5. Utility Network:')
for k, exp in [
    ('water_supply','Municipal Pipe'), ('electricity','National Grid'),
    ('drainage_system','Storm Drain'), ('sanitation_gully','Cesspit'),
    ('garbage_disposal','Municipal Collection'),
]:
    chk(k, str(d.get(k)) == str(exp), exp, d.get(k))

d = get(f'{BASE}/tax-assess-info/su_id={SU_ID}/')
print('\n6. Tax/Assessment:')
for k, exp in [('date_of_valuation','2023-01-10'), ('tax_status','PAID')]:
    chk(k, str(d.get(k)) == str(exp), exp, d.get(k))
chk('land_value~4500000',  abs(float(d.get('land_value') or 0)       - 4500000) < 1, 4500000,  d.get('land_value'))
chk('market_value~5200000',abs(float(d.get('market_value') or 0)     - 5200000) < 1, 5200000,  d.get('market_value'))
chk('annual_tax~18000',    abs(float(d.get('tax_annual_value') or 0) - 18000)   < 1, 18000,    d.get('tax_annual_value'))

d = get(f'{BASE}/la-spatial-source-retrive/su_id={SU_ID}/')
print('\n7. Metadata:')
for k, exp in [
    ('spatial_source_type','CADASTRAL_SURVEY'), ('source_id','PLAN/2023/BW/0042'),
    ('description','HIGH'), ('surveyor_name','Dept. of Survey - Badulla'),
]:
    chk(k, str(d.get(k)) == str(exp), exp, d.get(k))

print(f'\n{"="*55}')
print(f'FINAL: {len(PASS)} OK  |  {len(FAIL)} FAILED')
if FAIL:
    print('Failed:', FAIL)
else:
    print('ALL FIELDS VERIFIED CORRECTLY')
