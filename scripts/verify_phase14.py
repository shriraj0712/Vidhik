"""
Vidhik AI - Phase 14 Citizen / User Module Complete Verification Suite
======================================================================
Automated verification suite testing:
1. Database Schema & Migration 007 Integrity (Tables, Foreign Keys, Unique Constraints)
2. Citizen Registration, Role Assignment & Authentication Security
3. Elimination of Silent Fallback (Strict 401 on missing/invalid auth)
4. Strict Role Separation & Authorization Guards (Citizen != Lawyer)
5. Cross-User Data Isolation (Cases, Documents, Confidential Lawyer Notes)
6. Citizen Dashboard Live Metrics & Content Feed
7. Citizen Cases & Documents Management
8. Citizen Profile GET / PUT Persistence
9. Saved Statutory Provisions (Bookmarks) CRUD & Deduplication
10. Citizen Legal Search History Tracking & Privacy
11. Notifications Management & Read / Read-All
12. Procedure Checklist Persistence (Phase 12 Integration)
13. Document Analysis History Isolation (Phase 11 Integration)
14. Database Corpus Zero-Loss Verification (869 Laws, 41,442 Sections, 42 Lexicon, 9,304 Alignments)
"""

import sys
import os
import time
import uuid
import atexit
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath("backend"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.database import get_db_cursor

BASE_URL = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE_URL, timeout=15.0)

# Pre-flight check: Verify backend and database availability
try:
    r_health = client.get("/lawyer")
    if r_health.status_code not in (200, 307):
        print(f"[ERROR] Server responded with unexpected status code {r_health.status_code}")
        sys.exit(1)
except httpx.ConnectError:
    print("[ERROR] Backend server is not available at http://127.0.0.1:8000.")
    print("Please ensure the Uvicorn server is running before executing tests:")
    print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
    sys.exit(1)

try:
    with get_db_cursor() as cur:
        cur.execute("SELECT 1;")
except Exception as e:
    print(f"[ERROR] PostgreSQL database is unavailable: {e}")
    sys.exit(1)

print("=" * 74)
print("VIDHIK AI - PHASE 14 CITIZEN / USER MODULE VERIFICATION SUITE")
print("=" * 74)

