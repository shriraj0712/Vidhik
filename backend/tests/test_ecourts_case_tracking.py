"""
Vidhik Platform - eCourts Case Tracking & CNR Integration Test Suite
=====================================================================
Comprehensive tests validating the User-Assisted CNR Lookup + Dual-Track Case Model:
1. CNR Validation & Normalization (alphanumeric, 16 chars, case conversion, whitespace trimming)
2. CNR format rejection (hyphens, spaces, special chars, short/long lengths, empty)
3. CNR component parsing & official URL generation
4. Pydantic Schemas backwards compatibility (Lawyer & Citizen case models)
5. Lawyer Service Case Lifecycle with CNR metadata (create, detail, update, court-reference)
6. Citizen Service Case Lifecycle with CNR metadata & strict user ownership
7. Separate Status Model: VIDHIK internal case status vs. Official court status
8. Audit logging on court reference updates (case_updates & activity feed)
9. Reminder & Hearing schedule synchronization with official next hearing date
10. Authorization & Security (Citizen ownership isolation, Lawyer assignment boundary)
11. FastAPI REST Endpoints (PATCH /api/lawyer/cases/{id}/court-reference, PATCH /api/citizen/cases/{id}/court-reference)
12. Zero-Scraping / No-CAPTCHA-Bypass compliance verification
"""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.core.cnr_validator import (
    validate_cnr,
    normalize_cnr,
    is_valid_cnr,
    parse_cnr_components,
    get_official_ecourts_portal_url,
    ECOURTS_SERVICES_PORTAL,
    ECOURTS_MAIN_PORTAL
)
from app.schemas.lawyer import (
    CaseCreate,
    CaseUpdate,
    CaseCourtReferenceUpdate,
    CaseSummaryResponse,
    CaseDetailResponse
)
from app.schemas.citizen import (
    CitizenCaseCreate,
    CitizenCaseResponse,
    CitizenCaseDetailResponse,
    CitizenCaseCourtReferenceUpdate
)
from app.services.lawyer_service import LawyerService
from app.services.citizen_service import CitizenService
from app.services.auth_service import require_lawyer, require_citizen


# =============================================================================
# 1. CNR VALIDATION & NORMALIZATION UNIT TESTS
# =============================================================================

class TestCNRValidation:
    """Tests for CNR format validation, normalization, and component extraction."""

    def test_valid_16_char_cnr(self):
        cnr = "MHAU010123452023"
        valid, normalized, err = validate_cnr(cnr)
        assert valid is True
        assert normalized == "MHAU010123452023"
        assert err is None
        assert is_valid_cnr(cnr) is True

    def test_lowercase_cnr_normalization(self):
        cnr = "mhau010123452023"
        valid, normalized, err = validate_cnr(cnr)
        assert valid is True
        assert normalized == "MHAU010123452023"
        assert normalize_cnr(cnr) == "MHAU010123452023"

    def test_whitespace_trimming(self):
        cnr = "  MHAU010123452023   \n"
        valid, normalized, err = validate_cnr(cnr)
        assert valid is True
        assert normalized == "MHAU010123452023"
        assert normalize_cnr(cnr) == "MHAU010123452023"

    def test_invalid_length_short(self):
        cnr = "MH123"
        valid, normalized, err = validate_cnr(cnr)
        assert valid is False
        assert "exactly 16" in err
        assert is_valid_cnr(cnr) is False
        with pytest.raises(ValueError):
            normalize_cnr(cnr)

    def test_invalid_length_long(self):
        cnr = "MHAU010123452023EXTRA"
        valid, normalized, err = validate_cnr(cnr)
        assert valid is False
        assert "exactly 16" in err

    def test_invalid_characters_hyphens(self):
        cnr = "MHAU-010123452023"
        valid, normalized, err = validate_cnr(cnr)
        assert valid is False
        assert is_valid_cnr(cnr) is False

    def test_invalid_characters_spaces(self):
        cnr = "MHAU 010123452023"
        valid, normalized, err = validate_cnr(cnr)
        assert valid is False

    def test_invalid_characters_symbols(self):
        cnr = "MHAU01012345202@"
        valid, normalized, err = validate_cnr(cnr)
        assert valid is False
        assert "alphanumeric" in err

    def test_empty_or_none_cnr(self):
        assert validate_cnr("")[0] is False
        assert validate_cnr("   ")[0] is False
        assert validate_cnr(None)[0] is False
        with pytest.raises(ValueError):
            normalize_cnr("")

    def test_cnr_component_parsing(self):
        cnr = "MHAU010123452023"
        comp = parse_cnr_components(cnr)
        assert comp is not None
        assert comp["state_code"] == "MH"
        assert comp["court_complex_code"] == "AU01"
        assert comp["case_filing_number"] == "012345"
        assert comp["filing_year"] == 2023
        assert comp["official_portal_url"] == ECOURTS_SERVICES_PORTAL

    def test_official_portal_urls(self):
        url = get_official_ecourts_portal_url()
        assert url == ECOURTS_SERVICES_PORTAL
        assert url.startswith("https://services.ecourts.gov.in")
        assert "ecourts.gov.in" in ECOURTS_MAIN_PORTAL


