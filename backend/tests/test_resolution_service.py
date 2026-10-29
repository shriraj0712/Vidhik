"""
Vidhik Platform - Legal Resolution Decision Engine Test Suite
==============================================================
Validates:
1. Urgent Rules (Physical danger, domestic violence, arrest threat, child endangerment, imminent deadline)
2. Lawyer-Required Rules (Criminal FIR, court summons, property title, contested custody, high commercial, insolvency, writ, arbitration, labour, cyber fraud)
3. Self-Resolvable Rules (RTI, administrative certificates, simple consumer, traffic challans, tenancy notices, utility transfers)
4. Rule Precedence (Urgent > Lawyer > Self-Resolvable > Fallback)
5. Fallback for ambiguous/insufficient facts
6. Multilingual support (Marathi and Hindi scenarios)
7. FastAPI endpoint compliance (POST /api/resolution/evaluate, GET /api/resolution/health)
8. Backward compatibility across existing platform endpoints
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.resolution import (
    RecommendationType,
    RiskLevel,
    ResolutionEvaluationRequest,
    ResolutionEvaluationResponse
)
from app.services.resolution_service import (
    ResolutionDecisionEngine,
    VERIFIED_PROCEDURES,
    VERIFIED_EMERGENCY_DATA
)

client = TestClient(app)


# ==============================================================================
# 1. URGENT RULES TESTS
# ==============================================================================

def test_urgent_physical_danger():
    """Asserts that imminent physical danger triggers urgent intervention with critical risk."""
    req = ResolutionEvaluationRequest(
        situation="My neighbor has pulled out a knife, attacked my family, and threatened to kill us if we step outside.",
        is_physical_danger=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.URGENT_LEGAL_INTERVENTION
    assert res.risk_level == RiskLevel.CRITICAL
    assert any(r.rule_id == "URGENT_PHYSICAL_SAFETY" for r in res.triggered_rules)
    assert res.emergency_guidance is not None
    assert any(h["number"] == "112" for h in res.emergency_guidance["national_helplines"])
    assert "112" in res.next_steps[0]


def test_urgent_domestic_violence():
    """Asserts that active domestic violence and spousal assault triggers urgent intervention."""
    req = ResolutionEvaluationRequest(
        situation="My husband is beating me violently for dowry and has locked me inside the room.",
        involves_domestic_violence=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.URGENT_LEGAL_INTERVENTION
    assert res.risk_level == RiskLevel.CRITICAL
    assert any(r.rule_id == "URGENT_ACTIVE_DOMESTIC_VIOLENCE" for r in res.triggered_rules)
    assert res.emergency_guidance is not None
    assert any("1091" in h["number"] for h in res.emergency_guidance["national_helplines"])


def test_urgent_arrest_detention():
    """Asserts that police raid, arrest threats, or custody triggers urgent criminal defense."""
    req = ResolutionEvaluationRequest(
        situation="Police are raiding my house with an arrest warrant and threatening to take me into custody right now.",
        has_arrest_threat=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.URGENT_LEGAL_INTERVENTION
    assert res.risk_level == RiskLevel.CRITICAL
    assert any(r.rule_id == "URGENT_ARREST_DETENTION" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Criminal Defense & Bail"


def test_urgent_child_endangerment():
    """Asserts that child abuse or POCSO emergency triggers childline escalation."""
    req = ResolutionEvaluationRequest(
        situation="A neighbor has committed sexual assault against a minor child and is threatening the child.",
        involves_children=True,
        is_physical_danger=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.URGENT_LEGAL_INTERVENTION
    assert res.risk_level == RiskLevel.CRITICAL
    assert any(r.rule_id == "URGENT_CHILD_ENDANGERMENT" for r in res.triggered_rules)
    assert any("1098" in h["number"] for h in res.emergency_guidance["national_helplines"])


def test_urgent_imminent_deadline():
    """Asserts that 24-48 hour imminent statutory or court deadline triggers urgent intervention."""
    req = ResolutionEvaluationRequest(
        situation="The municipal corporation has issued an eviction notice with only 24 hours deadline before bulldozing the shop tomorrow.",
        has_urgent_deadline=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.URGENT_LEGAL_INTERVENTION
    assert res.risk_level == RiskLevel.CRITICAL
    assert any(r.rule_id == "URGENT_IMMINENT_DEADLINE" for r in res.triggered_rules)


# ==============================================================================
# 2. LAWYER REQUIRED RULES TESTS
# ==============================================================================

def test_lawyer_non_bailable_criminal():
    """Asserts that serious criminal FIR allegations require criminal defense counsel."""
    req = ResolutionEvaluationRequest(
        situation="An FIR has been registered against me alleging cheating and fraud under Section 420 of IPC involving business funds.",
        has_police_involvement=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert res.risk_level == RiskLevel.HIGH
    assert any(r.rule_id == "LAWYER_NON_BAILABLE_CRIMINAL" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Criminal Defense & Bail"


def test_lawyer_active_court_proceedings():
    """Asserts that formal court summons and civil lawsuit requires lawyer consultation."""
    req = ResolutionEvaluationRequest(
        situation="I have received a court summons from the civil court requiring me to file a written statement in a civil suit.",
        has_court_notice=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert any(r.rule_id == "LAWYER_ACTIVE_COURT_PROCEEDINGS" for r in res.triggered_rules)


def test_lawyer_property_title_dispute():
    """Asserts that ancestral property title disputes and forged deeds require property law specialization."""
    req = ResolutionEvaluationRequest(
        situation="My relatives have created a forged sale deed for our ancestral property and filed a partition suit.",
        issue_category="Property"
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert res.risk_level == RiskLevel.HIGH
    assert any(r.rule_id == "LAWYER_PROPERTY_TITLE_DISPUTE" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Property & Real Estate"


def test_lawyer_contested_matrimonial():
    """Asserts that contested divorce and child custody battle require family law counsel."""
    req = ResolutionEvaluationRequest(
        situation="My spouse has filed for contested divorce and is fighting for sole child custody and exorbitant alimony.",
        issue_category="Family"
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert any(r.rule_id == "LAWYER_CONTESTED_MATRIMONIAL" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Family & Matrimonial"


def test_lawyer_high_value_commercial():
    """Asserts that commercial breach of contract over ₹10 Lakhs requires commercial advocate."""
    req = ResolutionEvaluationRequest(
        situation="A supplier has committed a massive breach of contract causing severe business damage.",
        monetary_amount=2500000.0  # ₹25 Lakhs
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert res.risk_level == RiskLevel.HIGH
    assert any(r.rule_id == "LAWYER_HIGH_VALUE_COMMERCIAL" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Corporate & Commercial"


def test_lawyer_insolvency_bankruptcy():
    """Asserts that NCLT / IBC insolvency matters trigger insolvency specialization."""
    req = ResolutionEvaluationRequest(
        situation="Our creditor has filed a Section 7 insolvency petition before NCLT under the IBC for corporate default."
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert any(r.rule_id == "LAWYER_INSOLVENCY_BANKRUPTCY" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Insolvency & Bankruptcy (NCLT)"


def test_lawyer_constitutional_writ():
    """Asserts that High Court writ petitions under Article 226 require constitutional counsel."""
    req = ResolutionEvaluationRequest(
        situation="The state government has arbitrarily cancelled my government license without giving a hearing, violating Article 226."
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert any(r.rule_id == "LAWYER_CONSTITUTIONAL_WRIT" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Constitutional & Public Law"


def test_lawyer_arbitration_matters():
    """Asserts that formal commercial arbitration requires arbitration counsel."""
    req = ResolutionEvaluationRequest(
        situation="The counterparty has invoked the arbitration clause and approached the High Court under Section 11 to appoint an arbitrator."
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert any(r.rule_id == "LAWYER_ARBITRATION_MATTERS" for r in res.triggered_rules)


def test_lawyer_labour_termination():
    """Asserts that wrongful employment termination requires labour law advice."""
    req = ResolutionEvaluationRequest(
        situation="I was subjected to illegal termination without notice or severance pay and my gratuity has been withheld."
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert any(r.rule_id == "LAWYER_LABOUR_TERMINATION" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Labour & Employment"


def test_lawyer_cyber_financial_fraud_high():
    """Asserts that large-scale bank account hacking (> ₹2 Lakhs) requires cyber law expertise."""
    req = ResolutionEvaluationRequest(
        situation="My bank account was hacked via SIM swap and ₹5,00,000 was drained via unauthorized wire transfer.",
        monetary_amount=500000.0
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert any(r.rule_id == "LAWYER_CYBER_FINANCIAL_FRAUD_HIGH" for r in res.triggered_rules)
    assert res.lawyer_specialization_needed == "Cyber & IT Law"


# ==============================================================================
# 3. SELF RESOLVABLE RULES TESTS
# ==============================================================================

def test_self_resolvable_rti():
    """Asserts that RTI application is categorized as self-resolvable with Procedure #1 attached."""
    req = ResolutionEvaluationRequest(
        situation="I want to file an RTI application to get a copy of the government tender evaluation and marksheet."
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert res.risk_level == RiskLevel.LOW
    assert any(r.rule_id == "SELF_RTI_APPLICATION" for r in res.triggered_rules)
    assert any(p.procedure_slug == "rti-application" for p in res.relevant_procedures)
    assert len(res.self_help_checklist) > 0


def test_self_resolvable_birth_certificate():
    """Asserts that birth certificate correction is self-resolvable with Procedure #10 attached."""
    req = ResolutionEvaluationRequest(
        situation="I need to apply for birth certificate correction to fix a spelling mistake in my child's name at the municipal ward."
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert res.risk_level == RiskLevel.LOW
    assert any(r.rule_id == "SELF_ROUTINE_ADMIN_CERTIFICATE" for r in res.triggered_rules)
    assert any(p.procedure_slug == "birth-certificate-registration-correction" for p in res.relevant_procedures)


def test_self_resolvable_caste_certificate():
    """Asserts that caste certificate application attaches Procedure #12."""
    req = ResolutionEvaluationRequest(
        situation="How do I submit an application for caste certificate issuance and scrutiny at the tehsil office?"
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert any(p.procedure_slug == "caste-certificate-issuance" for p in res.relevant_procedures)


def test_self_resolvable_consumer_grievance_small():
    """Asserts that small consumer grievance (< ₹5L) attaches Procedure #2 (E-Daakhil)."""
    req = ResolutionEvaluationRequest(
        situation="I purchased a smartphone for 15,000 rupees online, received a defective product, and the e-commerce company is refusing a refund.",
        monetary_amount=15000.0
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert res.risk_level == RiskLevel.LOW
    assert any(r.rule_id == "SELF_CONSUMER_GRIEVANCE_SIMPLE" for r in res.triggered_rules)
    assert any(p.procedure_slug == "consumer-complaint" for p in res.relevant_procedures)


def test_self_resolvable_traffic_challan():
    """Asserts that traffic e-challan payment is self-resolvable with Procedure #21."""
    req = ResolutionEvaluationRequest(
        situation="I received an e-challan for signal jump fine of 1,000 rupees on my two-wheeler and want to check payment options on virtual traffic court.",
        monetary_amount=1000.0
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert any(r.rule_id == "SELF_TRAFFIC_CHALLAN_ROUTINE" for r in res.triggered_rules)
    assert any(p.procedure_slug == "traffic-e-challan-challenge" for p in res.relevant_procedures)


def test_self_resolvable_tenancy_notice():
    """Asserts that standard 30-day notice to landlord for security deposit return is self-resolvable."""
    req = ResolutionEvaluationRequest(
        situation="I am vacating my rented flat and want to send a formal 30 days notice to my landlord for security deposit return.",
        monetary_amount=50000.0
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert any(r.rule_id == "SELF_BASIC_TENANCY_COMMUNICATION" for r in res.triggered_rules)


def test_self_resolvable_electricity_meter():
    """Asserts that utility meter name transfer attaches Procedure #22."""
    req = ResolutionEvaluationRequest(
        situation="How do I apply for electricity meter name change after purchasing an apartment?"
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert any(p.procedure_slug == "electricity-meter-name-transfer" for p in res.relevant_procedures)


# ==============================================================================
# 4. RULE PRECEDENCE & PRIORITY CONFLICT TESTS
# ==============================================================================

def test_precedence_urgent_overrides_self_resolvable():
    """
    CRITICAL TEST: If a user asks for an RTI document but also mentions physical assault and death threats,
    URGENT_LEGAL_INTERVENTION must override SELF_RESOLVABLE.
    """
    req = ResolutionEvaluationRequest(
        situation="I want to file an RTI application to get local municipal contractor records, but the contractor attacked me with a weapon and threatened to kill me if I proceed.",
        is_physical_danger=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.URGENT_LEGAL_INTERVENTION
    assert res.risk_level == RiskLevel.CRITICAL
    # Both triggered rules must be preserved in audit telemetry
    rule_ids = [r.rule_id for r in res.triggered_rules]
    assert "URGENT_PHYSICAL_SAFETY" in rule_ids
    assert "SELF_RTI_APPLICATION" in rule_ids


def test_precedence_lawyer_overrides_self_resolvable():
    """
    CRITICAL TEST: If a consumer dispute mentions a formal court lawsuit or claim > ₹10 Lakhs,
    LAWYER_CONSULTATION_REQUIRED must override SELF_RESOLVABLE.
    """
    req = ResolutionEvaluationRequest(
        situation="I had a consumer complaint for defective equipment, but the company has now filed a formal lawsuit with a court summons against me for ₹15,00,000.",
        has_court_notice=True,
        monetary_amount=1500000.0
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert res.risk_level == RiskLevel.HIGH


def test_precedence_multiple_lawyer_rules_preserved():
    """Asserts that multiple concurrent lawyer rules (Property title + Criminal allegations) are all retained in response."""
    req = ResolutionEvaluationRequest(
        situation="My uncle filed a criminal FIR of cheating against me and also filed a partition suit regarding our ancestral property.",
        has_police_involvement=True
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    rule_ids = [r.rule_id for r in res.triggered_rules]
    assert "LAWYER_NON_BAILABLE_CRIMINAL" in rule_ids
    assert "LAWYER_PROPERTY_TITLE_DISPUTE" in rule_ids


# ==============================================================================
# 5. CAUTIOUS FALLBACK (INSUFFICIENT FACTS)
# ==============================================================================

def test_fallback_vague_narrative():
    """Asserts that ambiguous or general situations default safely to cautious lawyer review."""
    req = ResolutionEvaluationRequest(
        situation="I need general legal advice about some agreement issues with a person."
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.LAWYER_CONSULTATION_REQUIRED
    assert res.risk_level == RiskLevel.MEDIUM
    assert res.confidence == "cautious_fallback"
    assert any(r.rule_id == "FALLBACK_INSUFFICIENT_FACTS_CAUTIOUS" for r in res.triggered_rules)


# ==============================================================================
# 6. MULTILINGUAL TESTS (MARATHI & HINDI)
# ==============================================================================

def test_multilingual_marathi_urgent_domestic_violence():
    """Asserts that Marathi domestic violence prompt triggers urgent intervention."""
    req = ResolutionEvaluationRequest(
        situation="माझे पती मला हुंड्यासाठी खूप मारहाण करत आहेत आणि घरात डांबून ठेवले आहे.",
        language="mr"
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.URGENT_LEGAL_INTERVENTION
    assert res.risk_level == RiskLevel.CRITICAL
    assert any(r.rule_id == "URGENT_ACTIVE_DOMESTIC_VIOLENCE" for r in res.triggered_rules)


def test_multilingual_marathi_self_rti():
    """Asserts that Marathi RTI prompt triggers self-resolvable triage."""
    req = ResolutionEvaluationRequest(
        situation="मला महानगरपालिकेकडून माहिती अधिकार (RTI) अंतर्गत माहिती मागवायची आहे.",
        language="mr"
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert any(r.rule_id == "SELF_RTI_APPLICATION" for r in res.triggered_rules)


def test_multilingual_hindi_urgent_arrest():
    """Asserts that Hindi arrest warrant prompt triggers urgent intervention."""
    req = ResolutionEvaluationRequest(
        situation="पुलिस मेरे घर पर गिरफ्तारी वारंट लेकर आई है और मुझे तुरंत हिरासत में लेने की धमकी दे रही है।",
        language="hi"
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.URGENT_LEGAL_INTERVENTION
    assert res.risk_level == RiskLevel.CRITICAL
    assert any(r.rule_id == "URGENT_ARREST_DETENTION" for r in res.triggered_rules)


def test_multilingual_hindi_self_traffic():
    """Asserts that Hindi traffic challan prompt triggers self-resolvable triage."""
    req = ResolutionEvaluationRequest(
        situation="मुझे सिग्नल तोड़ने का ई-चालान मिला है, ऑनलाइन जुर्माना कैसे भरें?",
        language="hi"
    )
    res = ResolutionDecisionEngine.evaluate(req)

    assert res.recommendation_type == RecommendationType.SELF_RESOLVABLE
    assert any(r.rule_id == "SELF_TRAFFIC_CHALLAN_ROUTINE" for r in res.triggered_rules)


# ==============================================================================
# 7. FASTAPI API ROUTER & VALIDATION TESTS
# ==============================================================================

def test_api_resolution_evaluate_success():
    """Asserts that POST /api/resolution/evaluate returns 200 OK with valid schema."""
    payload = {
        "situation": "I want to apply for a Right to Information (RTI) request for road construction records.",
        "jurisdiction": "Maharashtra",
        "language": "en"
    }
    resp = client.post("/api/resolution/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendation_type"] == "self_resolvable"
    assert data["risk_level"] == "low"
    assert "disclaimer" in data
    assert len(data["self_help_checklist"]) > 0


def test_api_resolution_evaluate_validation_error():
    """Asserts that empty or short situation strings return 422 Unprocessable Entity."""
    resp = client.post("/api/resolution/evaluate", json={"situation": "  "})
    assert resp.status_code == 422


def test_api_resolution_health_endpoint():
    """Asserts that GET /api/resolution/health returns 200 OK and diagnostic telemetry."""
    resp = client.get("/api/resolution/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert data["subsystem"] == "Vidhik Resolution Decision Engine"
    assert data["deterministic_classification"] is True


def test_backward_compatibility_existing_endpoints(monkeypatch):
    """Asserts that new resolution engine registration did not break existing platform endpoints."""
    # Health check
    resp_health = client.get("/health")
    assert resp_health.status_code == 200

    # Assistant and RAG health with an available configured provider.
    ready_provider = {"provider": "test (model)", "ready": True, "status": "ready"}
    monkeypatch.setattr("app.routers.assistant.check_llm_provider_readiness", lambda: ready_provider)
    monkeypatch.setattr("app.routers.rag.check_llm_provider_readiness", lambda: ready_provider)
    resp_asst = client.get("/api/assistant/health")
    assert resp_asst.status_code == 200

    # RAG health
    resp_rag = client.get("/api/rag/health")
    assert resp_rag.status_code == 200
