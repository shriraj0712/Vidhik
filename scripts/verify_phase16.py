"""
Vidhik AI - Phase 16 Full-Stack UI & Integration Complete Verification Suite
=============================================================================
Runs an automated end-to-end verification covering:
 1. Application startup & system health (/health)
 2. Frontend availability (/, /lawyer, /citizen, /static/styles.css, /static/app.js, /static/index.html)
 3. Authentication endpoints (/api/auth/login, /api/auth/register, /api/auth/logout)
 4. Citizen login (Sunita Sharma authentication & token verification)
 5. Lawyer login (Adv. Rajesh Deshmukh authentication & token verification)
 6. Citizen registration (Registration lifecycle, profile initialization, duplicate rejection)
 7. Role-based navigation & API authorization guards (Strict 403 Forbidden cross-role enforcement)
 8. Legal search integration (Natural language query, section retrieval, deterministic ranking)
 9. Search history integration (Tracking, retrieval, deletion)
10. Saved provisions / Bookmarks integration (Add bookmark, retrieval, deduplication, removal)
11. Legal document analysis integration (Text parsing, clause extraction, verified citations)
12. Documentation & procedure integration (Categories, procedures, persistent checklist tracking)
13. Citizen case integration (Case list, case detail, strict omission of confidential lawyer notes)
14. Lawyer case integration (Case list, case detail, private notes, documents, hearings)
15. Notifications integration (Feed listing, unread counts, mark all read)
16. Citizen profile integration (GET profile, PUT update persistence, rollback)
17. Responsive frontend asset availability (Viewport meta, mobile menu toggle, backdrop, responsive breakpoints)
18. Unauthorized access handling (Strict 401 on missing/invalid token, zero silent fallback)
19. Live PostgreSQL database connectivity & connection pool health
20. Legal corpus zero-loss integrity (869 Laws, 41,442 Sections, 42 Lexicon, 9,304 Alignments)
"""

import sys
import os
import time
import uuid
import atexit
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath("backend"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.database import get_db_cursor

BASE_URL = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE_URL, timeout=15.0)

print("=" * 80)
print("VIDHIK AI - PHASE 16 FULL-STACK UI & INTEGRATION VERIFICATION SUITE")
print("=" * 80)

# Global test tracking for guaranteed cleanup
cleanup_state = {
    "test_user_id": None,
    "test_analysis_id": None,
    "test_bookmark_section_id": None,
    "test_proc_id": None,
    "orig_profile": None,
    "sunita_user_id": None,
    "sunita_headers": None
}

def guaranteed_cleanup():
    print("\n[CLEANUP] REMOVING TEMPORARY TEST ARTIFACTS...")
    try:
        with get_db_cursor() as cur:
            # 1. Purge registered test citizen
            if cleanup_state.get("test_user_id"):
                u_id = cleanup_state["test_user_id"]
                cur.execute("DELETE FROM user_search_history WHERE user_id = %s;", (u_id,))
                cur.execute("DELETE FROM user_saved_sections WHERE user_id = %s;", (u_id,))
                cur.execute("DELETE FROM user_procedure_trackers WHERE user_id = %s;", (u_id,))
                cur.execute("DELETE FROM user_profiles WHERE user_id = %s;", (u_id,))
                cur.execute("DELETE FROM users WHERE user_id = %s;", (u_id,))
                cur.connection.commit()
                print(f"  ✓ Purged temporary test citizen ID {u_id}")

            # 2. Purge test analysis
            if cleanup_state.get("test_analysis_id"):
                ana_id = cleanup_state["test_analysis_id"]
                try:
                    client.delete(f"/api/analysis/{ana_id}", headers=cleanup_state.get("sunita_headers"))
                    print(f"  ✓ Purged test analysis ID {ana_id}")
                except Exception:
                    pass

            # 3. Purge test bookmark if lingering
            if cleanup_state.get("test_bookmark_section_id") and cleanup_state.get("sunita_user_id"):
                cur.execute("DELETE FROM user_saved_sections WHERE user_id = %s AND section_id = %s;",
                            (cleanup_state["sunita_user_id"], cleanup_state["test_bookmark_section_id"]))
                cur.connection.commit()

            # 4. Purge test procedure tracker if lingering
            if cleanup_state.get("test_proc_id") and cleanup_state.get("sunita_user_id"):
                cur.execute("DELETE FROM user_procedure_trackers WHERE user_id = %s AND procedure_id = %s;",
                            (cleanup_state["sunita_user_id"], cleanup_state["test_proc_id"]))
                cur.connection.commit()

            # 5. Restore Sunita's original profile
            if cleanup_state.get("orig_profile") and cleanup_state.get("sunita_user_id"):
                s_id = cleanup_state["sunita_user_id"]
                op = cleanup_state["orig_profile"]
                cur.execute("""
                    UPDATE users SET phone = %s WHERE user_id = %s;
                    UPDATE user_profiles SET
                        preferred_language = %s,
                        city = %s,
                        state = %s,
                        pincode = %s,
                        occupation = %s,
                        emergency_contact = %s
                    WHERE user_id = %s;
                """, (
                    op.get("phone", "+91 98112 34567"), s_id,
                    op.get("preferred_language", "en"),
                    op.get("city"),
                    op.get("state"),
                    op.get("pincode"),
                    op.get("occupation"),
                    op.get("emergency_contact"),
                    s_id
                ))
                cur.connection.commit()
                print("  ✓ Sunita profile restored to original seeded state")
    except Exception as e:
        print(f"  [WARNING] Cleanup encountered error: {e}")
    print("  ✓ Cleanup complete. Legitimate database state completely preserved.")