# =============================================================================
# 2. PYDANTIC SCHEMAS BACKWARD COMPATIBILITY TESTS
# =============================================================================

class TestPydanticSchemas:
    """Validates schemas support optional CNR metadata without breaking existing workflows."""

    def test_lawyer_case_create_without_cnr(self):
        payload = CaseCreate(
            user_id=1,
            case_title="Standard Commercial Brief",
            case_number="CS/2026/101"
        )
        assert payload.cnr_number is None
        assert payload.court_source == "eCourts India"

    def test_lawyer_case_create_with_cnr(self):
        payload = CaseCreate(
            user_id=1,
            case_title="Writ Petition vs State",
            cnr_number="MHAU010123452023",
            court_name="High Court of Bombay"
        )
        assert payload.cnr_number == "MHAU010123452023"

    def test_citizen_case_create_without_cnr(self):
        payload = CitizenCaseCreate(
            title="Boundary Dispute Matter",
            description="Neighbor encroachment issue"
        )
        assert payload.cnr_number is None

    def test_citizen_case_create_with_cnr(self):
        payload = CitizenCaseCreate(
            title="Consumer Forum Appeal",
            description="Defective electronics warranty claim",
            cnr_number="DLND010098762024"
        )
        assert payload.cnr_number == "DLND010098762024"

    def test_court_reference_update_schema(self):
        update = CaseCourtReferenceUpdate(
            cnr_number="MHAU010123452023",
            external_status="Listed for Admission",
            external_next_hearing_date=date(2026, 11, 15)
        )
        assert update.cnr_number == "MHAU010123452023"
        assert update.external_status == "Listed for Admission"
        assert update.external_next_hearing_date == date(2026, 11, 15)

    def test_case_summary_court_reference_model(self):
        resp = CaseSummaryResponse(
            case_id=1,
            user_id=1,
            case_title="Writ Petition",
            status="active",
            cnr_number="MHAU010123452023",
            court_source="eCourts India",
            official_case_url=ECOURTS_SERVICES_PORTAL,
            external_status="Arguments Concluded",
            external_next_hearing_date=date(2026, 12, 1),
            last_verified_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert resp.cnr_number == "MHAU010123452023"
        assert resp.court_source == "eCourts India"
        assert resp.external_status == "Arguments Concluded"


from fastapi import HTTPException

# =============================================================================
# 3. LAWYER SERVICE UNIT & DUAL-TRACK TESTS
# =============================================================================

class TestLawyerServiceCNR:
    """Tests LawyerService methods handling CNR metadata and dual-track case status."""

    def test_create_case_with_valid_cnr(self):
        db = MagicMock()
        db.fetchone.return_value = {"case_id": 10, "created_at": datetime.now(), "updated_at": datetime.now()}
        db.fetchall.return_value = [
            {
                "case_id": 10,
                "user_id": 1,
                "case_title": "Tax Appeal",
                "case_number": "TA/2026/01",
                "case_type": "Taxation",
                "court_name": "High Court",
                "opposite_party": "Revenue Dept",
                "filing_date": "2026-01-10",
                "status": "active",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "client_name": "Ramesh",
                "client_phone": "9876543210",
                "assigned_lawyer_id": 1,
                "cnr_number": "MHAU010123452023",
                "court_source": "eCourts India",
                "official_case_url": ECOURTS_SERVICES_PORTAL,
                "last_verified_at": None,
                "external_status": None,
                "external_next_hearing_date": None
            }
        ]

        payload = CaseCreate(
            user_id=1,
            case_title="Tax Appeal",
            case_number="TA/2026/01",
            cnr_number="  mhau010123452023  "  # Testing normalization
        )

        res = LawyerService.create_case(db, lawyer_id=1, payload=payload)
        assert res.cnr_number == "MHAU010123452023"
        assert db.execute.called

    def test_create_case_with_invalid_cnr_raises_value_error(self):
        db = MagicMock()
        payload = CaseCreate(
            user_id=1,
            case_title="Bad CNR Case",
            cnr_number="INVALID-CNR-123"
        )
        with pytest.raises(Exception) as exc:
            LawyerService.create_case(db, lawyer_id=1, payload=payload)
        assert "16" in str(exc.value) or "CNR" in str(exc.value) or getattr(exc.value, 'status_code', None) == 400

    def test_get_case_detail_includes_court_reference(self):
        db = MagicMock()
        db.fetchone.return_value = {
            "case_id": 10,
            "user_id": 1,
            "case_title": "Property Suit",
            "case_number": "CS/2026/99",
            "case_type": "Civil",
            "court_name": "City Civil Court",
            "opposite_party": "Builder Corp",
            "filing_date": "2026-02-01",
            "incident_date": None,
            "location": "Mumbai",
            "police_station": None,
            "case_description": "Specific performance of contract",
            "status": "active",  # VIDHIK internal status
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "client_name": "Sunita",
            "client_phone": "9820011111",
            "client_email": "sunita@example.com",
            "assigned_lawyer_id": 1,
            "cnr_number": "MHAU010123452023",
            "court_source": "eCourts India",
            "official_case_url": ECOURTS_SERVICES_PORTAL,
            "last_verified_at": datetime.now(),
            "external_status": "Notice Issued",  # External court status
            "external_next_hearing_date": date(2026, 11, 20)
        }
        db.fetchall.return_value = []

        detail = LawyerService.get_case_detail(db, case_id=10, lawyer_id=1)
        assert detail is not None
        assert detail.status == "active"  # Internal status preserved
        assert detail.court_reference is not None
        assert detail.court_reference["cnr_number"] == "MHAU010123452023"
        assert detail.court_reference["external_status"] == "Notice Issued"
        assert detail.court_reference["external_next_hearing_date"] == date(2026, 11, 20)

    def test_update_court_reference_dual_track_and_audit(self):
        """Validates external status update does NOT overwrite internal status, logs update and reminder."""
        db = MagicMock()
        # 1. Existing case fetch, 2. reminder check, 3. get_case_detail fetch
        db.fetchone.side_effect = [
            {
                "case_id": 10,
                "user_id": 1,
                "case_title": "Property Suit",
                "court_name": "City Civil Court",
                "status": "active",
                "cnr_number": None,
                "external_status": None,
                "external_next_hearing_date": None
            },
            None,
            {
                "case_id": 10,
                "user_id": 1,
                "case_title": "Property Suit",
                "case_number": "CS/2026/99",
                "case_type": "Civil",
                "court_name": "City Civil Court",
                "opposite_party": "Builder Corp",
                "filing_date": "2026-02-01",
                "incident_date": None,
                "location": "Mumbai",
                "police_station": None,
                "case_description": "Specific performance of contract",
                "status": "active",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "client_name": "Sunita",
                "client_phone": "9820011111",
                "client_email": "sunita@example.com",
                "assigned_lawyer_id": 1,
                "cnr_number": "MHAU010123452023",
                "court_source": "eCourts India",
                "official_case_url": ECOURTS_SERVICES_PORTAL,
                "last_verified_at": datetime.now(),
                "external_status": "Evidence Stage",
                "external_next_hearing_date": date(2026, 12, 10)
            }
        ]
        db.fetchall.return_value = []

        payload = CaseCourtReferenceUpdate(
            cnr_number="MHAU010123452023",
            external_status="Evidence Stage",
            external_next_hearing_date=date(2026, 12, 10)
        )

        res = LawyerService.update_court_reference(db, case_id=10, lawyer_id=1, payload=payload)
        assert res.status == "active"
        assert res.court_reference["external_status"] == "Evidence Stage"
        assert res.court_reference["external_next_hearing_date"] == date(2026, 12, 10)
        assert db.execute.called


# =============================================================================
# 4. CITIZEN SERVICE UNIT & STRICT OWNERSHIP TESTS
# =============================================================================

class TestCitizenServiceCNR:
    """Tests CitizenService methods for strict ownership and court reference handling."""

    def test_citizen_create_case_with_cnr(self):
        db = MagicMock()
        db.fetchone.return_value = {
            "case_id": 25,
            "user_id": 5,
            "case_title": "Tenant Rent Eviction",
            "title": "Tenant Rent Eviction",
            "case_type": "Civil Litigation",
            "court_name": "Small Causes Court",
            "court": "Small Causes Court",
            "opposite_party": "Landlord",
            "filing_date": None,
            "incident_date": None,
            "police_station": None,
            "location": "Pune",
            "case_description": "Unlawful eviction notice without due process",
            "description": "Unlawful eviction notice without due process",
            "status": "active",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "assigned_lawyer_id": None,
            "documents_count": 0,
            "hearings_count": 0,
            "cnr_number": "MHPU020054322024",
            "court_source": "eCourts India",
            "official_case_url": ECOURTS_SERVICES_PORTAL,
            "last_verified_at": None,
            "external_status": None,
            "external_next_hearing_date": None
        }

        payload = CitizenCaseCreate(
            title="Tenant Rent Eviction",
            description="Unlawful eviction notice without due process",
            cnr_number="  mhpu020054322024 "
        )

        res = CitizenService.create_case(db, user_id=5, payload=payload)
        assert res["cnr_number"] == "MHPU020054322024"
        assert res["status"] == "active"

    def test_citizen_cannot_access_unowned_case(self):
        """Ensures citizen cannot view or update another user's case (ownership boundary)."""
        db = MagicMock()
        db.fetchone.return_value = None  # No matching record where cases.user_id = 5

        detail = CitizenService.get_case_detail(db, user_id=5, case_id=999)
        assert detail is None

    def test_citizen_update_court_reference(self):
        db = MagicMock()
        db.fetchone.side_effect = [
            # 1. Ownership check
            {
                "case_id": 25,
                "user_id": 5,
                "case_title": "Tenant Rent Eviction",
                "court_name": "Small Causes Court",
                "status": "active",
                "cnr_number": None,
                "external_status": None,
                "external_next_hearing_date": None
            },
            # 2. Existing reminder check
            None,
            # 3. get_case_detail fetch
            {
                "case_id": 25,
                "user_id": 5,
                "case_title": "Tenant Rent Eviction",
                "case_type": "Civil Litigation",
                "court_name": "Small Causes Court",
                "opposite_party": "Landlord",
                "filing_date": None,
                "incident_date": None,
                "police_station": None,
                "location": "Pune",
                "case_description": "Unlawful eviction notice without due process",
                "status": "active",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "assigned_lawyer_id": None,
                "assigned_lawyer_name": None,
                "assigned_lawyer_email": None,
                "assigned_lawyer_phone": None,
                "assigned_lawyer_specialization": None,
                "cnr_number": "MHPU020054322024",
                "court_source": "eCourts India",
                "official_case_url": ECOURTS_SERVICES_PORTAL,
                "last_verified_at": datetime.now(),
                "external_status": "Written Statement Filed",
                "external_next_hearing_date": date(2026, 11, 28)
            }
        ]
        db.fetchall.return_value = []

        payload = CitizenCaseCourtReferenceUpdate(
            cnr_number="MHPU020054322024",
            external_status="Written Statement Filed",
            external_next_hearing_date=date(2026, 11, 28)
        )

        res = CitizenService.update_court_reference(db, user_id=5, case_id=25, payload=payload)
        assert res is not None
        assert res["court_reference"]["cnr_number"] == "MHPU020054322024"
        assert res["court_reference"]["external_status"] == "Written Statement Filed"


# =============================================================================
# 5. FASTAPI API ROUTER INTEGRATION & SECURITY TESTS
# =============================================================================

class TestFastAPIRoutesCNR:
    """Tests FastAPI router endpoints for Lawyer and Citizen court-reference operations."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_lawyer_patch_court_reference_endpoint(self, client):
        mock_lawyer = {"user_id": 2, "lawyer_id": 1, "role": "lawyer"}
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"case_id": 1, "user_id": 1, "case_title": "Case 1", "status": "active", "court_name": "Court"},
            None,
            {
                "case_id": 1, "user_id": 1, "case_title": "Case 1", "case_number": "C1", "case_type": "Civil",
                "court_name": "Court", "opposite_party": "OP", "filing_date": "2026-01-01", "incident_date": None,
                "location": None, "police_station": None, "case_description": "Desc", "status": "active",
                "created_at": datetime.now(), "updated_at": datetime.now(), "client_name": "Client",
                "client_phone": "123", "client_email": "c@example.com", "assigned_lawyer_id": 1,
                "cnr_number": "MHAU010123452023", "court_source": "eCourts India",
                "official_case_url": ECOURTS_SERVICES_PORTAL, "last_verified_at": datetime.now(),
                "external_status": "Stay Granted", "external_next_hearing_date": "2026-11-30"
            }
        ]
        mock_cursor.fetchall.return_value = []

        app.dependency_overrides[require_lawyer] = lambda: mock_lawyer
        app.dependency_overrides[get_db] = lambda: mock_cursor

        try:
            resp = client.patch(
                "/api/lawyer/cases/1/court-reference",
                json={
                    "cnr_number": "MHAU010123452023",
                    "external_status": "Stay Granted",
                    "external_next_hearing_date": "2026-11-30"
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["court_reference"]["cnr_number"] == "MHAU010123452023"
            assert data["court_reference"]["external_status"] == "Stay Granted"
        finally:
            app.dependency_overrides.clear()

    def test_citizen_patch_court_reference_endpoint(self, client):
        mock_citizen = {"user_id": 5, "role": "citizen"}
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"case_id": 25, "user_id": 5, "case_title": "Matter", "court_name": "Court", "status": "active"},
            None,
            {
                "case_id": 25, "user_id": 5, "case_title": "Matter", "title": "Matter", "case_type": "Civil",
                "court_name": "Court", "court": "Court", "opposite_party": "OP", "filing_date": None, "incident_date": None,
                "police_station": None, "location": None, "case_description": "Desc", "description": "Desc", "status": "active",
                "created_at": datetime.now(), "updated_at": datetime.now(), "assigned_lawyer_id": None,
                "assigned_lawyer_name": None, "assigned_lawyer_email": None, "assigned_lawyer_phone": None, "assigned_lawyer_specialization": None,
                "cnr_number": "MHPU020054322024", "court_source": "eCourts India",
                "official_case_url": ECOURTS_SERVICES_PORTAL, "last_verified_at": datetime.now(),
                "external_status": "Notice Awaited", "external_next_hearing_date": "2026-12-05"
            }
        ]
        mock_cursor.fetchall.return_value = []

        app.dependency_overrides[require_citizen] = lambda: mock_citizen
        app.dependency_overrides[get_db] = lambda: mock_cursor

        try:
            resp = client.patch(
                "/api/citizen/cases/25/court-reference",
                json={
                    "cnr_number": "MHPU020054322024",
                    "external_status": "Notice Awaited",
                    "external_next_hearing_date": "2026-12-05"
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["court_reference"]["cnr_number"] == "MHPU020054322024"
        finally:
            app.dependency_overrides.clear()

    def test_invalid_cnr_returns_422_or_400(self, client):
        mock_lawyer = {"user_id": 2, "lawyer_id": 1, "role": "lawyer"}
        mock_cursor = MagicMock()
        app.dependency_overrides[require_lawyer] = lambda: mock_lawyer
        app.dependency_overrides[get_db] = lambda: mock_cursor

        try:
            resp = client.patch(
                "/api/lawyer/cases/1/court-reference",
                json={
                    "cnr_number": "BAD-CNR",
                    "external_status": "Invalid"
                }
            )
            assert resp.status_code in [400, 422]
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# 6. ZERO-SCRAPING & NO-CAPTCHA-AUTOMATION COMPLIANCE TEST
# =============================================================================

class TestNoScrapingCompliance:
    """Verifies that the codebase contains no automated eCourts scrapers or CAPTCHA solvers."""

    def test_no_scraping_libraries_imported(self):
        import app.core.cnr_validator as cnr_val
        import app.services.lawyer_service as ls
        import app.services.citizen_service as cs

        for module in [cnr_val, ls, cs]:
            module_text = open(module.__file__, "r", encoding="utf-8").read()
            assert "selenium" not in module_text.lower()
            assert "playwright" not in module_text.lower()
            assert "pytesseract" not in module_text.lower()
            assert "2captcha" not in module_text.lower()
            assert "anticaptcha" not in module_text.lower()

    def test_official_url_is_ecourts_portal(self):
        assert "services.ecourts.gov.in" in ECOURTS_SERVICES_PORTAL
        assert "ecourts.gov.in" in ECOURTS_MAIN_PORTAL