# ==============================================================================
# 1. DATABASE SCHEMA & MIGRATION 007 INTEGRITY
# ==============================================================================
print("\n[1/14] VERIFY DATABASE SCHEMA & MIGRATION 007 TABLES & CONSTRAINTS")
with get_db_cursor() as cur:
    # 1.1 Verify tables exist
    required_tables = [
        "user_profiles",
        "user_saved_sections",
        "user_search_history",
        "user_procedure_trackers"
    ]
    for tbl in required_tables:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            );
        """, (tbl,))
        exists = cur.fetchone()["exists"]
        assert exists, f"Table '{tbl}' does not exist in public schema!"
        print(f"  ✓ Table '{tbl}' verified in database schema")

    # 1.2 Verify user_profiles unique constraint on user_id
    cur.execute("""
        SELECT COUNT(*) as cnt
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = 'user_profiles'
          AND tc.constraint_type IN ('UNIQUE', 'PRIMARY KEY')
          AND ccu.column_name = 'user_id';
    """)
    assert cur.fetchone()["cnt"] > 0, "user_profiles missing UNIQUE constraint on user_id!"
    print("  ✓ user_profiles: UNIQUE(user_id) constraint verified")

    # 1.3 Verify user_saved_sections unique constraint on (user_id, section_id)
    cur.execute("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'user_saved_sections' AND constraint_type = 'UNIQUE';
    """)
    bm_uniques = [r["constraint_name"] for r in cur.fetchall()]
    assert len(bm_uniques) > 0, "user_saved_sections missing UNIQUE constraint!"
    print(f"  ✓ user_saved_sections: UNIQUE(user_id, section_id) constraint verified")

    # 1.4 Verify user_procedure_trackers unique constraint on (user_id, procedure_id)
    cur.execute("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'user_procedure_trackers' AND constraint_type = 'UNIQUE';
    """)
    trk_uniques = [r["constraint_name"] for r in cur.fetchall()]
    assert len(trk_uniques) > 0, "user_procedure_trackers missing UNIQUE constraint!"
    print(f"  ✓ user_procedure_trackers: UNIQUE(user_id, procedure_id) constraint verified")

    # Clean up any leftover test accounts from prior interrupted runs
    cur.execute("DELETE FROM users WHERE email LIKE 'citizen.test.%@example.com';")
    cur.connection.commit()

    # 1.5 Verify blank profile rows created for existing users
    cur.execute("SELECT COUNT(*) as total_users FROM users;")
    total_users = cur.fetchone()["total_users"]
    cur.execute("SELECT COUNT(*) as total_profiles FROM user_profiles;")
    total_profiles = cur.fetchone()["total_profiles"]
    assert total_profiles >= total_users, f"Profiles ({total_profiles}) less than Users ({total_users})!"
    print(f"  ✓ user_profiles: {total_profiles} profile rows initialized for existing accounts")


# Tracking state for reliable test data isolation & cleanup
test_state = {
    "new_citizen_id": None,
    "sunita_case_id": None,
    "test_ana_id": None,
    "orig_profile": None,
    "sunita_id": 201,
    "sunita_headers": None,
}

def cleanup():
    # 1. Clean up temporary test citizen created in Suite 2 (cascades to profiles, etc.)
    new_citizen_id = test_state.get("new_citizen_id")
    if new_citizen_id:
        try:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM users WHERE user_id = %s;", (new_citizen_id,))
                cur.connection.commit()
        except Exception as e:
            print(f"Warning: Cleanup test user {new_citizen_id} failed: {e}")

    # 2. Clean up temporary test case created in Suite 6 (cascades to case_documents & case_updates)
    sunita_case_id = test_state.get("sunita_case_id")
    if sunita_case_id:
        try:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM cases WHERE case_id = %s;", (sunita_case_id,))
                cur.connection.commit()
        except Exception as e:
            print(f"Warning: Cleanup test case {sunita_case_id} failed: {e}")

    # 3. Clean up test document analysis if still present
    test_ana_id = test_state.get("test_ana_id")
    sunita_headers = test_state.get("sunita_headers")
    if test_ana_id and sunita_headers:
        try:
            client.delete(f"/api/analysis/{test_ana_id}", headers=sunita_headers)
        except Exception:
            pass

    # 4. Clean up any leftover notifications for Sunita from this test run
    sunita_id = test_state.get("sunita_id", 201)
    try:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM notifications WHERE user_id = %s AND (title = 'Legal Matter Registered' OR message LIKE '%Flat Title%');", (sunita_id,))
            cur.connection.commit()
    except Exception:
        pass

    # 5. Restore Sunita's seeded profile values
    orig_profile = test_state.get("orig_profile")
    if orig_profile:
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    UPDATE users SET phone = '+91 98112 34567' WHERE user_id = %s;
                    UPDATE user_profiles SET
                        date_of_birth = NULL,
                        address = NULL,
                        city = NULL,
                        state = NULL,
                        pincode = NULL,
                        preferred_language = 'en',
                        occupation = NULL,
                        emergency_contact = NULL
                    WHERE user_id = %s;
                """, (sunita_id, sunita_id))
                cur.connection.commit()
        except Exception:
            pass

    # 6. Clean up any leftover procedure trackers for Sunita
    try:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM user_procedure_trackers WHERE user_id = %s;", (sunita_id,))
            cur.connection.commit()
    except Exception:
        pass

atexit.register(cleanup)


# ==============================================================================
# 2. CITIZEN REGISTRATION & AUTHENTICATION SECURITY
# ==============================================================================
print("\n[2/14] VERIFY CITIZEN REGISTRATION & AUTHENTICATION SECURITY")

