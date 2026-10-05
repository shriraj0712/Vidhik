import urllib.request
import json

def post(url, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get(url, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# 1. Login
auth = post('http://localhost:8000/api/auth/login', {'email': 'sunita.sharma@example.com', 'password': 'password123'})
token = auth['token']
print('Login successful for:', auth['full_name'], '| Role:', auth['role'])

# 2. Create and analyze case (Feature 19 - Traffic police licence)
case1 = post('http://localhost:8000/api/cases/create-and-analyze', {
    'title': 'Traffic Police Licence Incident',
    'description': 'Traffic police scratched my licence.',
    'case_type': 'Motor Vehicle / Traffic'
}, token=token)
print('\n[CASE 1 CREATED & ANALYZED]')
print('Case ID:', case1['case_id'])
print('Situation:', case1['situation_summary'])
print('Category:', case1['case_category'], '| Domain:', case1['legal_domain'])
print('Ranked Provisions:', len(case1['ranked_provisions']), 'found')
for p in case1['ranked_provisions'][:3]:
    print(f"  - {p['act_name']} Sec {p['section_number']}: {p['section_title']}")
print('Lawyers:', len(case1['recommended_lawyers']), 'matched')
for l in case1['recommended_lawyers'][:2]:
    print(f"  - {l['full_name']} | Score: {l['match_score']} | {l['match_reason'][:70]}...")

# 3. Check active case
active = get('http://localhost:8000/api/cases/active', token=token)
print('\n[CURRENT ACTIVE CASE]')
print('Active Case ID:', active['active_case']['case_id'], '| Title:', active['active_case']['title'])

# 4. Create second case (Feature 20 - Landlord security deposit)
case2 = post('http://localhost:8000/api/cases/create-and-analyze', {
    'title': 'Security Deposit Refund Dispute',
    'description': 'My landlord is refusing to return my security deposit.',
    'case_type': 'Property & Tenancy'
}, token=token)
print('\n[CASE 2 CREATED & ANALYZED]')
print('Case ID:', case2['case_id'])
print('Category:', case2['case_category'], '| Domain:', case2['legal_domain'])
for p in case2['ranked_provisions'][:3]:
    print(f"  - {p['act_name']} Sec {p['section_number']}: {p['section_title']}")
for l in case2['recommended_lawyers'][:2]:
    print(f"  - {l['full_name']} | {l['specialization']} | {l['match_reason'][:70]}...")

# 5. Switch active case back to case 1
switch_res = post(f"http://localhost:8000/api/cases/{case1['case_id']}/set-active", {}, token=token)
print('\n[SWITCHED ACTIVE CASE BACK TO CASE 1]')
print('Active Case is now:', switch_res['active_case']['title'])

# 6. Re-analyze case 1 with new facts (Feature 17)
reanalyzed = post(f"http://localhost:8000/api/cases/{case1['case_id']}/update-and-reanalyze", {
    'additional_facts': 'The officer also kept my licence for two days without issuing any seizure memo or receipt.',
    'recalculate_urgency': True
}, token=token)
print('\n[CASE 1 RE-ANALYZED]')
print('Updated Version:', reanalyzed['analysis_version'])
print('Updated Extracted Facts:', len(reanalyzed['extracted_facts']), 'facts')
for f in reanalyzed['extracted_facts'][-3:]:
    print('  -', f)
