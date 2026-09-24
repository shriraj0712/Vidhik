"""
Vidhik AI - Phase 13 Lawyer Module Complete Verification Test
=============================================================
Runs an automated end-to-end verification against the live server
covering Authentication, Dashboard, Clients, Cases, Case Details,
Documents, Hearings, Case Notes, Legal Research, and Lawyer Profile.
"""

import sys
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE_URL, timeout=10.0)

print("=" * 65)
print("VIDHIK AI - PHASE 13 LAWYER MODULE END-TO-END VERIFICATION")
print("=" * 65)

# 1. ROOT & STATIC UI
print("\n[1/11] VERIFY ROOT & STATIC UI")
r_lawyer = client.get("/lawyer")
assert r_lawyer.status_code == 200, f"Expected 200, got {r_lawyer.status_code}"
assert "Vidhik AI" in r_lawyer.text
assert "Lawyer Dashboard" in r_lawyer.text
print("  ✓ /lawyer UI served successfully (200 OK)")

r_css = client.get("/static/styles.css")
assert r_css.status_code == 200
print("  ✓ /static/styles.css served (200 OK)")

r_js = client.get("/static/app.js")
assert r_js.status_code == 200
print("  ✓ /static/app.js served (200 OK)")

# 2. AUTHENTICATION
print("\n[2/11] VERIFY AUTHENTICATION")
login_payload = {"email": "rajesh.advocate@vidhik.ai", "password": "password123"}
r_login = client.post("/api/auth/login", json=login_payload)
assert r_login.status_code == 200, f"Login failed: {r_login.text}"
auth_data = r_login.json()
token = auth_data["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"  ✓ Logged in as: {auth_data['full_name']} (Role: {auth_data['role']}, Lawyer ID: {auth_data['lawyer_id']})")

# 3. DASHBOARD METRICS
print("\n[3/11] VERIFY DASHBOARD METRICS")
r_dash = client.get("/api/lawyer/dashboard", headers=headers)
assert r_dash.status_code == 200
dash = r_dash.json()
print(f"  ✓ Total Clients: {dash['total_clients']}")
print(f"  ✓ Active Cases: {dash['active_cases']}")
print(f"  ✓ Upcoming Hearings: {dash['upcoming_hearings']}")
print(f"  ✓ Recent Documents: {dash['recent_documents_count']}")
print(f"  ✓ Recent Cases in Brief: {len(dash['recent_cases'])}")
print(f"  ✓ Upcoming Hearings Count: {len(dash['upcoming_hearings_list'])}")
print(f"  ✓ Recent Activity Events: {len(dash['recent_activity'])}")

# 4. CLIENT MANAGEMENT
print("\n[4/11] VERIFY CLIENT MANAGEMENT")
r_clients = client.get("/api/lawyer/clients", headers=headers)
assert r_clients.status_code == 200
clients_data = r_clients.json()
print(f"  ✓ Total Clients Listed: {clients_data['total']}")
for c in clients_data["clients"]:
    print(f"    - {c['full_name']} ({c['email']}) | Active Matters: {c['active_cases_count']}")

client_detail = client.get(f"/api/lawyer/clients/{clients_data['clients'][0]['user_id']}", headers=headers).json()
print(f"  ✓ Inspected Client Detail: {client_detail['full_name']} with {len(client_detail.get('cases', []))} matters")

# 5. CASE MANAGEMENT & WORKSPACE
print("\n[5/11] VERIFY CASE MANAGEMENT")
r_cases = client.get("/api/lawyer/cases", headers=headers)
assert r_cases.status_code == 200
cases_data = r_cases.json()
print(f"  ✓ Total Cases Listed: {cases_data['total']}")
for cs in cases_data["cases"]:
    print(f"    - [{cs['case_number']}] {cs['case_title']} | Court: {cs['court_name']} | Status: {cs['status']}")

# 6. CASE DETAILS WORKSPACE (CASE 1)
print("\n[6/11] VERIFY CASE DETAILS WORKSPACE (CASE 1)")
case1 = client.get("/api/lawyer/cases/1", headers=headers).json()
print(f"  ✓ Case Title: {case1['case_title']}")
print(f"  ✓ Opposite Party: {case1['opposite_party']}")
print(f"  ✓ Documents in Workspace: {len(case1['documents'])}")
print(f"  ✓ Hearings in Workspace: {len(case1['hearings'])}")
print(f"  ✓ Notes in Workspace: {len(case1['notes'])}")
print(f"  ✓ Linked Statutory Provisions: {len(case1['legal_sections'])}")
print(f"  ✓ Procedural Timeline Updates: {len(case1['updates'])}")

# 7. CASE NOTES CRUD
print("\n[7/11] VERIFY CASE NOTES CRUD")
new_note_res = client.post("/api/lawyer/cases/1/notes", headers=headers, json={
    "case_id": 1,
    "title": "Automated Test Strategic Note",
    "content": "Verified case law precedents on natural justice under Article 226 of the Constitution.",
    "is_pinned": False
})
assert new_note_res.status_code == 200
created_note = new_note_res.json()
print(f"  ✓ Note Created: ID {created_note['note_id']} - {created_note['title']}")

del_note_res = client.delete(f"/api/lawyer/notes/{created_note['note_id']}", headers=headers)
assert del_note_res.status_code == 200
print(f"  ✓ Note Successfully Deleted: ID {created_note['note_id']}")

# 8. HEARINGS MANAGEMENT
print("\n[8/11] VERIFY HEARINGS MANAGEMENT")
r_hearings = client.get("/api/lawyer/hearings", headers=headers)
assert r_hearings.status_code == 200
h_data = r_hearings.json()
print(f"  ✓ Upcoming Hearings: {len(h_data['upcoming'])}")
for h in h_data["upcoming"]:
    print(f"    - [{h['reminder_date']} {h['reminder_time']}] {h['title']} @ {h['court_name']}")
print(f"  ✓ Past Hearings: {len(h_data['past'])}")

# 9. DOCUMENT MANAGEMENT
print("\n[9/11] VERIFY DOCUMENT MANAGEMENT")
r_docs = client.get("/api/lawyer/documents", headers=headers)
assert r_docs.status_code == 200
docs_data = r_docs.json()
print(f"  ✓ Total Cataloged Documents: {docs_data['total']}")
for d in docs_data["documents"]:
    print(f"    - {d['document_name']} ({d['document_type']}) | Case: {d['case_title']}")

# 10. REUSING EXISTING LEGAL SEARCH & LINKING PROVISION
print("\n[10/11] VERIFY EXISTING LEGAL RESEARCH INTEGRATION")
r_search = client.get("/api/search?q=co-operative&limit=3")
assert r_search.status_code == 200
search_data = r_search.json()
print(f"  ✓ Query: '{search_data['query']}'")
print(f"  ✓ Total Corpus Matches in Vidhik DB: {search_data['total']}")
top_match = search_data["results"][0]
print(f"  ✓ Top Match: Section {top_match['section_number']} - {top_match['section_title']}")
print(f"  ✓ Act Name: {top_match['law_name']}")
print(f"  ✓ Extracted Snippet: {top_match['snippet'][:90]}...")

link_res = client.post("/api/lawyer/cases/1/sections", headers=headers, json={
    "section_id": top_match["section_id"],
    "relevance_score": 98.0,
    "explanation": "Statutory authority governing powers and functions of society committee."
})
assert link_res.status_code == 200
link_data = link_res.json()
print(f"  ✓ Successfully Linked Section {link_data['section_number']} to Case 1 (Score: {link_data['relevance_score']}%)")

# 11. LAWYER PROFILE
print("\n[11/11] VERIFY LAWYER PROFILE")
r_prof = client.get("/api/lawyer/profile", headers=headers)
assert r_prof.status_code == 200
prof = r_prof.json()
print(f"  ✓ Name: {prof['full_name']}")
print(f"  ✓ Bar Registration: {prof['bar_council_number']}")
print(f"  ✓ Experience: {prof['experience_years']} Years")
print(f"  ✓ Courts: {prof['court_practice']}")
print(f"  ✓ Specializations: {', '.join(prof['specializations_list'])}")
print(f"  ✓ Languages: {', '.join(prof['languages_list'])}")

print("\n" + "=" * 65)
print("ALL 11 VERIFICATION STAGES COMPLETED WITH 100% SUCCESS!")
print("=" * 65)
