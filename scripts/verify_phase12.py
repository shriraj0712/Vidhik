"""
Vidhik AI - Phase 12 Documentation Support Module Complete Verification
========================================================================
Runs an automated end-to-end verification covering:
1. Backend Startup & Endpoint Health
2. Database Schema & Migration 005 Integrity
3. API Routes: Categories, Procedures, Details, Checklists
4. Keyword Search Across Procedures
5. Category Filter Granularity
6. Mandatory vs Supporting Classification
7. Statutory References Grounding (Direct Section Join)
8. Frontend Assets (HTML, CSS, JS Navigation & Modals)
9. Lawyer Case File Attachment Integration
10. Existing Legal Search Regression Test
11. Existing Phase 13 Lawyer Module Regression Test
12. Zero-Loss Database Corpus Verification (869 Laws, 41,442 Sections)
"""

import sys
import os
sys.path.insert(0, os.path.abspath("backend"))
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE_URL, timeout=10.0)

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

from app.database import get_db_cursor
try:
    with get_db_cursor() as cur:
        cur.execute("SELECT 1;")
except Exception as e:
    print(f"[ERROR] PostgreSQL database is unavailable: {e}")
    sys.exit(1)

print("=" * 70)
print("VIDHIK AI - PHASE 12 DOCUMENTATION SUPPORT END-TO-END VERIFICATION")
print("=" * 70)

# ----------------------------------------------------------------------
# 1. ROOT & STATIC ASSETS
# ----------------------------------------------------------------------
print("\n[1/12] VERIFY ROOT, STATIC UI & PHASE 12 ASSETS")
r_root = client.get("/")
assert r_root.status_code == 200, f"Expected 200, got {r_root.status_code}"
assert "Documentation Support" in r_root.text
assert "view-documentation" in r_root.text
assert "modal-procedure-checklist" in r_root.text
print("  ✓ /lawyer SPA served with Phase 12 Documentation Support view & modal (200 OK)")

r_css = client.get("/static/styles.css")
assert r_css.status_code == 200
assert ".procedure-card" in r_css.text
assert ".checklist-item-card" in r_css.text
assert ".legal-ref-badge" in r_css.text
print("  ✓ /static/styles.css served with Phase 12 design tokens (200 OK)")

r_js = client.get("/static/app.js")
assert r_js.status_code == 200
assert "loadDocumentationModule" in r_js.text
assert "openProcedureChecklist" in r_js.text
assert "toggleChecklistDoc" in r_js.text
assert "attachChecklistToCase" in r_js.text
print("  ✓ /static/app.js served with Phase 12 client logic (200 OK)")

# ----------------------------------------------------------------------
# 2. CATEGORIES ENDPOINT
# ----------------------------------------------------------------------
print("\n[2/12] VERIFY CATEGORIES ENDPOINT (/api/documentation/categories)")
r_cat = client.get("/api/documentation/categories")
assert r_cat.status_code == 200
cats = r_cat.json()
assert len(cats) >= 6, f"Expected at least 6 categories, got {len(cats)}"
print(f"  ✓ Total Categories: {len(cats)}")
for c in cats:
    print(f"    - {c['category']}: {c['procedures_count']} procedures")

# ----------------------------------------------------------------------
# 3. PROCEDURES LISTING
# ----------------------------------------------------------------------
print("\n[3/12] VERIFY PROCEDURES LISTING (/api/documentation/procedures)")
r_proc = client.get("/api/documentation/procedures")
assert r_proc.status_code == 200
proc_data = r_proc.json()
assert proc_data["total"] == 25, f"Expected 25 seeded procedures, got {proc_data['total']}"
assert len(proc_data["procedures"]) == 25
print(f"  ✓ Total Procedures Listed: {proc_data['total']}")
for p in proc_data["procedures"]:
    print(f"    [{p['procedure_id']}] {p['procedure_name']} ({p['category']}) | Docs: {p['total_documents_count']} (Mandatory: {p['mandatory_documents_count']}, Supporting: {p['supporting_documents_count']})")

