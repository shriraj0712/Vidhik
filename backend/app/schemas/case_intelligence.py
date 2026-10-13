"""
Vidhik Platform - Case Intelligence & Central Context Schemas
============================================================
Pydantic models representing the central Case Context and its sub-modules:
- Case understanding & situation overview
- Database-grounded statutory provisions & simple explanations
- Case-specific recommended actions (immediate, next, optional)
- Case-specific document & evidence checklist (required, important, supporting)
- Procedural pathway & timeline
- Emotional indicators & adaptive communication guidance
- Database-driven matched lawyers & deterministic match explanations
- Authority recommendations
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# 1. CASE UNDERSTANDING & SITUATION OVERVIEW
# -------------------------------------------------------------
class CaseFactItem(BaseModel):
    category: str = Field(..., description="Fact category: explicit, inferred, or context")
    fact: str = Field(..., description="Extracted factual statement")
    is_verified: bool = Field(True, description="Whether explicitly stated by user")


class CaseSituationOverview(BaseModel):
    situation_summary: str = Field(..., description="Cautious, objective plain-language summary of situation")
    explicit_facts: List[str] = Field(default_factory=list, description="Facts explicitly stated by the user")
    extracted_facts: List[str] = Field(default_factory=list, description="Important facts extracted from statement")
    identified_issues: List[str] = Field(default_factory=list, description="Potential legal issues identified")
    uncertain_facts: List[str] = Field(default_factory=list, description="Facts that remain uncertain or unconfirmed")
    missing_information: List[str] = Field(default_factory=list, description="Missing information needed for precise analysis")
    case_category: str = Field("General Legal Matter", description="Broad category of dispute")
    legal_domain: str = Field("General Indian Law", description="Specific legal domain")
    jurisdiction: Optional[str] = Field(None, description="Inferred or stated jurisdiction")
    urgency: str = Field("Medium", description="Low, Medium, High, or Critical")


# -------------------------------------------------------------
# 2. DATABASE-GROUNDED LEGAL PROVISION & SIMPLE EXPLANATION
# -------------------------------------------------------------
class RankedLegalProvision(BaseModel):
    rank: int = Field(..., description="Deterministic rank position")
    act_id: Optional[int] = Field(None, description="Enactment ID")
    act_name: str = Field(..., description="Statute name")
    short_name: Optional[str] = Field(None, description="Statute short acronym")
    section_number: str = Field(..., description="Statutory section number")
    section_title: str = Field(..., description="Official section heading")
    relevance_score: float = Field(..., description="Relevance score (0 to 100)")
    relevance_tier: str = Field("Relevant", description="Directly Relevant, Contextually Relevant, or Supporting")
    simple_explanation: str = Field(..., description="Plain-language explanation of provision")
    why_relevant: str = Field(..., description="Why this section relates to user's case")
    cautious_framing: str = Field(
        "Potentially relevant provision. Does not establish definitive liability or violation.",
        description="Legal qualification"
    )
    snippet: Optional[str] = Field(None, description="Statutory text excerpt")


class CaseLegalAnalysis(BaseModel):
    case_id: int
    case_category: str
    legal_domain: str
    ranked_provisions: List[RankedLegalProvision] = Field(default_factory=list)
    total_provisions_found: int = 0
    disclaimer: str = Field(
        "Legal provisions are retrieved from official statutory sources for decision support and do not constitute formal legal counsel."
    )


# -------------------------------------------------------------
# 3. CASE ACTION PLAN
# -------------------------------------------------------------
class CaseActionItem(BaseModel):
    action_id: str
    action_title: str
    description: str
    priority: str = Field("Normal", description="Immediate, High, Normal, or Optional")
    category: str = Field("General", description="Preservation, Evidence, Administrative, or Filing")
    statutory_basis: Optional[str] = None


class CaseActionPlan(BaseModel):
    case_id: int
    immediate_actions: List[CaseActionItem] = Field(default_factory=list)
    recommended_next_steps: List[CaseActionItem] = Field(default_factory=list)
    optional_supporting_actions: List[CaseActionItem] = Field(default_factory=list)
    guidance_note: str = Field(
        "Actions are tailored to the current case description and standard statutory procedures."
    )


# -------------------------------------------------------------
# 4. DOCUMENT & EVIDENCE CHECKLIST
# -------------------------------------------------------------
class CaseDocumentItem(BaseModel):
    document_id: str
    title: str
    description: str
    importance: str = Field("Important", description="Required, Important, or Supporting")
    purpose: str = Field(..., description="Role in substantiating claim or complaint")
    statutory_reference: Optional[str] = None
    is_digital_evidence: bool = False
    evidence_safeguard: Optional[str] = None


class CaseDocumentChecklist(BaseModel):
    case_id: int
    required_documents: List[CaseDocumentItem] = Field(default_factory=list)
    important_documents: List[CaseDocumentItem] = Field(default_factory=list)
    supporting_documents: List[CaseDocumentItem] = Field(default_factory=list)
    bsa_evidence_note: str = Field(
        "Under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023, electronic records (photos, videos, chats) require certification when produced as evidence in court proceedings."
    )


# -------------------------------------------------------------
# 5. FURTHER PROCEDURE
# -------------------------------------------------------------
class ProcedureStepItem(BaseModel):
    step_number: int
    stage_name: str
    authority_involved: str
    description: str
    expected_timeline: Optional[str] = None
    safeguards: List[str] = Field(default_factory=list)


class CaseFurtherProcedure(BaseModel):
    case_id: int
    legal_domain: str
    procedural_pathway: List[ProcedureStepItem] = Field(default_factory=list)
    overall_timeline: Optional[str] = None
    statutory_source: Optional[str] = None
    procedural_note: str = Field(
        "Depending on the applicable procedure, the concerned authority may verify the complaint, examine relevant records, and seek an explanation from the parties involved."
    )


# -------------------------------------------------------------
# 6. EMOTIONAL STATE ANALYSIS & ADAPTIVE GUIDANCE
# -------------------------------------------------------------
class CaseEmotionalAnalysis(BaseModel):
    case_id: int
    detected_indicators: List[str] = Field(default_factory=list, description="Fear, Anxiety, Anger, Frustration, Confusion, Distress, Urgency, Sadness, Neutral/Calm")
    primary_tone: str = Field("Neutral/Calm")
    urgency_level: str = Field("Medium", description="Low, Medium, High, or Critical")
    communication_adaptation: str = Field(..., description="How Vidhik adapts language based on emotional indicators")
    safety_indicators_present: bool = False
    immediate_safety_notice: Optional[str] = None
    disclaimer: str = Field(
        "This assessment identifies language patterns in the submitted text to optimize communication clarity. It does not constitute psychological, medical, or diagnostic evaluation."
    )


# -------------------------------------------------------------
# 7. DATABASE-DRIVEN LAWYER RECOMMENDATION
# -------------------------------------------------------------
class MatchedLawyerProfile(BaseModel):
    lawyer_id: int
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    bar_council_number: Optional[str] = None
    specialization: str
    experience_years: Optional[int] = None
    court_practice: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    office_address: Optional[str] = None
    is_verified: bool = True
    is_available: bool = True
    match_score: float = Field(..., description="Deterministic matching score (0 to 100)")
    matched_specializations: List[str] = Field(default_factory=list)
    matched_jurisdictions: List[str] = Field(default_factory=list)
    match_reason: str = Field(..., description="Explicit reason why lawyer matches this case")


class CaseLawyerRecommendation(BaseModel):
    case_id: int
    case_category: str
    legal_domain: str
    required_expertise: List[str] = Field(default_factory=list)
    jurisdiction: Optional[str] = None
    recommended_lawyers: List[MatchedLawyerProfile] = Field(default_factory=list)
    total_lawyers_matched: int = 0
    disclaimer: str = Field(
        "Lawyer recommendations are generated by deterministic matching against registered advocate profiles in the Vidhik database. Vidhik does not endorse specific practitioners."
    )


# -------------------------------------------------------------
# 8. AUTHORITY RECOMMENDATION
# -------------------------------------------------------------
class CaseAuthorityItem(BaseModel):
    authority_name: str
    authority_type: str = Field(..., description="Tribunal, Regulatory Authority, Police Grievance Cell, Judicial Court, or Consumer Commission")
    jurisdiction_level: str = Field("District", description="District, State, or National")
    role_in_case: str
    filing_channel: Optional[str] = None
    relevant_act: Optional[str] = None


class CaseAuthorityRecommendation(BaseModel):
    case_id: int
    primary_authorities: List[CaseAuthorityItem] = Field(default_factory=list)
    precedent_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    source_status: str = Field("SOURCE_VERIFIED")


# -------------------------------------------------------------
# 9. CENTRAL COMPLETE CASE CONTEXT (FEATURE 10)
# -------------------------------------------------------------
class CentralCaseContext(BaseModel):
    context_id: int
    case_id: int
    user_id: int
    title: str
    original_description: str
    normalized_description: Optional[str] = None
    situation_summary: str
    extracted_facts: List[str] = Field(default_factory=list)
    explicit_facts: List[str] = Field(default_factory=list)
    identified_issues: List[str] = Field(default_factory=list)
    uncertain_facts: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    case_category: str
    legal_domain: str
    jurisdiction: Optional[str] = None
    urgency: str = "Medium"
    status: str = "active"
    analysis_version: int = 1

    # Integrated Modules
    emotional_indicators: Dict[str, Any] = Field(default_factory=dict)
    ranked_provisions: List[RankedLegalProvision] = Field(default_factory=list)
    recommended_authorities: List[CaseAuthorityItem] = Field(default_factory=list)
    recommended_lawyers: List[MatchedLawyerProfile] = Field(default_factory=list)
    recommended_actions: Dict[str, Any] = Field(default_factory=dict)
    required_documents: Dict[str, Any] = Field(default_factory=dict)
    further_procedure: Dict[str, Any] = Field(default_factory=dict)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# -------------------------------------------------------------
# 10. REQUEST MODELS
# -------------------------------------------------------------
class CaseCreateAndAnalyzeRequest(BaseModel):
    title: Optional[str] = None
    description: str = Field(..., min_length=5, description="Natural language legal problem description")
    case_type: Optional[str] = None
    court_name: Optional[str] = None
    incident_date: Optional[date] = None
    location: Optional[str] = None
    police_station: Optional[str] = None
    opposite_party: Optional[str] = None


class CaseUpdateAndReanalyzeRequest(BaseModel):
    additional_information: str = Field(..., min_length=3, description="New factual statements to incorporate")
    updated_location: Optional[str] = None
    updated_incident_date: Optional[date] = None
    updated_opposite_party: Optional[str] = None


class ActiveCaseResponse(BaseModel):
    active_case_id: Optional[int] = None
    case: Optional[Dict[str, Any]] = None
    context: Optional[CentralCaseContext] = None