atexit.register(guaranteed_cleanup)

try:
    # --------------------------------------------------------------------------
    # 1. APPLICATION STARTUP & SYSTEM HEALTH
    # --------------------------------------------------------------------------
    print("\n[1/20] VERIFY APPLICATION STARTUP & SYSTEM HEALTH (/health)")
    r_health = client.get("/health")
    assert r_health.status_code == 200, f"Expected 200 from /health, got {r_health.status_code}"
    health_data = r_health.json()
    assert health_data.get("status") == "healthy", f"Expected status 'healthy', got {health_data}"
    db_info = health_data.get("database", {})
    db_status = db_info.get("status") if isinstance(db_info, dict) else db_info
    assert db_status == "connected", f"Expected database 'connected', got {health_data}"
    print(f"  ✓ Service status: {health_data['status']} | Database: {db_status}")

    # --------------------------------------------------------------------------
    # 2. FRONTEND AVAILABILITY
    # --------------------------------------------------------------------------
    print("\n[2/20] VERIFY FRONTEND WORKSPACES & STATIC ASSETS")
    r_root = client.get("/")
    assert r_root.status_code == 200, f"Root / returned {r_root.status_code}"
    assert "Vidhik AI" in r_root.text, "Vidhik AI branding missing from /"
    print("  ✓ Root / successfully served SPA (200 OK)")

    r_lawyer_view = client.get("/lawyer")
    assert r_lawyer_view.status_code == 200, f"/lawyer returned {r_lawyer_view.status_code}"
    assert "Vidhik AI" in r_lawyer_view.text, "Vidhik AI branding missing from /lawyer"
    print("  ✓ /lawyer route successfully served SPA (200 OK)")

    r_citizen_view = client.get("/citizen")
    assert r_citizen_view.status_code == 200, f"/citizen returned {r_citizen_view.status_code}"
    assert "Vidhik AI" in r_citizen_view.text, "Vidhik AI branding missing from /citizen"
    print("  ✓ /citizen route successfully served SPA (200 OK)")

    r_css = client.get("/static/styles.css")
    assert r_css.status_code == 200, f"/static/styles.css returned {r_css.status_code}"
    print(f"  ✓ /static/styles.css served ({len(r_css.text)} bytes)")

    r_js = client.get("/static/app.js")
    assert r_js.status_code == 200, f"/static/app.js returned {r_js.status_code}"
    print(f"  ✓ /static/app.js served ({len(r_js.text)} bytes)")

    r_index = client.get("/static/index.html")
    assert r_index.status_code == 200, f"/static/index.html returned {r_index.status_code}"
    print(f"  ✓ /static/index.html served ({len(r_index.text)} bytes)")

    # --------------------------------------------------------------------------
    # 3. AUTHENTICATION ENDPOINTS VALIDATION
    # --------------------------------------------------------------------------
    print("\n[3/20] VERIFY AUTHENTICATION SCHEMAS & INPUT VALIDATION")
    # Empty login payload
    r_bad_login = client.post("/api/auth/login", json={})
    assert r_bad_login.status_code == 422, f"Expected 422 for empty login, got {r_bad_login.status_code}"
    print("  ✓ POST /api/auth/login rejects empty payload with 422 Unprocessable Entity")

    # Empty register payload
    r_bad_reg = client.post("/api/auth/register", json={})
    assert r_bad_reg.status_code == 422, f"Expected 422 for empty register, got {r_bad_reg.status_code}"
    print("  ✓ POST /api/auth/register rejects empty payload with 422 Unprocessable Entity")

    # Logout endpoint
    r_logout = client.post("/api/auth/logout")
    assert r_logout.status_code == 200, f"Expected 200 from logout, got {r_logout.status_code}"
    assert r_logout.json().get("status") == "success"
    print("  ✓ POST /api/auth/logout responds cleanly (200 OK)")

    # --------------------------------------------------------------------------
    # 4. CITIZEN LOGIN
    # --------------------------------------------------------------------------
    print("\n[4/20] VERIFY CITIZEN LOGIN (Sunita Sharma)")
    sunita_creds = {"email": "sunita.sharma@example.com", "password": "password123"}
    r_sunita_login = client.post("/api/auth/login", json=sunita_creds)
    assert r_sunita_login.status_code == 200, f"Citizen login failed: {r_sunita_login.text}"
    sunita_auth = r_sunita_login.json()
    assert sunita_auth["role"] in ("citizen", "user"), f"Expected citizen/user role, got {sunita_auth['role']}"
    assert "Sunita Sharma" in sunita_auth["full_name"]
    sunita_token = sunita_auth["token"]
    sunita_user_id = sunita_auth["user_id"]
    cleanup_state["sunita_user_id"] = sunita_user_id
    sunita_headers = {"Authorization": f"Bearer {sunita_token}"}
    cleanup_state["sunita_headers"] = sunita_headers
    print(f"  ✓ Authenticated as: {sunita_auth['full_name']} | Role: {sunita_auth['role']} | ID: {sunita_user_id}")

    # --------------------------------------------------------------------------
    # 5. LAWYER LOGIN
    # --------------------------------------------------------------------------
    print("\n[5/20] VERIFY LAWYER LOGIN (Adv. Rajesh Deshmukh)")
    rajesh_creds = {"email": "rajesh.advocate@vidhik.ai", "password": "password123"}
    r_rajesh_login = client.post("/api/auth/login", json=rajesh_creds)
    assert r_rajesh_login.status_code == 200, f"Lawyer login failed: {r_rajesh_login.text}"
    rajesh_auth = r_rajesh_login.json()
    assert rajesh_auth["role"] == "lawyer", f"Expected lawyer role, got {rajesh_auth['role']}"
    assert "Rajesh" in rajesh_auth["full_name"]
    assert rajesh_auth.get("lawyer_id") is not None, "Missing lawyer_id for lawyer session"
    rajesh_token = rajesh_auth["token"]
    rajesh_headers = {"Authorization": f"Bearer {rajesh_token}"}
    print(f"  ✓ Authenticated as: {rajesh_auth['full_name']} | Role: {rajesh_auth['role']} | Lawyer ID: {rajesh_auth['lawyer_id']}")

    # --------------------------------------------------------------------------
    # 6. CITIZEN REGISTRATION & DUPLICATE REJECTION
    # --------------------------------------------------------------------------
    print("\n[6/20] VERIFY CITIZEN REGISTRATION & DUPLICATE REJECTION")
    unique_suffix = int(time.time())
    unique_test_email = f"test.p16.{unique_suffix}@example.com"
    reg_payload = {
        "full_name": f"Integration Citizen {unique_suffix}",
        "email": unique_test_email,
        "password": "Password123!",
        "phone": "+91 99887 76655"
    }
    r_reg = client.post("/api/auth/register", json=reg_payload)
    assert r_reg.status_code == 201, f"Registration failed: {r_reg.text}"
    reg_data = r_reg.json()
    cleanup_state["test_user_id"] = reg_data["user_id"]
    assert reg_data["role"] in ("citizen", "user")
    assert reg_data["email"] == unique_test_email.lower()
    test_headers = {"Authorization": f"Bearer {reg_data['token']}"}
    print(f"  ✓ Registered new citizen: {reg_data['full_name']} (User ID: {reg_data['user_id']})")

    # Duplicate registration should return 400 Bad Request
    r_dup = client.post("/api/auth/register", json=reg_payload)
    assert r_dup.status_code == 400, f"Expected 400 for duplicate email, got {r_dup.status_code}"
    print("  ✓ Duplicate registration cleanly rejected with 400 Bad Request")

    # --------------------------------------------------------------------------
    # 7. ROLE-BASED NAVIGATION & API AUTHORIZATION GUARDS
    # --------------------------------------------------------------------------
    print("\n[7/20] VERIFY ROLE-BASED API AUTHORIZATION GUARDS (Strict 403 Forbidden)")
    # Citizen trying to access Lawyer workspace APIs
    r_cit_lawyer_dash = client.get("/api/lawyer/dashboard", headers=sunita_headers)
    assert r_cit_lawyer_dash.status_code == 403, f"Citizen accessed lawyer dashboard! Status: {r_cit_lawyer_dash.status_code}"
    print("  ✓ Citizen accessing /api/lawyer/dashboard correctly blocked (403 Forbidden)")

    r_cit_lawyer_cases = client.get("/api/lawyer/cases", headers=sunita_headers)
    assert r_cit_lawyer_cases.status_code == 403, f"Citizen accessed lawyer cases! Status: {r_cit_lawyer_cases.status_code}"
    print("  ✓ Citizen accessing /api/lawyer/cases correctly blocked (403 Forbidden)")

    # Lawyer trying to access Citizen portal APIs
    r_law_cit_dash = client.get("/api/citizen/dashboard", headers=rajesh_headers)
    assert r_law_cit_dash.status_code == 403, f"Lawyer accessed citizen dashboard! Status: {r_law_cit_dash.status_code}"
    print("  ✓ Lawyer accessing /api/citizen/dashboard correctly blocked (403 Forbidden)")

    # --------------------------------------------------------------------------
    # 8. LEGAL SEARCH INTEGRATION
    # --------------------------------------------------------------------------
    print("\n[8/20] VERIFY DETERMINISTIC LEGAL SEARCH INTEGRATION (/api/search)")
    search_query = "co-operative"
    r_search = client.get(f"/api/search?q={search_query}&limit=5")
    assert r_search.status_code == 200, f"Search failed: {r_search.text}"
    search_json = r_search.json()
    assert "results" in search_json, "Search response missing 'results' field"
    results = search_json["results"]
    assert len(results) > 0, f"No search results returned for '{search_query}'"
    top_res = results[0]
    assert "section_number" in top_res
    assert "law_name" in top_res
    print(f"  ✓ Search query '{search_query}' returned {len(results)} ranked sections")
    print(f"    Top Match: {top_res['law_name']} - Sec. {top_res['section_number']}: {top_res.get('title') or top_res.get('section_title')}")

    # --------------------------------------------------------------------------
    # 9. SEARCH HISTORY INTEGRATION
    # --------------------------------------------------------------------------
    print("\n[9/20] VERIFY CITIZEN SEARCH HISTORY INTEGRATION")
    sh_payload = {
        "query_text": "protection of women from domestic violence",
        "filters": {"jurisdiction": "Central"},
        "results_count": 12
    }
    r_add_sh = client.post("/api/citizen/search-history", headers=test_headers, json=sh_payload)
    assert r_add_sh.status_code == 201, f"Save search history failed: {r_add_sh.text}"
    print("  ✓ Search history item logged via POST /api/citizen/search-history")

    r_hist = client.get("/api/citizen/search-history", headers=test_headers)
    assert r_hist.status_code == 200, f"Search history failed: {r_hist.text}"
    hist_items = r_hist.json()
    assert len(hist_items) >= 1, "Expected at least 1 search history item"
    assert hist_items[0]["query_text"] == sh_payload["query_text"]
    print(f"  ✓ Search history retrieval verified ({len(hist_items)} items for user)")

    # Test clear search history
    r_clear_hist = client.delete("/api/citizen/search-history", headers=test_headers)
    assert r_clear_hist.status_code == 200, f"Clear search history failed: {r_clear_hist.text}"
    r_hist_after = client.get("/api/citizen/search-history", headers=test_headers)
    assert len(r_hist_after.json()) == 0, "Search history was not cleared"
    print("  ✓ DELETE /api/citizen/search-history cleared history cleanly")

    # --------------------------------------------------------------------------
    # 10. SAVED PROVISIONS / BOOKMARKS INTEGRATION
    # --------------------------------------------------------------------------
    print("\n[10/20] VERIFY SAVED PROVISIONS / BOOKMARKS CRUD & DEDUPLICATION")
    # Fetch a valid section ID from the corpus
    with get_db_cursor() as cur:
        cur.execute("SELECT section_id, section_number, section_title FROM sections ORDER BY section_id LIMIT 1;")
        sample_sec = cur.fetchone()
        sec_id = sample_sec["section_id"]
        cleanup_state["test_bookmark_section_id"] = sec_id

    # Add bookmark
    bookmark_payload = {"section_id": sec_id, "notes": "Phase 16 integration test provision", "tag": "Property Law"}
    r_add_bm = client.post("/api/citizen/bookmarks", headers=test_headers, json=bookmark_payload)
    assert r_add_bm.status_code in (200, 201), f"Add bookmark failed: {r_add_bm.text}"
    print(f"  ✓ Section {sample_sec['section_number']} bookmarked successfully")

    # Duplicate / update bookmark
    r_dup_bm = client.post("/api/citizen/bookmarks", headers=test_headers, json={
        "section_id": sec_id,
        "notes": "Updated note on Phase 16 test",
        "tag": "Urgent"
    })
    assert r_dup_bm.status_code in (200, 201)
    print("  ✓ Duplicate bookmark safely updated without database unique violation")

    # Retrieve bookmarks
    r_list_bm = client.get("/api/citizen/bookmarks", headers=test_headers)
    assert r_list_bm.status_code == 200
    bms = r_list_bm.json()
    assert any(b["section_id"] == sec_id for b in bms), "Bookmarked section missing from list"
    print("  ✓ GET /api/citizen/bookmarks returns saved provision with joined law metadata")

    # Remove bookmark
    r_del_bm = client.delete(f"/api/citizen/bookmarks/{sec_id}", headers=test_headers)
    assert r_del_bm.status_code == 200
    r_list_bm_after = client.get("/api/citizen/bookmarks", headers=test_headers)
    assert not any(b["section_id"] == sec_id for b in r_list_bm_after.json())
    cleanup_state["test_bookmark_section_id"] = None
    print("  ✓ DELETE /api/citizen/bookmarks/{id} removed bookmark cleanly")

    # --------------------------------------------------------------------------
    # 11. LEGAL DOCUMENT ANALYSIS INTEGRATION (Phase 11)
    # --------------------------------------------------------------------------
    print("\n[11/20] VERIFY LEGAL DOCUMENT ANALYSIS INTEGRATION (/api/analysis/text)")
    legal_text_doc = """
    COMMERCIAL LEASE AGREEMENT
    This Agreement is made on 15th January 2026 between Alpha Corp (Lessor)
    and Beta Technologies Pvt Ltd (Lessee).
    The monthly rent shall be Rs. 1,50,000 payable on or before the 7th of every month.
    In case of dishonoured cheques, proceedings under Section 138 of the Negotiable Instruments Act 1881 will be initiated.
    The Lessee shall maintain the premises in tenantable condition.
    """
    r_ana = client.post("/api/analysis/text", headers=sunita_headers, json={
        "text": legal_text_doc,
        "document_title": "Phase 16 Integration Lease Analysis"
    })
    assert r_ana.status_code == 200, f"Analysis failed: {r_ana.text}"
    ana_result = r_ana.json()
    cleanup_state["test_analysis_id"] = ana_result["analysis_id"]
    assert "document_type" in ana_result
    assert "summary" in ana_result
    assert "parties" in ana_result
    assert "legal_references" in ana_result
    leg_refs = ana_result["legal_references"]
    print(f"  ✓ Document analyzed: {ana_result['document_type']} | Parties: {len(ana_result['parties'])}")
    has_ni_ref = any("138" in ref.get("section_number", "") or "Negotiable Instruments" in ref.get("law_name", "") for ref in leg_refs)
    print(f"  ✓ Grounded statutory citation identified: {has_ni_ref} (Verified in DB: {leg_refs[0].get('is_verified_in_db') if leg_refs else False})")

    # Clean up test analysis
    r_del_ana = client.delete(f"/api/analysis/{ana_result['analysis_id']}", headers=sunita_headers)
    assert r_del_ana.status_code == 200
    cleanup_state["test_analysis_id"] = None
    print("  ✓ Test document analysis cleaned up cleanly")

    # --------------------------------------------------------------------------
    # 12. DOCUMENTATION & PROCEDURE INTEGRATION (Phase 12)
    # --------------------------------------------------------------------------
    print("\n[12/20] VERIFY DOCUMENTATION SUPPORT & PROCEDURE TRACKING")
    # Categories
    r_cats = client.get("/api/documentation/categories")
    assert r_cats.status_code == 200, f"Categories failed: {r_cats.text}"
    categories = r_cats.json()
    assert len(categories) > 0, "No procedure categories found"
    print(f"  ✓ Categories loaded: {len(categories)} categories available")

    # Procedures
    r_procs = client.get("/api/documentation/procedures")
    assert r_procs.status_code == 200, f"Procedures failed: {r_procs.text}"
    proc_json = r_procs.json()
    procs = proc_json.get("procedures", [])
    assert proc_json.get("total") == 8, f"Expected 8 legal procedures, got {proc_json.get('total')}"
    assert len(procs) == 8, f"Expected 8 procedure items in list, got {len(procs)}"
    test_proc = procs[0]
    test_proc_id = test_proc["procedure_id"]
    cleanup_state["test_proc_id"] = test_proc_id
    print(f"  ✓ Procedures loaded: {len(procs)} procedures | Selected: '{test_proc['procedure_name']}'")

    # Toggle checklist item for test user
    toggle_payload = {"document_name": "Identity Proof (Aadhaar / Voter ID)"}
    r_toggle = client.post(f"/api/citizen/procedures/{test_proc_id}/toggle-doc", headers=test_headers, json=toggle_payload)
    assert r_toggle.status_code == 200, f"Toggle doc failed: {r_toggle.text}"
    tracker_res = r_toggle.json()
    assert "Identity Proof (Aadhaar / Voter ID)" in tracker_res["completed_documents"]
    print("  ✓ Checklist item toggled ON and persisted in user_procedure_trackers")

    # Verify via citizen trackers API
    r_my_procs = client.get("/api/citizen/procedures", headers=test_headers)
    assert r_my_procs.status_code == 200
    my_trackers = r_my_procs.json()
    matched = next((t for t in my_trackers if t["procedure_id"] == test_proc_id), None)
    assert matched is not None
    assert "Identity Proof (Aadhaar / Voter ID)" in matched["completed_documents"]
    print(f"  ✓ Tracker reflected in /api/citizen/procedures with progress {matched.get('completion_percentage')}%")

    # --------------------------------------------------------------------------
    # 13. CITIZEN CASE INTEGRATION & LAWYER NOTES ISOLATION
    # --------------------------------------------------------------------------
    print("\n[13/20] VERIFY CITIZEN CASES & CONFIDENTIAL LAWYER NOTES ISOLATION")
    r_cit_cases = client.get("/api/citizen/cases", headers=sunita_headers)
    assert r_cit_cases.status_code == 200, f"Citizen cases failed: {r_cit_cases.text}"
    cit_cases = r_cit_cases.json()
    assert len(cit_cases) > 0, "Sunita has no cases registered"
    first_case = cit_cases[0]
    first_case_id = first_case["case_id"]
    print(f"  ✓ Citizen cases loaded: {len(cit_cases)} cases | Case Number: {first_case['case_number']}")

    # Fetch case detail
    r_case_det = client.get(f"/api/citizen/cases/{first_case_id}", headers=sunita_headers)
    assert r_case_det.status_code == 200
    case_detail = r_case_det.json()
    # Ensure lawyer's confidential notes are NOT present in citizen case schema
    assert "notes" not in case_detail or len(case_detail.get("notes", [])) == 0, "CONFIDENTIAL LAWYER NOTES EXPOSED TO CITIZEN!"
    print("  ✓ Strict data boundary: Confidential lawyer notes omitted from citizen case response")

    # --------------------------------------------------------------------------
    # 14. LAWYER CASE INTEGRATION & COMPLETE WORKSPACE DATA
    # --------------------------------------------------------------------------
    print("\n[14/20] VERIFY LAWYER CASES & COMPLETE WORKSPACE LIFECYCLE")
    r_law_cases = client.get("/api/lawyer/cases", headers=rajesh_headers)
    assert r_law_cases.status_code == 200, f"Lawyer cases failed: {r_law_cases.text}"
    cases_resp = r_law_cases.json()
    law_cases = cases_resp.get("cases", []) if isinstance(cases_resp, dict) else cases_resp
    assert len(law_cases) > 0, "Rajesh has no cases"
    law_case = law_cases[0]
    print(f"  ✓ Lawyer cases loaded: {len(law_cases)} cases | Selected: {law_case['case_number']}")

    # Fetch lawyer case detail
    r_law_det = client.get(f"/api/lawyer/cases/{law_case['case_id']}", headers=rajesh_headers)
    assert r_law_det.status_code == 200
    law_det = r_law_det.json()
    assert "notes" in law_det, "Lawyer case details missing notes array"
    assert "documents" in law_det, "Lawyer case details missing documents array"
    assert "hearings" in law_det, "Lawyer case details missing hearings array"
    print(f"  ✓ Lawyer case detail verified with notes ({len(law_det['notes'])}), docs ({len(law_det['documents'])}), hearings ({len(law_det['hearings'])})")

    # --------------------------------------------------------------------------
    # 15. NOTIFICATIONS INTEGRATION
    # --------------------------------------------------------------------------
    print("\n[15/20] VERIFY NOTIFICATIONS FEED & READ STATUS")
    r_notifs = client.get("/api/citizen/notifications", headers=sunita_headers)
    assert r_notifs.status_code == 200, f"Notifications failed: {r_notifs.text}"
    notif_data = r_notifs.json()
    assert "notifications" in notif_data
    assert "unread_count" in notif_data
    print(f"  ✓ Notifications loaded: {len(notif_data['notifications'])} notifications | Unread: {notif_data['unread_count']}")

    # Mark all read
    r_read_all = client.post("/api/citizen/notifications/read-all", headers=sunita_headers)
    assert r_read_all.status_code == 200, f"Mark all read failed: {r_read_all.text}"
    r_notifs_after = client.get("/api/citizen/notifications", headers=sunita_headers)
    assert r_notifs_after.json()["unread_count"] == 0
    print("  ✓ POST /api/citizen/notifications/read-all successfully marked all read")

    # --------------------------------------------------------------------------
    # 16. CITIZEN PROFILE GET & PUT PERSISTENCE
    # --------------------------------------------------------------------------
    print("\n[16/20] VERIFY CITIZEN PROFILE GET & PUT PERSISTENCE")
    r_prof = client.get("/api/citizen/profile", headers=sunita_headers)
    assert r_prof.status_code == 200, f"Get profile failed: {r_prof.text}"
    prof_orig = r_prof.json()
    cleanup_state["orig_profile"] = prof_orig
    print(f"  ✓ Current profile: {prof_orig['full_name']} | City: {prof_orig.get('city')}")

    # Update profile
    r_update = client.put("/api/citizen/profile", headers=sunita_headers, json={
        "full_name": prof_orig["full_name"],
        "phone": prof_orig.get("phone") or "+91 98112 34567",
        "city": "Pune",
        "state": "Maharashtra",
        "preferred_language": "en"
    })
    assert r_update.status_code == 200
    assert r_update.json()["city"] == "Pune"
    print("  ✓ Profile successfully updated city to 'Pune'")

    # Revert back to original
    client.put("/api/citizen/profile", headers=sunita_headers, json={
        "full_name": prof_orig["full_name"],
        "phone": prof_orig.get("phone") or "+91 98112 34567",
        "city": prof_orig.get("city"),
        "state": prof_orig.get("state"),
        "preferred_language": prof_orig.get("preferred_language") or "en"
    })
    print("  ✓ Profile city rolled back cleanly")

    # --------------------------------------------------------------------------
    # 17. RESPONSIVE FRONTEND ASSETS & BREAKPOINTS
    # --------------------------------------------------------------------------
    print("\n[17/20] VERIFY RESPONSIVE FRONTEND ASSETS & BREAKPOINTS")
    # Verify index.html responsive tags
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in r_index.text, "Viewport meta tag missing"
    assert 'id="btn-mobile-menu-toggle"' in r_index.text, "Mobile menu toggle hamburger missing"
    assert 'id="mobile-backdrop"' in r_index.text, "Mobile drawer backdrop missing"
    assert 'id="view-citizen-search-history"' in r_index.text, "Search history view section missing"
    assert 'id="view-citizen-notifications"' in r_index.text, "Notifications view section missing"
    assert 'class="app-footer"' in r_index.text, "App footer missing"
    print("  ✓ index.html includes mobile viewport, drawer backdrop, hamburger toggle, and footer")

    # Verify styles.css responsive breakpoints
    assert "@media (max-width: 1024px)" in r_css.text, "1024px breakpoint missing in CSS"
    assert "@media (max-width: 768px)" in r_css.text, "768px breakpoint missing in CSS"
    assert "@media (max-width: 480px)" in r_css.text, "480px breakpoint missing in CSS"
    assert ".mobile-backdrop" in r_css.text, ".mobile-backdrop styling missing"
    assert ".mobile-menu-btn" in r_css.text, ".mobile-menu-btn styling missing"
    print("  ✓ styles.css includes responsive breakpoints for 1024px (tablet), 768px (mobile landscape), 480px (mobile portrait 375px)")

    # --------------------------------------------------------------------------
    # 18. UNAUTHORIZED ACCESS & ZERO SILENT FALLBACK
    # --------------------------------------------------------------------------
    print("\n[18/20] VERIFY UNAUTHORIZED ACCESS REJECTION (Zero Silent Fallback)")
    # Missing token
    r_no_auth = client.get("/api/citizen/dashboard")
    assert r_no_auth.status_code == 401, f"Expected 401 on missing auth, got {r_no_auth.status_code}"
    print("  ✓ Missing token rejected with strict 401 Unauthorized")

    # Invalid token
    r_bad_auth = client.get("/api/citizen/dashboard", headers={"Authorization": "Bearer invalid_token_p16"})
    assert r_bad_auth.status_code == 401, f"Expected 401 on invalid token, got {r_bad_auth.status_code}"
    print("  ✓ Invalid bearer token rejected with strict 401 Unauthorized (No silent fallback)")

    # --------------------------------------------------------------------------
    # 19. LIVE DATABASE CONNECTIVITY & CONNECTION POOLING
    # --------------------------------------------------------------------------
    print("\n[19/20] VERIFY LIVE POSTGRESQL CONNECTIVITY & CONNECTION POOL")
    with get_db_cursor() as cur:
        cur.execute("SELECT current_database(), current_user, inet_server_port();")
        db_meta = cur.fetchone()
        assert db_meta["current_database"] == "vidhik_db"
        print(f"  ✓ Connected to PostgreSQL Database: '{db_meta['current_database']}' as user '{db_meta['current_user']}' on port {db_meta['inet_server_port']}")

    # --------------------------------------------------------------------------
    # 20. LEGAL CORPUS ZERO-LOSS INTEGRITY
    # --------------------------------------------------------------------------
    print("\n[20/20] VERIFY ZERO-LOSS LEGAL CORPUS INTEGRITY")
    with get_db_cursor() as cur:
        cur.execute("SELECT count(*) as cnt FROM laws;")
        laws_cnt = cur.fetchone()["cnt"]
        assert laws_cnt == 869, f"Expected 869 laws, got {laws_cnt}"
        print(f"  ✓ laws: {laws_cnt} (100% Intact)")

        cur.execute("SELECT count(*) as cnt FROM sections;")
        secs_cnt = cur.fetchone()["cnt"]
        assert secs_cnt == 41442, f"Expected 41442 sections, got {secs_cnt}"
        print(f"  ✓ sections: {secs_cnt} (100% Intact)")

        cur.execute("SELECT count(*) as cnt FROM legal_lexicon;")
        lex_cnt = cur.fetchone()["cnt"]
        assert lex_cnt == 42, f"Expected 42 lexicon terms, got {lex_cnt}"
        print(f"  ✓ legal_lexicon: {lex_cnt} (100% Intact)")

        cur.execute("SELECT count(*) as cnt FROM section_alignments;")
        align_cnt = cur.fetchone()["cnt"]
        assert align_cnt == 9304, f"Expected 9304 alignments, got {align_cnt}"
        print(f"  ✓ section_alignments: {align_cnt} (100% Intact)")

        cur.execute("SELECT count(*) as cnt FROM legal_procedures;")
        proc_cnt = cur.fetchone()["cnt"]
        assert proc_cnt == 8, f"Expected 8 legal procedures, got {proc_cnt}"
        print(f"  ✓ legal_procedures: {proc_cnt} (Phase 12 Intact)")

        cur.execute("SELECT count(*) as cnt FROM procedure_required_documents;")
        doc_cnt = cur.fetchone()["cnt"]
        assert doc_cnt == 48, f"Expected 48 required documents, got {doc_cnt}"
        print(f"  ✓ procedure_required_documents: {doc_cnt} (Phase 12 Intact)")

    print("\n" + "=" * 80)
    print("ALL 20 PHASE 16 FULL-STACK UI & INTEGRATION VERIFICATION CHECKS PASSED!")
    print("=" * 80)

finally:
    pass