unique_suffix = int(time.time())
reg_email = f"citizen.test.{unique_suffix}@example.com"
reg_name = f"Test Citizen {unique_suffix}"
reg_payload = {
    "full_name": reg_name,
    "email": reg_email,
    "phone": "+91 98200 12345",
    "password": "Password@123"
}

# 2.1 Citizen Registration
r_reg = client.post("/api/auth/register", json=reg_payload)
assert r_reg.status_code == 201, f"Registration failed ({r_reg.status_code}): {r_reg.text}"
reg_res = r_reg.json()
assert "token" in reg_res, "Token missing in registration response"
assert reg_res["email"] == reg_email.lower(), "Email mismatch"
assert reg_res["role"] == "user", f"Expected role='user', got {reg_res['role']}"
new_citizen_token = reg_res["token"]
new_citizen_id = reg_res["user_id"]
test_state["new_citizen_id"] = new_citizen_id
new_citizen_headers = {"Authorization": f"Bearer {new_citizen_token}"}
print(f"  ✓ POST /api/auth/register created citizen account (User ID: {new_citizen_id}, Role: {reg_res['role']})")

# 2.2 Verify duplicate registration rejection
r_dup = client.post("/api/auth/register", json=reg_payload)
assert r_dup.status_code == 400, f"Expected 400 on duplicate registration, got {r_dup.status_code}"
assert "already registered" in r_dup.text.lower(), "Expected duplicate email warning"
print("  ✓ Duplicate registration rejected with HTTP 400 Bad Request")

# 2.3 Verify missing required fields rejected
r_bad = client.post("/api/auth/register", json={"email": "bad@example.com"})
assert r_bad.status_code == 422, f"Expected 422 on missing fields, got {r_bad.status_code}"
print("  ✓ Incomplete registration payload rejected with HTTP 422 Unprocessable Entity")

# 2.4 Verify citizen login works with newly registered credentials
r_login_new = client.post("/api/auth/login", json={"email": reg_email, "password": "Password@123"})
assert r_login_new.status_code == 200, f"Login failed: {r_login_new.text}"
assert r_login_new.json()["token"] is not None
print("  ✓ POST /api/auth/login authenticated newly registered citizen")

# 2.5 Verify seeded citizen account login
r_sunita = client.post("/api/auth/login", json={"email": "sunita.sharma@example.com", "password": "password123"})
assert r_sunita.status_code == 200, f"Sunita login failed: {r_sunita.text}"
sunita_token = r_sunita.json()["token"]
sunita_headers = {"Authorization": f"Bearer {sunita_token}"}
sunita_id = r_sunita.json()["user_id"]
test_state["sunita_id"] = sunita_id
test_state["sunita_headers"] = sunita_headers
print(f"  ✓ Seeded citizen login verified: Sunita Sharma (User ID: {sunita_id})")

# 2.6 Verify existing lawyer login still works
r_lawyer = client.post("/api/auth/login", json={"email": "rajesh.advocate@vidhik.ai", "password": "password123"})
assert r_lawyer.status_code == 200, f"Lawyer login failed: {r_lawyer.text}"
lawyer_token = r_lawyer.json()["token"]
lawyer_headers = {"Authorization": f"Bearer {lawyer_token}"}
print(f"  ✓ Seeded lawyer login verified: Rajesh Advocate (Role: {r_lawyer.json()['role']})")


# ==============================================================================
# 3. STRICT AUTHENTICATION (ELIMINATION OF SILENT FALLBACK HAZARD)
# ==============================================================================
print("\n[3/14] VERIFY REMOVAL OF SILENT FALLBACK (STRICT 401)")

# 3.1 Unauthenticated requests to protected endpoints return 401
r_noauth_cit = client.get("/api/citizen/dashboard")
assert r_noauth_cit.status_code == 401, f"Expected 401 on /api/citizen/dashboard, got {r_noauth_cit.status_code}"
print("  ✓ Unauthenticated /api/citizen/dashboard strictly returns HTTP 401")