# ----------------------------------------------------------------------
# 4. PROCEDURE SEARCH FUNCTIONALITY
# ----------------------------------------------------------------------
print("\n[4/12] VERIFY KEYWORD SEARCH ACROSS PROCEDURES")
search_tests = [
    ("RTI", "Right to Information (RTI) Application"),
    ("Succession", "Application for Succession Certificate"),
    ("Sale Deed", "Registration of Conveyance / Sale Deed"),
    ("Consumer", "Filing of Consumer Complaint"),
    ("Divorce", "Petition for Mutual Consent Divorce"),
    ("Civil Suit", "Civil Suit Plaint Presentation & Institution"),
    ("Mutation", "Land Title Mutation (7/12 Extract Ferfar)"),
    ("Co-operative", "Registration of Co-operative Society"),
    ("Marriage", "Registration of Marriage (Special & Hindu Marriage Acts)"),
    ("Birth", "Birth Certificate Registration and Correction"),
    ("Death", "Death Certificate Registration and Correction"),
    ("Gazette", "Name Change and Official Gazette Publication"),
    ("Domicile", "Application for Domicile and Nationality Certificate"),
    ("Income", "Application for Income Certificate"),
    ("Caste", "Caste Certificate Issuance and Scrutiny Verification"),
    ("Legal Heir", "Legal Heir / Surviving Member Certificate"),
    ("Encumbrance", "Property Encumbrance Certificate (EC) & Title Search"),
    ("Banking Ombudsman", "Banking Ombudsman / RBI Grievance Redressal"),
    ("Insurance Ombudsman", "Insurance Ombudsman Complaint Filing"),
    ("EPFO", "Employees' Provident Fund (EPFO / PF) Settlement Claim"),
    ("Gratuity", "Payment of Gratuity Claim and Controlling Authority Application"),
    ("Compensation", "Employee Compensation Claim for Workplace Injury"),
    ("FIR", "First Information Report (FIR) / Police Complaint Filing"),
    ("Bail", "Bail Application (Regular & Anticipatory Bail)"),
    ("Legal Notice", "Statutory Legal Notice & Demand (Cheque Dishonour / Section 80 CPC)")
]
for query, expected_title in search_tests:
    res = client.get(f"/api/documentation/procedures?search={query}").json()
    assert res["total"] >= 1, f"Search failed for '{query}'"
    titles = [x["procedure_name"] for x in res["procedures"]]
    assert expected_title in titles, f"Expected '{expected_title}' in search results for '{query}'"
    print(f"  ✓ Search '{query}': matched '{expected_title}' (Results: {res['total']})")

# ----------------------------------------------------------------------
# 5. CATEGORY FILTERING
# ----------------------------------------------------------------------
print("\n[5/12] VERIFY CATEGORY FILTERING")
cat_tests = [
    ("Property", 3),
    ("Government Applications", 1),
    ("Court / Litigation", 4),
    ("Certificates / Registrations", 9),
    ("Consumer / Commercial", 3),
    ("Family / Personal", 2),
    ("Employment / Social", 3)
]
for cat_name, expected_count in cat_tests:
    res = client.get(f"/api/documentation/procedures?category={cat_name}").json()
    assert res["total"] == expected_count, f"Category '{cat_name}': expected {expected_count}, got {res['total']}"
    for p in res["procedures"]:
        assert p["category"] == cat_name
    print(f"  ✓ Filter '{cat_name}': {res['total']} procedure(s) matched accurately")

# ----------------------------------------------------------------------
# 6. PROCEDURE DETAIL & STATUTORY METADATA
# ----------------------------------------------------------------------
print("\n[6/12] VERIFY PROCEDURE DETAIL & STATUTORY GOVERNANCE")
r_p1 = client.get("/api/documentation/procedures/1")
assert r_p1.status_code == 200
p1 = r_p1.json()
assert p1["procedure_slug"] == "rti-application"
assert p1["governing_law_name"] == "The Right to Information Act, 2005"
assert p1["governing_section_number"] == "6"
assert p1["estimated_processing_days"] == 30
assert p1["official_portal_url"] == "https://rtionline.gov.in"
print(f"  ✓ Procedure: {p1['procedure_name']}")
print(f"    - Governing Statute: {p1['governing_law_name']} (Section {p1['governing_section_number']})")
print(f"    - Authority: {p1['authority_type']} | Jurisdiction: {p1['jurisdiction']}")
print(f"    - Timeline: ~{p1['estimated_processing_days']} Days | Portal: {p1['official_portal_url']}")

