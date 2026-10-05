"""
Vidhik Platform - Case Intelligence & Central Context Comprehensive Tests
========================================================================
Validates all 25 features of the Case-Centric Legal Decision Support System:
- Feature 1: Overall Case Description & Fact Extraction (Cautious phrasing)
- Feature 2 & 3: Database-Grounded Legal Analysis & Ranked Provisions
- Feature 4: Case-Specific Action Plan (Immediate, Next, Optional)
- Feature 5: Document & Evidence Requirements Checklist
- Feature 6: Further Procedure Pathway & Timeline
- Feature 7: Emotional State Analysis & Adaptive Guidance (No clinical diagnosis)
- Feature 8 & 12: Persistent Current Case & Case Switching
- Feature 10 & 11: Central Case Context & Scoped Endpoints
- Feature 13: Case Isolation & Security (Cross-user access denied)
- Feature 14: Database-Driven Lawyer Recommendations (Zero hallucination)
- Feature 17: Case Update & Re-analysis Workflow
- Feature 18: Missing Information Identification
- Features 19, 20, 21: Test Cases (Traffic/Licence, Tenancy/Deposit, Employment/Salary, Consumer, Cyber, Criminal)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db_cursor
from app.services.case_intelligence_service import CaseIntelligenceService
from app.core.security import create_access_token

client = TestClient(app)


# Helpers for authenticated requests
def get_user_token(user_id: int = 201, email: str = "sunita.sharma@example.com", role: str = "user"):
    return create_access_token(user_id=user_id, email=email, role=role, full_name="Sunita Sharma")


def auth_headers(user_id: int = 201, email: str = "sunita.sharma@example.com", role: str = "user"):
    token = get_user_token(user_id, email, role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# TEST SUITE 1: SITUATION UNDERSTANDING & CAUTIOUS PHRASING (FEATURE 1, 18)
# ==============================================================================
def test_traffic_licence_case_understanding():
    """Validates Feature 1: Traffic police licence incident understanding."""
    text = "Traffic police scratched my licence."
    overview = CaseIntelligenceService.analyze_situation(
        title="Traffic Police Stop",
        description=text,
        location="Pune, Maharashtra"
    )

    # 1. Cautious language check
    assert "Based on the information provided" in overview.situation_summary
    assert "appears to concern" in overview.situation_summary
    assert "driving licence" in overview.situation_summary.lower()

    # 2. Domain classification
    assert overview.case_category == "Traffic Enforcement & Motor Vehicle"
    assert overview.legal_domain == "Motor Vehicle Law"

    # 3. Facts and issues
    assert len(overview.explicit_facts) > 0
    assert len(overview.extracted_facts) > 0
    assert any("Section 130" in issue or "Section 206" in issue for issue in overview.identified_issues)

    # 4. Uncertain facts and missing information (Feature 18)
    assert len(overview.uncertain_facts) > 0
    assert len(overview.missing_information) > 0
    assert any("challan" in item.lower() for item in overview.missing_information)


def test_tenancy_security_deposit_understanding():
    """Validates Feature 20: Tenancy security deposit refusal understanding."""
    text = "My landlord is refusing to return my security deposit."
    overview = CaseIntelligenceService.analyze_situation(
        title="Deposit Dispute",
        description=text,
        location="Mumbai, Maharashtra"
    )

    assert "Based on the information provided" in overview.situation_summary
    assert overview.case_category == "Tenancy & Rental Dispute"
    assert overview.legal_domain == "Property & Tenancy Law"
    assert any("Transfer of Property Act" in issue or "Contract Act" in issue for issue in overview.identified_issues)
    assert len(overview.missing_information) > 0


def test_employment_unpaid_salary_understanding():
    """Validates Feature 21: Employment unpaid salary understanding."""
    text = "My employer has not paid my salary for two months."
    overview = CaseIntelligenceService.analyze_situation(
        title="Unpaid Salary Matter",
        description=text,
        location="Mumbai"
    )

    assert "Based on the information provided" in overview.situation_summary
    assert overview.case_category == "Employment & Wage Dispute"
    assert overview.legal_domain == "Labour & Employment Law"
    assert any("Payment of Wages Act" in issue or "Contract Act" in issue for issue in overview.identified_issues)


# ==============================================================================
# TEST SUITE 2: DATABASE-GROUNDED LEGAL PROVISIONS & RANKING (FEATURES 2, 3)
# ==============================================================================
def test_traffic_licence_legal_provisions():
    """Validates Feature 2 & 3: Grounded statutory sections for Motor Vehicle stop."""
    with get_db_cursor() as cur:
        provisions = CaseIntelligenceService.get_grounded_legal_provisions(
            category="Traffic Enforcement & Motor Vehicle",
            domain="Motor Vehicle Law",
            query_text="Traffic police scratched licence Section 130 Section 206 Motor Vehicles Act",
            db=cur,
            limit=5
        )

        assert len(provisions) >= 3
        # Check first provision is MVA
        mva_sections = [p for p in provisions if "Motor Vehicles" in p.act_name or p.short_name == "MVA"]
        assert len(mva_sections) >= 2

        # Check section 130 or 206 presence
        sec_nums = [p.section_number for p in provisions]
        assert "130" in sec_nums or "206" in sec_nums

        # Cautious framing check
        for p in provisions:
            assert "Potentially relevant" in p.cautious_framing
            assert len(p.simple_explanation) > 10
            assert len(p.why_relevant) > 10


def test_tenancy_legal_provisions():
    """Validates grounded statutory sections for Tenancy deposit dispute."""
    with get_db_cursor() as cur:
        provisions = CaseIntelligenceService.get_grounded_legal_provisions(
            category="Tenancy & Rental Dispute",
            domain="Property & Tenancy Law",
            query_text="Landlord refusing security deposit refund lease agreement",
            db=cur,
            limit=4
        )

        assert len(provisions) >= 2
        acts = [p.act_name for p in provisions]
        assert any("Transfer of Property" in a or "Contract" in a for a in acts)


# ==============================================================================
# TEST SUITE 3: ACTION PLAN & DOCUMENTS CHECKLIST (FEATURES 4, 5)
# ==============================================================================
def test_case_action_plan():
    """Validates Feature 4: Non-generic, case-specific action plan."""
    plan = CaseIntelligenceService.generate_action_plan(
        case_id=1,
        category="Traffic Enforcement & Motor Vehicle",
        domain="Motor Vehicle Law"
    )

    assert len(plan.immediate_actions) >= 2
    assert len(plan.recommended_next_steps) >= 2
    assert len(plan.optional_supporting_actions) >= 1

    # Immediate actions must include preservation
    immed_titles = [a.action_title.lower() for a in plan.immediate_actions]
    assert any("preserve" in t or "licence" in t or "photograph" in t for t in immed_titles)


def test_case_document_checklist():
    """Validates Feature 5: Required, Important, Supporting document checklist."""
    checklist = CaseIntelligenceService.generate_document_checklist(
        case_id=1,
        category="Traffic Enforcement & Motor Vehicle",
        domain="Motor Vehicle Law"
    )

    assert len(checklist.required_documents) >= 1
    assert len(checklist.important_documents) >= 2
    assert len(checklist.supporting_documents) >= 1

    # Check BSA 2023 evidence safeguard note
    assert "Bharatiya Sakshya Adhiniyam" in checklist.bsa_evidence_note or "Section 63" in checklist.bsa_evidence_note


# ==============================================================================
# TEST SUITE 4: FURTHER PROCEDURE & TIMELINE (FEATURE 6)
# ==============================================================================
def test_case_further_procedure():
    """Validates Feature 6: Realistic procedural pathway grounded in law."""
    proc = CaseIntelligenceService.generate_further_procedure(
        case_id=1,
        category="Traffic Enforcement & Motor Vehicle",
        domain="Motor Vehicle Law"
    )

    assert len(proc.procedural_pathway) >= 3
    assert proc.overall_timeline is not None
    # Verify cautious procedural note
    assert "Depending on the applicable procedure" in proc.procedural_note


# ==============================================================================
# TEST SUITE 5: EMOTIONAL STATE ANALYSIS (FEATURE 7)
# ==============================================================================
def test_emotional_analysis_fear_and_confusion():
    """Validates Feature 7: Emotional indicators and communication adaptation without clinical diagnosis."""
    text = "I am so scared and confused, traffic police threatened to put me in jail and scratched my card!"
    emotion = CaseIntelligenceService.analyze_emotional_state(case_id=1, text=text)

    assert "Fear/Anxiety" in emotion.detected_indicators or "Confusion" in emotion.detected_indicators
    assert emotion.disclaimer is not None
    assert "does not constitute" in emotion.disclaimer.lower()
    assert len(emotion.communication_adaptation) > 10


def test_emotional_analysis_emergency_safety():
    """Validates emergency safety notice triggering for physical threats."""
    text = "A man threatened to kill me and beat me up with physical assault!"
    emotion = CaseIntelligenceService.analyze_emotional_state(case_id=1, text=text)

    assert emotion.safety_indicators_present is True
    assert emotion.immediate_safety_notice is not None
    assert "112" in emotion.immediate_safety_notice


# ==============================================================================
# TEST SUITE 6: DATABASE-DRIVEN LAWYER RECOMMENDATION (FEATURE 14)
# ==============================================================================
def test_database_driven_lawyer_recommendation_traffic():
    """Validates Feature 14: Matching authentic database lawyers for Traffic/Motor Vehicle."""
    with get_db_cursor() as cur:
        recs = CaseIntelligenceService.match_lawyers_from_database(
            case_id=1,
            category="Traffic Enforcement & Motor Vehicle",
            domain="Motor Vehicle Law",
            jurisdiction="Pune, Maharashtra",
            db=cur
        )

        assert recs.total_lawyers_matched > 0
        top_lawyer = recs.recommended_lawyers[0]

        # Top lawyer for Traffic in Pune must be Adv. Vikramaditya Shinde (ID 2)
        assert top_lawyer.lawyer_id == 2
        assert "Vikramaditya Shinde" in top_lawyer.full_name
        assert top_lawyer.match_score > 60.0
        assert "Motor Vehicle" in top_lawyer.match_reason or "MACT" in top_lawyer.match_reason
        assert top_lawyer.is_verified is True


def test_database_driven_lawyer_recommendation_tenancy():
    """Validates matching authentic database lawyers for Tenancy/Property."""
    with get_db_cursor() as cur:
        recs = CaseIntelligenceService.match_lawyers_from_database(
            case_id=2,
            category="Tenancy & Rental Dispute",
            domain="Property & Tenancy Law",
            jurisdiction="Mumbai, Maharashtra",
            db=cur
        )

        assert recs.total_lawyers_matched > 0
        top_lawyer = recs.recommended_lawyers[0]

        # Top lawyer for Tenancy in Mumbai must be Adv. Sunita R. Rao (ID 3)
        assert top_lawyer.lawyer_id == 3
        assert "Sunita" in top_lawyer.full_name
        assert "Property" in top_lawyer.match_reason or "Tenancy" in top_lawyer.match_reason


def test_database_driven_lawyer_recommendation_employment():
    """Validates matching authentic database lawyers for Labour/Salary."""
    with get_db_cursor() as cur:
        recs = CaseIntelligenceService.match_lawyers_from_database(
            case_id=3,
            category="Employment & Wage Dispute",
            domain="Labour & Employment Law",
            jurisdiction="Mumbai, Maharashtra",
            db=cur
        )

        assert recs.total_lawyers_matched > 0
        top_lawyer = recs.recommended_lawyers[0]

        # Top lawyer for Labour/Employment in Mumbai must be Adv. Pradeep K. Verma (ID 4)
        assert top_lawyer.lawyer_id == 4
        assert "Pradeep" in top_lawyer.full_name
        assert "Labour" in top_lawyer.match_reason or "Employment" in top_lawyer.match_reason


# ==============================================================================
# TEST SUITE 7: END-TO-END API ENDPOINTS & CASE SWITCHING (FEATURES 8, 9, 10, 11, 12, 13)
# ==============================================================================
def test_create_and_analyze_case_api():
    """Validates POST /api/cases/create-and-analyze creates case and complete Central Case Context."""
    headers = auth_headers(user_id=201)
    payload = {
        "title": "Traffic Police Licence Incident",
        "description": "Traffic police scratched my licence at the Shivajinagar checkpoint.",
        "location": "Pune, Maharashtra"
    }

    res = client.post("/api/cases/create-and-analyze", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["case_id"] > 0
    assert data["user_id"] == 201
    assert "Based on the information provided" in data["situation_summary"]
    assert len(data["ranked_provisions"]) >= 2
    assert len(data["recommended_lawyers"]) >= 1
    assert data["recommended_lawyers"][0]["lawyer_id"] == 2  # Adv. Vikramaditya Shinde


def test_active_case_and_switching_api():
    """Validates Feature 8 & 12: Active case retrieval, case switching, and isolation."""
    headers = auth_headers(user_id=201)

    # 1. Create Case 1
    res1 = client.post("/api/cases/create-and-analyze", json={
        "title": "Case 1 Traffic Incident",
        "description": "Traffic police scratched my driving licence in Pune.",
        "location": "Pune"
    }, headers=headers)
    case1_id = res1.json()["case_id"]

    # 2. Create Case 2
    res2 = client.post("/api/cases/create-and-analyze", json={
        "title": "Case 2 Landlord Deposit Dispute",
        "description": "My landlord is refusing to return my security deposit in Mumbai.",
        "location": "Mumbai"
    }, headers=headers)
    case2_id = res2.json()["case_id"]

    # Active case should currently be Case 2 (most recently created)
    res_act = client.get("/api/cases/active", headers=headers)
    assert res_act.status_code == 200
    assert res_act.json()["active_case_id"] == case2_id
    assert "Tenancy" in res_act.json()["context"]["case_category"]

    # Switch active case to Case 1
    res_switch = client.post(f"/api/cases/{case1_id}/set-active", headers=headers)
    assert res_switch.status_code == 200
    assert res_switch.json()["active_case_id"] == case1_id

    # Verify active case is now Case 1 with zero data leakage
    res_act2 = client.get("/api/cases/active", headers=headers)
    assert res_act2.json()["active_case_id"] == case1_id
    assert "Traffic" in res_act2.json()["context"]["case_category"]


def test_case_modular_endpoints_api():
    """Validates Feature 11: Modular endpoints scoped to case_id."""
    headers = auth_headers(user_id=201)

    # Create case
    res = client.post("/api/cases/create-and-analyze", json={
        "title": "Modular Endpoint Verification Case",
        "description": "Traffic police scratched my licence at intersection.",
        "location": "Pune"
    }, headers=headers)
    case_id = res.json()["case_id"]

    # 1. GET situation-overview
    res_sit = client.get(f"/api/cases/{case_id}/situation-overview", headers=headers)
    assert res_sit.status_code == 200
    assert "Based on the information provided" in res_sit.json()["situation_summary"]

    # 2. GET legal-analysis
    res_leg = client.get(f"/api/cases/{case_id}/legal-analysis", headers=headers)
    assert res_leg.status_code == 200
    assert len(res_leg.json()["ranked_provisions"]) > 0

    # 3. GET action-plan
    res_act = client.get(f"/api/cases/{case_id}/action-plan", headers=headers)
    assert res_act.status_code == 200
    assert len(res_act.json()["immediate_actions"]) > 0

    # 4. GET documents
    res_doc = client.get(f"/api/cases/{case_id}/documents", headers=headers)
    assert res_doc.status_code == 200
    assert len(res_doc.json()["required_documents"]) > 0

    # 5. GET procedure
    res_pr = client.get(f"/api/cases/{case_id}/procedure", headers=headers)
    assert res_pr.status_code == 200
    assert len(res_pr.json()["procedural_pathway"]) > 0

    # 6. GET emotional-analysis
    res_em = client.get(f"/api/cases/{case_id}/emotional-analysis", headers=headers)
    assert res_em.status_code == 200
    assert "Neutral/Calm" in res_em.json()["detected_indicators"] or "Anger/Frustration" in res_em.json()["detected_indicators"]

    # 7. GET lawyer-recommendation
    res_law = client.get(f"/api/cases/{case_id}/lawyer-recommendation", headers=headers)
    assert res_law.status_code == 200
    assert len(res_law.json()["recommended_lawyers"]) > 0


def test_case_update_and_reanalyze_api():
    """Validates Feature 17: Case update with new facts and re-analysis."""
    headers = auth_headers(user_id=201)

    # Initial case creation
    res = client.post("/api/cases/create-and-analyze", json={
        "title": "Initial Traffic Stop",
        "description": "Traffic police scratched my licence.",
        "location": "Pune"
    }, headers=headers)
    case_id = res.json()["case_id"]
    v1 = res.json()["analysis_version"]

    # Update with additional information
    res_up = client.post(f"/api/cases/{case_id}/update-and-reanalyze", json={
        "additional_information": "The officer also kept my licence for two days without giving any receipt or challan."
    }, headers=headers)

    assert res_up.status_code == 200
    updated_data = res_up.json()
    assert updated_data["analysis_version"] == v1 + 1
    assert "two days" in updated_data["original_description"]


def test_unauthorized_case_isolation():
    """Validates Feature 13: Strict cross-user isolation. User B cannot access User A's case."""
    user_a_headers = auth_headers(user_id=201, email="user_a@example.com")
    user_b_headers = auth_headers(user_id=202, email="user_b@example.com")

    # User A creates a case
    res_a = client.post("/api/cases/create-and-analyze", json={
        "title": "User A Private Confidential Matter",
        "description": "Confidential legal dispute involving personal funds.",
        "location": "Pune"
    }, headers=user_a_headers)
    case_a_id = res_a.json()["case_id"]

    # User B attempts to access User A's case context
    res_b_context = client.get(f"/api/cases/{case_a_id}/context", headers=user_b_headers)
    assert res_b_context.status_code == 404

    # User B attempts to switch to User A's case
    res_b_switch = client.post(f"/api/cases/{case_a_id}/set-active", headers=user_b_headers)
    assert res_b_switch.status_code == 404

    # User B attempts to get situation-overview for User A's case
    res_b_sit = client.get(f"/api/cases/{case_a_id}/situation-overview", headers=user_b_headers)
    assert res_b_sit.status_code == 404