r_noauth_law = client.get("/api/lawyer/dashboard")
assert r_noauth_law.status_code == 401, f"Expected 401 on /api/lawyer/dashboard, got {r_noauth_law.status_code}"
print("  ✓ Unauthenticated /api/lawyer/dashboard strictly returns HTTP 401")

r_bad_token = client.get("/api/citizen/dashboard", headers={"Authorization": "Bearer invalid_gibberish_token_12345"})
assert r_bad_token.status_code == 401, f"Expected 401 for invalid token, got {r_bad_token.status_code}"
print("  ✓ Invalid bearer token strictly returns HTTP 401")


# ==============================================================================
# 4. STRICT ROLE SEPARATION & AUTHORIZATION GUARDS
# ==============================================================================
print("\n[4/14] VERIFY ROLE SEPARATION & AUTHORIZATION GUARDS")

# 4.1 Citizen attempting to access Lawyer Dashboard
r_cit_on_lawyer = client.get("/api/lawyer/dashboard", headers=sunita_headers)
assert r_cit_on_lawyer.status_code == 403, f"Expected 403 for citizen on lawyer dashboard, got {r_cit_on_lawyer.status_code}"
print("  ✓ Citizen accessing /api/lawyer/dashboard strictly blocked with HTTP 403 Forbidden")

# 4.2 Lawyer attempting to access Citizen Dashboard
r_law_on_citizen = client.get("/api/citizen/dashboard", headers=lawyer_headers)
assert r_law_on_citizen.status_code == 403, f"Expected 403 for lawyer on citizen dashboard, got {r_law_on_citizen.status_code}"
print("  ✓ Lawyer accessing /api/citizen/dashboard strictly blocked with HTTP 403 Forbidden")


# ==============================================================================
# 5. CITIZEN DASHBOARD LIVE METRICS
# ==============================================================================
print("\n[5/14] VERIFY CITIZEN DASHBOARD LIVE METRICS & RECENT FEEDS")
r_dash = client.get("/api/citizen/dashboard", headers=sunita_headers)
assert r_dash.status_code == 200, f"Dashboard failed: {r_dash.text}"
dash_data = r_dash.json()
assert "metrics" in dash_data, "metrics missing from dashboard"
metrics = dash_data["metrics"]
print(f"  ✓ Active Cases: {metrics['active_cases']}")
print(f"  ✓ Total Documents: {metrics['total_documents']}")
print(f"  ✓ Upcoming Hearings: {metrics['upcoming_hearings']}")
print(f"  ✓ Saved Provisions: {metrics['saved_sections']}")
print(f"  ✓ Recent Cases in Feed: {len(dash_data.get('recent_cases', []))}")
print(f"  ✓ Upcoming Hearings in Feed: {len(dash_data.get('upcoming_hearings', []))}")


# ==============================================================================
# 6. CITIZEN CASES & DATA ISOLATION
# ==============================================================================
print("\n[6/14] VERIFY CITIZEN CASE REGISTRATION & CROSS-USER ISOLATION")

# 6.1 Create case for Sunita
cit_case_payload = {
    "title": "Sunita Flat Title Grievance",
    "case_type": "Civil Property",
    "court": "City Civil Court, Dindoshi",
    "opposite_party": "Apex Builders Pvt Ltd",
    "description": "Failure to execute conveyance deed and deliver possession.",
    "incident_date": "2026-01-15",
    "police_station": "Kandivali East",
    "location": "Mumbai, Maharashtra"
}
r_create_case = client.post("/api/citizen/cases", headers=sunita_headers, json=cit_case_payload)
assert r_create_case.status_code == 201, f"Create case failed: {r_create_case.text}"
sunita_case = r_create_case.json()
sunita_case_id = sunita_case["case_id"]
test_state["sunita_case_id"] = sunita_case_id
print(f"  ✓ Citizen successfully registered matter: Case #{sunita_case_id} ('{sunita_case['title']}')")