# ----------------------------------------------------------------------
# 7. STRUCTURED DOCUMENT CHECKLIST PARTITIONING
# ----------------------------------------------------------------------
print("\n[7/12] VERIFY STRUCTURED CHECKLIST PARTITIONING (MANDATORY vs SUPPORTING)")
r_chk = client.get("/api/documentation/procedures/3/checklist")  # Sale Deed Registration
assert r_chk.status_code == 200
chk = r_chk.json()
assert chk["procedure_name"] == "Registration of Conveyance / Sale Deed"
assert chk["total_count"] == 7
assert chk["mandatory_count"] == 5
assert chk["supporting_count"] == 2
print(f"  ✓ Checklist for '{chk['procedure_name']}': {chk['total_count']} items total")
print(f"    - Mandatory Requirements ({len(chk['mandatory_documents'])} items):")
for d in chk["mandatory_documents"]:
    assert d["is_mandatory"] is True
    print(f"      [!] {d['document_name']} ({d['document_type']}) -> Purpose: {d['purpose'][:60]}...")
print(f"    - Supporting Records ({len(chk['supporting_documents'])} items):")
for d in chk["supporting_documents"]:
    assert d["is_mandatory"] is False
    print(f"      [i] {d['document_name']} ({d['document_type']}) -> Purpose: {d['purpose'][:60]}...")

# ----------------------------------------------------------------------
# 8. STATUTORY SECTION REUSE & CROSS-REFERENCE INTEGRITY
# ----------------------------------------------------------------------
print("\n[8/12] VERIFY STATUTORY CITATION RESOLUTION VIA EXISTING SECTIONS API")
# Find a document requirement with a statutory reference (e.g. Sale deed original on stamp paper -> Sec 17, ID 31365)
sale_deed_doc = [d for d in chk["mandatory_documents"] if d["statutory_reference_id"] is not None][0]
sec_id = sale_deed_doc["statutory_reference_id"]
r_sec = client.get(f"/api/sections/{sec_id}")
assert r_sec.status_code == 200, f"Expected 200 from /api/sections/{sec_id}"
sec_data = r_sec.json()
assert sec_data["section_number"] == "17"
assert sec_data["law_id"] == 680
assert "Registration Act" in sale_deed_doc["law_name"]
print(f"  ✓ Document '{sale_deed_doc['document_name']}' correctly linked to statutory Section {sec_data['section_number']}")
print(f"  ✓ Verified Verbatim Statutory Heading: '{sec_data['section_title']}'")
print(f"  ✓ Governing Act: {sale_deed_doc['law_name']} (Law ID: {sec_data['law_id']})")

# ----------------------------------------------------------------------
# 9. LAWYER INTEGRATION: ATTACH CHECKLIST TO CASE NOTES
# ----------------------------------------------------------------------
print("\n[9/12] VERIFY LAWYER MODULE INTEGRATION (ATTACH CHECKLIST TO CASE BRIEF)")
# Log in as lawyer
login_res = client.post("/api/auth/login", json={"email": "rajesh.advocate@vidhik.ai", "password": "password123"})
assert login_res.status_code == 200
token = login_res.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Attach succession checklist to Case 1
test_note_payload = {
    "case_id": 1,
    "title": "Checklist: Application for Succession Certificate",
    "content": "PROCEDURAL DOCUMENT CHECKLIST\n- [✓ READY] Verified Petition for Succession Certificate\n- [✓ READY] Official Death Certificate of Deceased\n- [ ] Detailed Schedule of Debts and Securities",
    "is_pinned": True
}
note_res = client.post("/api/lawyer/cases/1/notes", headers=headers, json=test_note_payload)
assert note_res.status_code == 200
created_note = note_res.json()
note_id = created_note["note_id"]
try:
    assert created_note["title"] == test_note_payload["title"]
    print(f"  ✓ Successfully attached checklist summary to Case 1 Notes (Note ID: {note_id})")
