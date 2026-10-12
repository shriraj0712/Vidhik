"""
Vidhik Platform - eCourts India Case Tracking Comprehensive Test Suite
========================================================================
Validates all 16 requirements of eCourts Case Tracking & Court Reference Integration:
1. Valid CNR normalization & format validation (State, Court, Case, Year components).
2. Invalid, empty, truncated, and malformed CNR rejection with clear messages.
3. Request and response schema serialization & backward compatibility.
4. Citizen can update court reference on their own case (ownership verification).
5. Citizen cannot update another citizen's case (returns 404).
6. Lawyer can update court reference on a case assigned to them.
7. Lawyer cannot update a case assigned to another lawyer (returns 404).
8. Missing or invalid lawyer identity is rejected (returns 403 Forbidden).
9. Nonexistent case ID handled cleanly (returns 404).
10. Optional fields preserve existing database values when omitted.
11. Hearing reminders are synchronized without duplicate creation.
12. Audit entries are recorded in case_updates table for traceability.
13. Database transaction integrity: errors trigger rollback without partial writes.
14. Existing case list and detail endpoints remain backward compatible.
15. Official court URL allowlist security: permits gov.in/nic.in HTTPS, blocks unsafe schemes.
16. Zero-scraping compliance: purely user-assisted verification architecture.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.cnr_validator import (
    normalize_cnr,
    validate_cnr,
    is_valid_cnr,
    parse_cnr_components,
    validate_official_case_url,
    is_valid_official_case_url,
    get_official_ecourts_portal_url,
    OFFICIAL_ECOURTS_PORTAL_URL
)
from app.core.security import create_access_token
from app.schemas.citizen import (
    CitizenCaseCourtReferenceUpdate,
    CitizenCaseResponse,
    CitizenCaseDetailResponse
)
from app.schemas.lawyer import (
    CaseCourtReferenceUpdate,
    CaseSummaryResponse,
    CaseDetailResponse
)
from app.services.citizen_service import CitizenService
from app.services.lawyer_service import LawyerService
from app.database import get_db_cursor

client = TestClient(app)


# ==============================================================================
# AUTHENTICATION HELPERS
# ==============================================================================
def citizen_auth_headers(user_id: int = 201, email: str = "sunita.sharma@example.com") -> dict:
    token = create_access_token(user_id=user_id, email=email, role="user", full_name="Sunita Sharma")
    return {"Authorization": f"Bearer {token}"}


def lawyer_auth_headers(user_id: int = 101, lawyer_id: int = 1, email: str = "rajesh.advocate@vidhik.ai") -> dict:
    token = create_access_token(
        user_id=user_id,
        email=email,
        role="lawyer",
        full_name="Adv. Rajesh Deshmukh",
        lawyer_id=lawyer_id
    )
    return {"Authorization": f"Bearer {token}"}


def lawyer_without_id_headers(user_id: int = 103, email: str = "no_id.advocate@vidhik.ai") -> dict:
    # Token has role="lawyer" but lawyer_id is None
    token = create_access_token(
        user_id=user_id,
        email=email,
        role="lawyer",
        full_name="Adv. Unknown",
        lawyer_id=None
    )
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# TEST 1 & 2: CNR NORMALIZATION, VALIDATION, AND REJECTION
# ==============================================================================
def test_valid_cnr_normalization_and_validation():
    """Test 1: Valid CNR normalization, uppercase transformation, and component extraction."""
    raw_cnr = "mhpu01-004523-2024"
    normalized = normalize_cnr(raw_cnr)
    assert normalized == "MHPU010045232024"
    assert is_valid_cnr(raw_cnr) is True

    is_valid, norm_cnr, err = validate_cnr(raw_cnr)
    assert is_valid is True
    assert norm_cnr == "MHPU010045232024"
    assert err is None

    comps = parse_cnr_components(raw_cnr)
    assert comps["state_code"] == "MH"
    assert comps["court_complex_code"] == "PU01"
    assert comps["case_filing_number"] == "004523"
    assert comps["filing_year"] == 2024

    # Whitespace handling
    assert normalize_cnr("  DLND010012342023  ") == "DLND010012342023"
    assert is_valid_cnr("  DLND010012342023  ") is True


def test_invalid_and_empty_cnr_rejection():
    """Test 2: Rejection of invalid, empty, short, long, or non-alphanumeric CNR inputs."""
    invalid_cases = [
        ("", "cannot be empty"),
        ("   ", "cannot be empty"),
        (None, "cannot be empty"),
        ("MHPU01", "must contain exactly 16 characters"),
        ("MHPU010045232024EXTRA", "must contain exactly 16 characters"),
        ("12PU010045232024", "First 2 characters must be alphabetic state code"),
        ("MHPU01ABCD232024", "Characters 7-12 must be a 6-digit numeric case number"),
        ("MHPU01004523YEAR", "Last 4 characters must be a 4-digit filing year"),
        ("MHPU010045231850", "must be between 1900 and"),
    ]

    for val, expected_err in invalid_cases:
        is_valid, norm, err_msg = validate_cnr(val)
        assert is_valid is False, f"Expected {val} to be invalid"
        assert expected_err.lower() in err_msg.lower(), (
            f"Expected '{expected_err}' in '{err_msg}' for input '{val}'"
        )
        assert is_valid_cnr(val) is False


# ==============================================================================
# TEST 3: SCHEMA COMPATIBILITY & SERIALIZATION
# ==============================================================================
def test_schema_compatibility_and_validation():
    """Test 3: Schema validation, optional fields, and court URL allowlist in schemas."""
    # Citizen update model
    update_data = CitizenCaseCourtReferenceUpdate(
        cnr_number="mhpu01-004523-2024",
        court_source="eCourts Services Portal",
        official_case_url="https://services.ecourts.gov.in/ecourtindia_v6/",
        external_status="Hearing Scheduled",
        external_next_hearing_date=date(2026, 11, 20),
        sync_hearing_reminder=True
    )
    assert update_data.cnr_number == "MHPU010045232024"

    # Lawyer update model
    lawyer_update = CaseCourtReferenceUpdate(
        cnr_number="DLND010012342023",
        external_status="Order Passed"
    )
    assert lawyer_update.cnr_number == "DLND010012342023"
    assert lawyer_update.external_next_hearing_date is None

    # Invalid URL scheme rejected by schema
    with pytest.raises(ValueError, match="Official court URL must use HTTPS"):
        CaseCourtReferenceUpdate(official_case_url="http://insecure.court.gov.in")

    with pytest.raises(ValueError, match="must belong to an authoritative government court domain"):
        CaseCourtReferenceUpdate(official_case_url="https://evil-spoof.com/ecourts")


# ==============================================================================
# TEST 4 & 5: CITIZEN OWNERSHIP AUTHORIZATION
# ==============================================================================
def test_citizen_can_update_own_case():
    """Test 4: Citizen 201 can update court reference on their own case (Case 1)."""
    headers = citizen_auth_headers(user_id=201)
    payload = {
        "cnr_number": "MHPU010045232024",
        "court_source": "District & Sessions Court, Pune",
        "external_status": "Evidence Stage",
        "external_next_hearing_date": "2026-11-15",
        "sync_hearing_reminder": True
    }

    resp = client.patch("/api/citizen/cases/1/court-reference", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["case_id"] == 1
    assert data["cnr_number"] == "MHPU010045232024"
    assert data["court_source"] == "District & Sessions Court, Pune"
    assert data["external_status"] == "Evidence Stage"
    assert data["external_next_hearing_date"] == "2026-11-15"
    assert data["last_verified_at"] is not None
    assert "court_reference" in data
    assert data["court_reference"]["cnr_number"] == "MHPU010045232024"


def test_citizen_cannot_update_another_citizen_case():
    """Test 5: Citizen 201 CANNOT update Case 2 owned by Citizen 202 (returns 404)."""
    headers = citizen_auth_headers(user_id=201)
    payload = {
        "cnr_number": "MHPU010045232024",
        "external_status": "Unauthorized Attempt"
    }

    # Case 2 belongs to user 202
    resp = client.patch("/api/citizen/cases/2/court-reference", json=payload, headers=headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ==============================================================================
# TEST 6, 7 & 8: LAWYER ASSIGNMENT AUTHORIZATION
# ==============================================================================
def test_lawyer_can_update_assigned_case():
    """Test 6: Lawyer 1 can update court reference on Case 1 assigned to Lawyer 1."""
    headers = lawyer_auth_headers(user_id=101, lawyer_id=1)
    payload = {
        "cnr_number": "MHPU010045232024",
        "court_source": "District Court, Pune",
        "external_status": "Arguments Heard",
        "external_next_hearing_date": "2026-11-25",
        "sync_hearing_reminder": True
    }

    resp = client.patch("/api/lawyer/cases/1/court-reference", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["case_id"] == 1
    assert data["cnr_number"] == "MHPU010045232024"
    assert data["external_status"] == "Arguments Heard"
    assert data["external_next_hearing_date"] == "2026-11-25"
    assert data["last_verified_at"] is not None


def test_lawyer_cannot_update_unassigned_case():
    """Test 7: Lawyer 2 CANNOT update Case 1 assigned to Lawyer 1 (returns 404)."""
    headers = lawyer_auth_headers(user_id=102, lawyer_id=2, email="vikram.shinde@vidhik.ai")
    payload = {
        "cnr_number": "MHPU010045232024",
        "external_status": "Unauthorized Change"
    }

    # Case 1 is assigned to Lawyer 1
    resp = client.patch("/api/lawyer/cases/1/court-reference", json=payload, headers=headers)
    assert resp.status_code == 404
    assert "not found or not assigned" in resp.json()["detail"].lower()


def test_missing_lawyer_identity_is_rejected():
    """Test 8: Lawyer request without authenticated lawyer_id is rejected with 403 Forbidden."""
    headers = lawyer_without_id_headers(user_id=103, email="no_id.advocate@vidhik.ai")
    payload = {
        "cnr_number": "MHPU010045232024"
    }

    resp = client.patch("/api/lawyer/cases/1/court-reference", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "lawyer" in resp.json()["detail"].lower()


# ==============================================================================
# TEST 9: NONEXISTENT CASES HANDLED CORRECTLY
# ==============================================================================
def test_nonexistent_cases_handled_correctly():
    """Test 9: Both citizen and lawyer endpoints return 404 for nonexistent case ID."""
    payload = {"cnr_number": "MHPU010045232024"}

    # Citizen 404
    c_resp = client.patch("/api/citizen/cases/999999/court-reference", json=payload, headers=citizen_auth_headers(201))
    assert c_resp.status_code == 404

    # Lawyer 404
    l_resp = client.patch("/api/lawyer/cases/999999/court-reference", json=payload, headers=lawyer_auth_headers(101, 1))
    assert l_resp.status_code == 404


# ==============================================================================
# TEST 10: OPTIONAL FIELDS PRESERVE EXISTING VALUES WHEN OMITTED
# ==============================================================================
def test_optional_fields_preserve_existing_values():
    """Test 10: Updating only external_status preserves previously saved cnr_number."""
    headers = citizen_auth_headers(user_id=201)

    # 1. First update setting both CNR and external status
    initial_payload = {
        "cnr_number": "MHPU010045232024",
        "external_status": "Pre-Trial",
        "external_next_hearing_date": "2026-12-01"
    }
    resp1 = client.patch("/api/citizen/cases/1/court-reference", json=initial_payload, headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["cnr_number"] == "MHPU010045232024"

    # 2. Second update omitting cnr_number and external_next_hearing_date
    partial_payload = {
        "external_status": "Framing of Charges"
    }
    resp2 = client.patch("/api/citizen/cases/1/court-reference", json=partial_payload, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Preserved values
    assert data2["cnr_number"] == "MHPU010045232024"
    assert data2["external_next_hearing_date"] == "2026-12-01"
    # Updated value
    assert data2["external_status"] == "Framing of Charges"


# ==============================================================================
# TEST 11: HEARING REMINDERS NOT DUPLICATED
# ==============================================================================
def test_hearing_reminders_not_duplicated():
    """Test 11: Repeated sync requests for the same case and hearing date do not create duplicate reminders."""
    headers = citizen_auth_headers(user_id=201)
    test_date = "2026-12-15"

    payload = {
        "external_next_hearing_date": test_date,
        "sync_hearing_reminder": True
    }

    # First update
    resp1 = client.patch("/api/citizen/cases/1/court-reference", json=payload, headers=headers)
    assert resp1.status_code == 200

    # Second identical update
    resp2 = client.patch("/api/citizen/cases/1/court-reference", json=payload, headers=headers)
    assert resp2.status_code == 200

    # Inspect reminders in database
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM reminders WHERE case_id = 1 AND reminder_date = %s;",
            (test_date,)
        )
        row = cur.fetchone()
        assert row["cnt"] == 1, f"Expected exactly 1 reminder for {test_date}, found {row['cnt']}"


# ==============================================================================
# TEST 12: AUDIT ENTRIES CREATED IN case_updates
# ==============================================================================
def test_audit_entries_created_appropriately():
    """Test 12: Audit records are properly logged in case_updates table for both citizen and lawyer."""
    # 1. Citizen audit
    c_resp = client.patch(
        "/api/citizen/cases/1/court-reference",
        json={"external_status": "Citizen Verified Stage"},
        headers=citizen_auth_headers(201)
    )
    assert c_resp.status_code == 200

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT update_title, update_description, updated_by
            FROM case_updates
            WHERE case_id = 1 AND updated_by = 'Citizen'
            ORDER BY update_id DESC LIMIT 1;
            """
        )
        c_audit = cur.fetchone()
        assert c_audit is not None
        assert "Court Reference" in c_audit["update_title"]
        assert "Citizen Verified Stage" in c_audit["update_description"]

    # 2. Lawyer audit
    l_resp = client.patch(
        "/api/lawyer/cases/1/court-reference",
        json={"external_status": "Lawyer Verified Stage"},
        headers=lawyer_auth_headers(101, 1)
    )
    assert l_resp.status_code == 200

    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT update_title, update_description, updated_by
            FROM case_updates
            WHERE case_id = 1 AND updated_by = 'Lawyer'
            ORDER BY update_id DESC LIMIT 1;
            """
        )
        l_audit = cur.fetchone()
        assert l_audit is not None
        assert "Court Reference" in l_audit["update_title"]
        assert "Lawyer Verified Stage" in l_audit["update_description"]


# ==============================================================================
# TEST 13: DATABASE TRANSACTION INTEGRITY & ROLLBACK
# ==============================================================================
def test_database_failure_rollback():
    """Test 13: Database exceptions during update trigger rollback without partial changes."""
    mock_db = MagicMock()
    mock_db.fetchone.return_value = {"case_id": 1, "case_title": "Test Case"}
    # The SELECT succeeds, and the subsequent UPDATE raises database exception
    mock_db.execute.side_effect = [None, Exception("Simulated mid-transaction database crash")]
    mock_db.connection = MagicMock()
    update_model = CitizenCaseCourtReferenceUpdate(cnr_number="MHPU010045232024")

    with pytest.raises(Exception):
        CitizenService.update_court_reference(mock_db, 201, 1, payload=update_model)

    mock_db.connection.rollback.assert_called_once()


# ==============================================================================
# TEST 14: EXISTING CASE LIST AND DETAIL BACKWARD COMPATIBILITY
# ==============================================================================
def test_existing_case_list_and_detail_backward_compatibility():
    """Test 14: Case list and detail responses contain court_reference fields without breaking existing structure."""
    headers_c = citizen_auth_headers(201)

    # Citizen Case List
    c_list_resp = client.get("/api/citizen/cases", headers=headers_c)
    assert c_list_resp.status_code == 200
    cases_c = c_list_resp.json()
    assert isinstance(cases_c, list)
    if cases_c:
        first = cases_c[0]
        assert "case_id" in first
        assert "title" in first
        assert "cnr_number" in first
        assert "court_reference" in first

    # Citizen Case Detail
    c_detail_resp = client.get("/api/citizen/cases/1", headers=headers_c)
    assert c_detail_resp.status_code == 200
    detail_c = c_detail_resp.json()
    assert detail_c["case_id"] == 1
    assert "documents" in detail_c
    assert "hearings" in detail_c
    assert "updates" in detail_c
    assert "legal_sections" in detail_c
    assert "court_reference" in detail_c

    # Lawyer Case List
    headers_l = lawyer_auth_headers(101, 1)
    l_list_resp = client.get("/api/lawyer/cases", headers=headers_l)
    assert l_list_resp.status_code == 200
    cases_data = l_list_resp.json()
    assert "cases" in cases_data
    cases_l = cases_data["cases"]
    assert isinstance(cases_l, list)
    if cases_l:
        first_l = cases_l[0]
        assert "case_id" in first_l
        assert "cnr_number" in first_l
        assert "court_reference" in first_l

    # Lawyer Case Detail
    l_detail_resp = client.get("/api/lawyer/cases/1", headers=headers_l)
    assert l_detail_resp.status_code == 200
    detail_l = l_detail_resp.json()
    assert detail_l["case_id"] == 1
    assert "documents" in detail_l
    assert "notes" in detail_l
    assert "court_reference" in detail_l


# ==============================================================================
# TEST 15: OFFICIAL COURT URL ALLOWLIST SECURITY
# ==============================================================================
def test_official_court_url_allowlist_security():
    """Test 15: Validation of authoritative court URLs and rejection of spoofed domains."""
    valid_urls = [
        "https://services.ecourts.gov.in/ecourtindia_v6/",
        "https://delhihighcourt.nic.in/case_status.asp",
        "https://bombayhighcourt.nic.in/case_query.php",
        "https://ecourts.gov.in/index.html",
        "https://districts.ecourts.gov.in/pune"
    ]
    for url in valid_urls:
        assert is_valid_official_case_url(url) is True

    invalid_urls = [
        "http://services.ecourts.gov.in/ecourtindia_v6/",  # Insecure HTTP
        "https://evil-ecourts.com/portal",                  # Untrusted domain
        "javascript:alert('xss')",                         # Script scheme
        "ftp://services.ecourts.gov.in",                   # Non-HTTP scheme
        "https://localhost/case",  # Localhost is not an official court domain
        "https://ecourts.gov.in@evil.com/case",  # Deceptive hostname
        "https://user:pass@ecourts.gov.in/case",  # Embedded credentials
        "https://gov.in.attacker.com",                     # Subdomain attack
        "",                                                # Empty
        None                                               # None
    ]
    for url in invalid_urls:
        assert is_valid_official_case_url(url) is False


# ==============================================================================
# TEST 16: ZERO-SCRAPING & DUAL-TRACK COMPLIANCE
# ==============================================================================
def test_zero_scraping_compliance():
    """Test 16: Confirms architecture relies strictly on user-assisted verification without unauthorized automation."""
    # Official portal URL constant check
    assert OFFICIAL_ECOURTS_PORTAL_URL == "https://services.ecourts.gov.in/ecourtindia_v6/"
    assert get_official_ecourts_portal_url() == OFFICIAL_ECOURTS_PORTAL_URL

    # Ensure no scraper packages or automated browser libraries are referenced in cnr_validator
    import app.core.cnr_validator as validator_module
    module_source = open(validator_module.__file__, "r", encoding="utf-8").read()
    assert "selenium" not in module_source.lower()
    assert "playwright" not in module_source.lower()
    assert "pyppeteer" not in module_source.lower()
    assert "captcha" not in module_source.lower()