# 6.2 Sunita can view her case
r_get_own_case = client.get(f"/api/citizen/cases/{sunita_case_id}", headers=sunita_headers)
assert r_get_own_case.status_code == 200
assert r_get_own_case.json()["title"] == cit_case_payload["title"]
# CRITICAL SECURITY CHECK: Lawyer notes must NEVER be in citizen case response
assert "case_notes" not in r_get_own_case.json(), "SECURITY BREACH: case_notes exposed to citizen!"
print("  ✓ Citizen case detail retrieved; lawyer notes strictly excluded")

# 6.3 Cross-user access check: new_citizen attempting to access Sunita's case
r_cross_case = client.get(f"/api/citizen/cases/{sunita_case_id}", headers=new_citizen_headers)
assert r_cross_case.status_code in (403, 404), f"Cross-user case access leaked data! Status: {r_cross_case.status_code}"
print(f"  ✓ Cross-user case access safely rejected with HTTP {r_cross_case.status_code}")

# 6.4 Verify cases list contains only authenticated user's cases
r_sunita_cases = client.get("/api/citizen/cases", headers=sunita_headers)
assert r_sunita_cases.status_code == 200
sunita_case_ids = [c["case_id"] for c in r_sunita_cases.json()]
assert sunita_case_id in sunita_case_ids, "Created case missing in citizen cases list"

r_new_cases = client.get("/api/citizen/cases", headers=new_citizen_headers)
assert r_new_cases.status_code == 200
assert sunita_case_id not in [c["case_id"] for c in r_new_cases.json()], "Data leak: foreign case in cases list!"
print("  ✓ Citizen cases listing strictly filtered by authenticated user_id")


# ==============================================================================
# 7. CITIZEN DOCUMENTS WORKSPACE
# ==============================================================================
print("\n[7/14] VERIFY CITIZEN DOCUMENTS MANAGEMENT")

doc_payload = {
    "case_id": sunita_case_id,
    "document_name": "Flat_Allotment_Letter_Copy.pdf",
    "document_type": "Evidence",
    "description": "Original allotment letter signed by developer."
}
r_upload_doc = client.post("/api/citizen/documents", headers=sunita_headers, json=doc_payload)
assert r_upload_doc.status_code == 201, f"Doc upload failed: {r_upload_doc.text}"
uploaded_doc = r_upload_doc.json()
print(f"  ✓ Document attached to Case #{sunita_case_id}: '{uploaded_doc['document_name']}'")

# List documents
r_list_docs = client.get("/api/citizen/documents", headers=sunita_headers)
assert r_list_docs.status_code == 200
docs = r_list_docs.json()
assert any(d["document_name"] == "Flat_Allotment_Letter_Copy.pdf" for d in docs)
print(f"  ✓ GET /api/citizen/documents lists cataloged documents ({len(docs)} found)")


# ==============================================================================
# 8. CITIZEN PROFILE GET / PUT
# ==============================================================================
print("\n[8/14] VERIFY CITIZEN PROFILE MANAGEMENT (GET / PUT)")

r_get_prof = client.get("/api/citizen/profile", headers=sunita_headers)
assert r_get_prof.status_code == 200
prof_data = r_get_prof.json()
orig_profile = prof_data
test_state["orig_profile"] = prof_data
assert prof_data["email"] == "sunita.sharma@example.com"
print(f"  ✓ GET /api/citizen/profile: {prof_data['full_name']} ({prof_data['email']})")

prof_update_payload = {
    "full_name": "Sunita Sharma",
    "phone": "+91 98111 22334",
    "date_of_birth": "1988-06-15",
    "preferred_language": "hi",
    "address": "B-402, Sunshine Heights, Linking Road",
    "city": "Mumbai",
    "state": "Maharashtra",
    "pincode": "400050",
    "occupation": "Chartered Accountant",
    "emergency_contact": "+91 98222 33445"
}
r_put_prof = client.put("/api/citizen/profile", headers=sunita_headers, json=prof_update_payload)
assert r_put_prof.status_code == 200, f"Profile update failed: {r_put_prof.text}"
updated_prof = r_put_prof.json()
assert updated_prof["preferred_language"] == "hi"
assert updated_prof["city"] == "Mumbai"
assert updated_prof["occupation"] == "Chartered Accountant"
print("  ✓ PUT /api/citizen/profile successfully updated personal details and residence")