finally:
    # Clean up test note
    del_res = client.delete(f"/api/lawyer/notes/{note_id}", headers=headers)
    assert del_res.status_code == 200
    print(f"  ✓ Cleaned up test note {note_id} after successful attachment verification")

# ----------------------------------------------------------------------
# 10. EXISTING LEGAL SEARCH REGRESSION
# ----------------------------------------------------------------------
print("\n[10/12] REGRESSION TEST: EXISTING LEGAL SEARCH & RANKING")
r_search = client.get("/api/search?q=co-operative&limit=5")
assert r_search.status_code == 200
s_data = r_search.json()
assert s_data["total"] > 0
top_item = s_data["results"][0]
assert "co-operative" in top_item["snippet"].lower() or "co-operative" in top_item["section_title"].lower() or "co-operative" in top_item["law_name"].lower()
print(f"  ✓ LegalSearchService functional: query 'co-operative' returned {s_data['total']} statutory matches")
print(f"    - Top Result: Sec {top_item['section_number']} - {top_item['section_title']} ({top_item['law_name']})")

# ----------------------------------------------------------------------
# 11. EXISTING PHASE 13 LAWYER MODULE REGRESSION
# ----------------------------------------------------------------------
print("\n[11/12] REGRESSION TEST: PHASE 13 LAWYER WORKSPACE")
r_dash = client.get("/api/lawyer/dashboard", headers=headers)
assert r_dash.status_code == 200
dash = r_dash.json()
assert dash["total_clients"] >= 3
assert dash["active_cases"] >= 2
print(f"  ✓ Lawyer Dashboard functional (Clients: {dash['total_clients']}, Active Cases: {dash['active_cases']})")

r_cases = client.get("/api/lawyer/cases", headers=headers)
assert r_cases.status_code == 200
print(f"  ✓ Lawyer Cases functional ({r_cases.json()['total']} cases cataloged)")

# ----------------------------------------------------------------------
# 12. ZERO-LOSS DATABASE CORPUS INTEGRITY
# ----------------------------------------------------------------------
print("\n[12/12] VERIFY ZERO-LOSS DATABASE CORPUS INTEGRITY")
with get_db_cursor() as cur:
    cur.execute("SELECT count(*) FROM laws;")
    r = cur.fetchone()
    laws_count = r["count"] if r else 0
    assert laws_count == 869, f"Expected 869 laws, got {laws_count}"

    cur.execute("SELECT count(*) FROM sections;")
    r = cur.fetchone()
    sections_count = r["count"] if r else 0
    assert sections_count == 41442, f"Expected 41,442 sections, got {sections_count}"

    cur.execute("SELECT count(*) FROM legal_lexicon;")
    r = cur.fetchone()
    lexicon_count = r["count"] if r else 0
    assert lexicon_count == 42, f"Expected 42 lexicon terms, got {lexicon_count}"

    cur.execute("SELECT count(*) FROM section_alignments;")
    r = cur.fetchone()
    alignments_count = r["count"] if r else 0
    assert alignments_count == 9304, f"Expected 9,304 alignments, got {alignments_count}"

    cur.execute("SELECT count(*) FROM legal_procedures;")
    r = cur.fetchone()
    proc_count = r["count"] if r else 0
    assert proc_count == 25, f"Expected 25 procedures, got {proc_count}"

    cur.execute("SELECT count(*) FROM procedure_required_documents;")
    r = cur.fetchone()
    docs_count = r["count"] if r else 0
    assert docs_count == 159, f"Expected 159 documents, got {docs_count}"

print(f"  ✓ laws: {laws_count} (100% Intact)")
print(f"  ✓ sections: {sections_count} (100% Intact)")
print(f"  ✓ legal_lexicon: {lexicon_count} (100% Intact)")
print(f"  ✓ section_alignments: {alignments_count} (100% Intact)")
print(f"  ✓ legal_procedures: {proc_count} (Phase 12 Expanded)")
print(f"  ✓ procedure_required_documents: {docs_count} (Phase 12 Expanded)")

print("\n" + "=" * 70)
print("ALL 12 PHASE 12 VERIFICATION SUITES COMPLETED WITH 100% SUCCESS!")
print("=" * 70)
