import requests, json, io

BASE = 'http://127.0.0.1:8000/api/user'
TOKEN = '9afe80dceedb56cfa6e459a116bb2e0dab16fc13'
H  = {'Authorization': f'Token {TOKEN}'}
HJ = {'Authorization': f'Token {TOKEN}', 'Content-Type': 'application/json'}

BA_UNIT_ID     = 101
RRR_ID_OWNER   = 97   # Kamal Sunil Perera (Owner)
RRR_ID_COOWNER = 98   # Sunil Asanga Fernando (Co-Owner)

PASS, FAIL = [], []

def chk(label, ok, exp, got):
    status = 'OK  ' if ok else 'FAIL'
    print(f'  {status}  {label}: expected={repr(str(exp))}  got={repr(str(got))}')
    (PASS if ok else FAIL).append(label)

print('=== SAVE ===')

# 1. Restriction on Owner RRR
r = requests.post(f'{BASE}/rrr-restrictions/rrr_id={RRR_ID_OWNER}/', headers=HJ, json={
    'rrr_restriction_type': 'RES_EAS',
    'description': 'Right-of-way easement for access road',
    'time_begin': '2020-01-15',
    'time_end': None,
})
print(f'  Restriction [{r.status_code}]: {r.text[:150]}')

# 2. Responsibility on Owner RRR
r = requests.post(f'{BASE}/rrr-responsibilities/rrr_id={RRR_ID_OWNER}/', headers=HJ, json={
    'rrr_responsibility_type': 'RSP_MAINT',
    'description': 'Maintenance of boundary fence',
    'time_begin': '2020-01-15',
    'time_end': None,
})
print(f'  Responsibility [{r.status_code}]: {r.text[:150]}')

# 3. Extra document (Survey Plan) with dummy PDF bytes
dummy_pdf = b'%PDF-1.4 dummy test document for parcel 11742'
r = requests.post(
    f'{BASE}/rrr-add-document/ba_unit_id={BA_UNIT_ID}/',
    headers=H,
    data={'admin_source_type': 'Survey Plan'},
    files={'file': ('survey_plan_11742.pdf', io.BytesIO(dummy_pdf), 'application/pdf')},
)
print(f'  Extra Document [{r.status_code}]: {r.text[:200]}')

print()
print('=== RETRIEVE & VERIFY ===')
r = requests.get(f'{BASE}/rrr_data_get/?su_id=11742', headers=H)
print(f'Status: {r.status_code}')
data = r.json()
print(json.dumps(data, indent=2))

records = data.get('records', [])
if records:
    rrrs = records[0]['rrrs']
    owner_rrr = next((x for x in rrrs if x['rrr_id'] == RRR_ID_OWNER), None)
    if owner_rrr:
        restr = owner_rrr.get('restrictions', [])
        respo = owner_rrr.get('responsibilities', [])
        chk('restriction saved', len(restr) > 0, '>0', len(restr))
        if restr:
            chk('restriction type=RES_EAS', restr[0]['rrr_restriction_type'] == 'RES_EAS', 'RES_EAS', restr[0]['rrr_restriction_type'])
            chk('restriction description', restr[0]['description'] == 'Right-of-way easement for access road', 'set', restr[0]['description'])
        chk('responsibility saved', len(respo) > 0, '>0', len(respo))
        if respo:
            chk('responsibility type=RSP_MAINT', respo[0]['rrr_responsibility_type'] == 'RSP_MAINT', 'RSP_MAINT', respo[0]['rrr_responsibility_type'])
            chk('responsibility description', respo[0]['description'] == 'Maintenance of boundary fence', 'set', respo[0]['description'])
    else:
        print('  FAIL  owner_rrr not found in response')

    docs = records[0]['admin_sources']
    chk('extra doc saved (>=2 docs)', len(docs) >= 2, '>=2', len(docs))
    survey_doc = next((d for d in docs if d['admin_source_type'] == 'Survey Plan'), None)
    chk('survey plan doc exists', survey_doc is not None, True, survey_doc is not None)
    if survey_doc:
        chk('survey plan file_url set', survey_doc['file_url'] is not None, 'not None', survey_doc['file_url'])

print(f'\n{"="*50}')
print(f'FINAL: {len(PASS)} OK  |  {len(FAIL)} FAILED')
if FAIL:
    print('Failed:', FAIL)
else:
    print('ALL VERIFIED')