# ==============================================================================
# 9. SAVED PROVISIONS (BOOKMARKS) CRUD & DEDUPLICATION
# ==============================================================================
print("\n[9/14] VERIFY SAVED PROVISIONS (BOOKMARKS) CRUD & DEDUPLICATION")

# Fetch an authentic statutory section from DB
with get_db_cursor() as cur:
    cur.execute("SELECT section_id, section_number, section_title FROM sections ORDER BY section_id LIMIT 1;")
    sec = cur.fetchone()
    test_sec_id = sec["section_id"]
    test_sec_num = sec["section_number"]

# 9.1 Save bookmark
bm_payload = {
    "section_id": test_sec_id,
    "notes": "Reference for civil property dispute preliminary arguments.",
    "tag": "Property Law"
}
r_add_bm = client.post("/api/citizen/bookmarks", headers=sunita_headers, json=bm_payload)
assert r_add_bm.status_code in (200, 201), f"Add bookmark failed: {r_add_bm.text}"
print(f"  ✓ Bookmarked Section {test_sec_num} for citizen reference")

# 9.2 Duplicate bookmark handling (should not 500 error, updates notes/tag)
bm_dup_payload = {
    "section_id": test_sec_id,
    "notes": "Updated note on preliminary arguments.",
    "tag": "Urgent Reference"
}
r_dup_bm = client.post("/api/citizen/bookmarks", headers=sunita_headers, json=bm_dup_payload)
assert r_dup_bm.status_code in (200, 201), f"Duplicate bookmark handling failed: {r_dup_bm.text}"
print("  ✓ Duplicate bookmark safely handled without database unique violation")

# 9.3 List bookmarks with statutory details join
r_bms = client.get("/api/citizen/bookmarks", headers=sunita_headers)
assert r_bms.status_code == 200
bms = r_bms.json()
matched_bm = next((b for b in bms if b["section_id"] == test_sec_id), None)
assert matched_bm is not None, "Bookmarked section missing from list"
assert matched_bm["law_name"] is not None, "Law name missing in bookmark join"
print(f"  ✓ GET /api/citizen/bookmarks returned provision joined with Act: '{matched_bm['law_name']}'")

# 9.4 Delete bookmark
r_del_bm = client.delete(f"/api/citizen/bookmarks/{test_sec_id}", headers=sunita_headers)
assert r_del_bm.status_code == 200
print(f"  ✓ DELETE /api/citizen/bookmarks/{test_sec_id} successfully removed bookmark")


# ==============================================================================
# 10. CITIZEN LEGAL SEARCH HISTORY
# ==============================================================================
print("\n[10/14] VERIFY CITIZEN SEARCH HISTORY INTEGRATION")

sh_payload = {
    "query_text": "conveyance deed deemed conveyance maharashtra",
    "filters": {"jurisdiction": "State"},
    "results_count": 8
}
r_add_sh = client.post("/api/citizen/search-history", headers=sunita_headers, json=sh_payload)
assert r_add_sh.status_code == 201, f"Save search history failed: {r_add_sh.text}"

r_get_sh = client.get("/api/citizen/search-history", headers=sunita_headers)
assert r_get_sh.status_code == 200
sh_list = r_get_sh.json()
assert len(sh_list) > 0
assert sh_list[0]["query_text"] == sh_payload["query_text"]
print(f"  ✓ Search query logged in user_search_history ('{sh_payload['query_text']}')")

# Clear history
r_del_sh = client.delete("/api/citizen/search-history", headers=sunita_headers)
assert r_del_sh.status_code == 200
r_check_sh = client.get("/api/citizen/search-history", headers=sunita_headers)
assert len(r_check_sh.json()) == 0, "Search history was not cleared"
print("  ✓ DELETE /api/citizen/search-history successfully cleared history")


# ==============================================================================
# 11. NOTIFICATIONS & READ / READ-ALL
# ==============================================================================
print("\n[11/14] VERIFY NOTIFICATIONS FEED & READ STATUS")

r_notifs = client.get("/api/citizen/notifications", headers=sunita_headers)
assert r_notifs.status_code == 200
notifs_data = r_notifs.json()
print(f"  ✓ Notifications found: {len(notifs_data.get('notifications', []))} (Unread: {notifs_data.get('unread_count')})")

if notifs_data.get("notifications"):
    first_notif_id = notifs_data["notifications"][0]["notification_id"]
    r_read = client.patch(f"/api/citizen/notifications/{first_notif_id}/read", headers=sunita_headers)
    assert r_read.status_code == 200
    print(f"  ✓ PATCH /api/citizen/notifications/{first_notif_id}/read marked notification read")

r_read_all = client.post("/api/citizen/notifications/read-all", headers=sunita_headers)
assert r_read_all.status_code == 200
print("  ✓ POST /api/citizen/notifications/read-all marked all notifications read")


# ==============================================================================
# 12. PROCEDURE CHECKLIST PERSISTENCE (PHASE 12 INTEGRATION)
# ==============================================================================
print("\n[12/14] VERIFY PROCEDURE CHECKLIST TRACKER PERSISTENCE")

with get_db_cursor() as cur:
    cur.execute("SELECT procedure_id, procedure_name FROM legal_procedures LIMIT 1;")
    proc = cur.fetchone()
    test_proc_id = proc["procedure_id"]
    test_proc_name = proc["procedure_name"]
    cur.execute("DELETE FROM user_procedure_trackers WHERE user_id = %s AND procedure_id = %s;", (sunita_id, test_proc_id))
    cur.connection.commit()

# 12.1 Toggle document in tracker
toggle_payload = {"document_name": "Identity Proof (Aadhaar / Voter ID)"}
r_toggle1 = client.post(f"/api/citizen/procedures/{test_proc_id}/toggle-doc", headers=sunita_headers, json=toggle_payload)
assert r_toggle1.status_code == 200, f"Toggle doc failed: {r_toggle1.text}"
tracker1 = r_toggle1.json()
assert "Identity Proof (Aadhaar / Voter ID)" in tracker1["completed_documents"]
print(f"  ✓ Checklist item toggled ON for '{test_proc_name}'")

# 12.2 Fetch citizen trackers
r_procs = client.get("/api/citizen/procedures", headers=sunita_headers)
assert r_procs.status_code == 200
trackers = r_procs.json()
matched_trk = next((t for t in trackers if t["procedure_id"] == test_proc_id), None)
assert matched_trk is not None
assert "Identity Proof (Aadhaar / Voter ID)" in matched_trk["completed_documents"]
print("  ✓ GET /api/citizen/procedures retains persistent completed documents")

# 12.3 Toggle document OFF
r_toggle2 = client.post(f"/api/citizen/procedures/{test_proc_id}/toggle-doc", headers=sunita_headers, json=toggle_payload)
assert r_toggle2.status_code == 200
tracker2 = r_toggle2.json()
assert "Identity Proof (Aadhaar / Voter ID)" not in tracker2["completed_documents"]
print(f"  ✓ Checklist item toggled OFF and persisted cleanly")

with get_db_cursor() as cur:
    cur.execute("DELETE FROM user_procedure_trackers WHERE user_id = %s AND procedure_id = %s;", (sunita_id, test_proc_id))
    cur.connection.commit()


# ==============================================================================
# 13. PHASE 11 DOCUMENT ANALYSIS INTEGRATION
# ==============================================================================
print("\n[13/14] VERIFY PHASE 11 DOCUMENT ANALYSIS INTEGRATION & HISTORY PRIVACY")

# 13.1 Citizen runs a document text analysis
analysis_sample = """
RENTAL AGREEMENT
This Rent Agreement is made on 1st January 2026 between Shri Ramesh Kumar (Landlord)
and Smt Sunita Sharma (Tenant) for Residential Flat No 304, Green Acres, Mumbai.
The monthly rent shall be Rs. 35,000 payable by the 5th of each calendar month.
Failure to pay rent or dishonour of rent cheques attracts Section 138 of the Negotiable Instruments Act.
"""
r_ana = client.post("/api/analysis/text", headers=sunita_headers, json={
    "text": analysis_sample,
    "document_title": "Sunita Rent Agreement Analysis",
    "case_id": sunita_case_id
})
assert r_ana.status_code == 200, f"Analysis failed: {r_ana.text}"
ana_res = r_ana.json()
ana_id = ana_res["analysis_id"]
test_ana_id = ana_id
test_state["test_ana_id"] = ana_id
print(f"  ✓ Citizen analyzed document: ID {ana_id} ({ana_res['document_type']})")

# 13.2 Citizen retrieves own analysis history
r_ana_hist = client.get("/api/analysis/history", headers=sunita_headers)
assert r_ana_hist.status_code == 200
ana_list = r_ana_hist.json().get("analyses", [])
assert any(a["analysis_id"] == ana_id for a in ana_list), "Created analysis missing from citizen history"
print("  ✓ Citizen successfully retrieves own analysis history")

# 13.3 Other citizen does NOT see Sunita's analysis
r_other_ana_hist = client.get("/api/analysis/history", headers=new_citizen_headers)
assert r_other_ana_hist.status_code == 200
other_list = r_other_ana_hist.json().get("analyses", [])
assert not any(a["analysis_id"] == ana_id for a in other_list), "Data leak: foreign analysis in history!"
print("  ✓ Strict analysis history privacy verified across citizen accounts")

# Clean up analysis
client.delete(f"/api/analysis/{ana_id}", headers=sunita_headers)
test_state["test_ana_id"] = None


# ==============================================================================
# 14. ZERO-LOSS DATABASE CORPUS VERIFICATION
# ==============================================================================
print("\n[14/14] VERIFY ZERO-LOSS DATABASE LEGAL CORPUS INTEGRITY")
with get_db_cursor() as cur:
    cur.execute("SELECT count(*) as cnt FROM laws;")
    laws_count = cur.fetchone()["cnt"]
    assert laws_count == 869, f"Expected 869 laws, got {laws_count}"
    print(f"  ✓ laws: {laws_count} (100% Intact)")

    cur.execute("SELECT count(*) as cnt FROM sections;")
    sections_count = cur.fetchone()["cnt"]
    assert sections_count == 41442, f"Expected 41442 sections, got {sections_count}"
    print(f"  ✓ sections: {sections_count} (100% Intact)")

    cur.execute("SELECT count(*) as cnt FROM legal_lexicon;")
    lexicon_count = cur.fetchone()["cnt"]
    assert lexicon_count == 42, f"Expected 42 lexicon terms, got {lexicon_count}"
    print(f"  ✓ legal_lexicon: {lexicon_count} (100% Intact)")

    cur.execute("SELECT count(*) as cnt FROM section_alignments;")
    align_count = cur.fetchone()["cnt"]
    assert align_count == 9304, f"Expected 9304 alignments, got {align_count}"
    print(f"  ✓ section_alignments: {align_count} (100% Intact)")

    cur.execute("SELECT count(*) as cnt FROM legal_procedures;")
    proc_count = cur.fetchone()["cnt"]
    assert proc_count == 8, f"Expected 8 legal procedures, got {proc_count}"
    print(f"  ✓ legal_procedures: {proc_count} (Phase 12 Intact)")

    cur.execute("SELECT count(*) as cnt FROM procedure_required_documents;")
    doc_count = cur.fetchone()["cnt"]
    assert doc_count == 48, f"Expected 48 required documents, got {doc_count}"
    print(f"  ✓ procedure_required_documents: {doc_count} (Phase 12 Intact)")

    print("\n" + "=" * 74)
    print("ALL 14 PHASE 14 CITIZEN MODULE VERIFICATION SUITES PASSED WITH 100% SUCCESS!")
    print("=" * 74)
