"""
Vidhik Platform - Case Intelligence Pydantic Schemas
=====================================================
Defines generic, extensible data structures for dynamic case understanding,
fact extraction, multi-issue identification, legal provision ranking,
authority matching, lawyer recommendation, action planning, document checklists,
further procedural stages, emotional indicators, and persistent case contexts.

Strictly avoids hardcoded case type flags or category enums.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FactItem(BaseModel):
    """Structured fact extracted dynamically from natural language."""
    fact: str = Field(..., description="Statement of extracted factual circumstance")
    entity_type: str = Field(..., description="Category of fact: party, event, monetary, instrument, date_time, digital, location, etc.")
    details: Optional[str] = Field(default=None, description="Additional contextual nuances")


class LegalIssue(BaseModel):
    """Dynamic legal issue identified within the user's matter."""
    issue_id: str = Field(..., description="Unique issue identifier, e.g. ISS-01")
    issue_type: str = Field(..., description="'primary' or 'additional'")
    title: str = Field(..., description="Succinct title of the legal issue")
    description: str = Field(..., description="Detailed description of the grievance/dispute")
    legal_concepts: List[str] = Field(default_factory=list, description="Extracted legal concepts/principles")
    potential_acts: List[str] = Field(default_factory=list, description="Potentially applicable statutes")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score for this issue")


class RankedLegalProvision(BaseModel):
    """Statutory provision matched and ranked deterministically against the case."""
    act_id: Optional[int] = Field(default=None, description="Statutory Act identifier")
    law_name: str = Field(..., description="Official title of the enactment")
    short_name: str = Field(..., description="Abbreviation, e.g. BNS, CPA, IT Act")
    section_number: str = Field(..., description="Statutory section or article number")
    section_title: str = Field(..., description="Heading or title of the section")
    relevance_score: float = Field(..., description="Deterministic relevance score")
    relevance_tier: int = Field(default=1, description="Deterministic priority tier (1-9)")
    explanation: str = Field(..., description="Human-readable justification of statutory relevance")
    snippet: Optional[str] = Field(default=None, description="Contextual excerpt of statutory text")
    is_offence: bool = Field(default=False)
    offence_name: Optional[str] = None
    bailable_status: Optional[str] = None
    cognizable_status: Optional[str] = None
    punishment_summary: Optional[str] = None
    procedure_summary: Optional[str] = None
    evidence_summary: Optional[str] = None


class AuthorityRecommendation(BaseModel):
    """Statutory authority, tribunal, commission, or forum applicable to the case."""
    authority_name: str = Field(..., description="Official name of the authority or forum")
    authority_type: str = Field(..., description="Court, Tribunal, Commission, Police, Regulatory, or Legal Aid")
    jurisdiction: str = Field(default="Central / Territorial", description="Jurisdictional competency")
    role: str = Field(..., description="Role in redressal, investigation, or adjudication")
    relevance_reason: str = Field(..., description="Why this authority is relevant to the matter")
    is_primary_recourse: bool = Field(default=False, description="True if this is the most direct first forum")


class LawyerRequirement(BaseModel):
    """Derived legal expertise requirements for lawyer matching."""
    domain: str = Field(..., description="Legal practice domain")
    required_expertise: List[str] = Field(default_factory=list, description="Specific specializations needed")
    priority: str = Field(default="high", description="Urgency/priority: immediate, high, medium")


class LawyerMatch(BaseModel):
    """Advocate or legal aid organization matched to the case requirements."""
    lawyer_id: Optional[int] = None
    full_name: str
    specializations: List[str] = Field(default_factory=list)
    experience_years: int = 0
    city: str = ""
    match_score: float = 0.0
    match_reason: str = ""
    is_legal_aid: bool = False
    contact_email: Optional[str] = None


class CaseAction(BaseModel):
    """Case-specific actionable recommendation step."""
    step: int = Field(..., description="Sequence number")
    action: str = Field(..., description="Action title or command")
    target_entity_or_authority: Optional[str] = Field(default=None, description="Target party or authority")
    urgency: str = Field(default="short_term", description="immediate, short_term, or procedural")
    description: str = Field(..., description="Concrete instruction and rationale")


class DocumentRequirementItem(BaseModel):
    """Dynamic document or evidentiary item required for the case."""
    document_name: str = Field(..., description="Name or description of the document/evidence")
    purpose: str = Field(..., description="Statutory purpose or role in proof")
    mandatory: bool = Field(default=True, description="True if essential to sustain the claim/complaint")
    source_provision: Optional[str] = Field(default=None, description="Statute or rule mandating it (e.g. BSA Sec 63)")


class FurtherProcedureStage(BaseModel):
    """Procedural stage explaining 'What happens next?'."""
    stage_number: int
    stage_name: str
    forum_or_authority: str
    description: str
    expected_timeline_or_outcome: Optional[str] = None


class EmotionalIndicator(BaseModel):
    """Emotional indicator detected from user's natural language."""
    emotion: str = Field(..., description="fear, anger, confusion, distress, frustration, urgency, sadness, or calm_neutral")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    detected_cues: List[str] = Field(default_factory=list, description="Specific words or phrases indicating emotion")
    communication_guidance: str = Field(..., description="Tone advice to reassure and guide the user")


class MissingInformation(BaseModel):
    """Clarification query when case context has gaps or uncertainties."""
    aspect: str = Field(..., description="Missing factual or legal dimension")
    question: str = Field(..., description="Clarifying question for the user")
    why_needed: str = Field(..., description="How this enables precise statutory grounding")


class CaseContext(BaseModel):
    """
    Generalized Case Context
    ========================
    Unified, extensible representation of an ongoing legal case in Vidhik.
    Zero hardcoded case-type flags. Works dynamically for ANY legal matter.
    """
    case_id: str = Field(..., description="Unique case identifier, e.g. CASE-001")
    original_description: str = Field(..., description="Raw user input in natural language")
    normalized_description: str = Field(..., description="Cleaned, normalized description")
    facts: List[FactItem] = Field(default_factory=list, description="Extracted factual elements")
    issues: List[LegalIssue] = Field(default_factory=list, description="Identified legal issues (primary & additional)")
    legal_domains: List[str] = Field(default_factory=list, description="Dynamically identified legal practice domains")
    jurisdiction: str = Field(default="India / Central", description="Applicable legal jurisdiction")
    legal_matches: List[Dict[str, Any]] = Field(default_factory=list, description="Raw statutory search matches")
    ranked_provisions: List[RankedLegalProvision] = Field(default_factory=list, description="Deterministically ranked legal provisions")
    authorities: List[AuthorityRecommendation] = Field(default_factory=list, description="Applicable statutory forums and authorities")
    lawyer_requirements: List[LawyerRequirement] = Field(default_factory=list, description="Derived lawyer expertise needs")
    lawyer_matches: List[LawyerMatch] = Field(default_factory=list, description="Matched lawyers or legal aid options")
    authority_preferred_over_lawyer: bool = Field(default=False, description="True if direct statutory authority recourse is more appropriate than hiring an advocate")
    authority_preference_reason: Optional[str] = Field(default=None, description="Explanation for authority preference")
    actions: List[CaseAction] = Field(default_factory=list, description="Tailored action plan")
    documents: List[DocumentRequirementItem] = Field(default_factory=list, description="Dynamic evidence & document checklist")
    procedure: List[FurtherProcedureStage] = Field(default_factory=list, description="Procedural roadmap ('What happens next?')")
    emotional_indicators: List[EmotionalIndicator] = Field(default_factory=list, description="Emotional indicators and communication cues")
    urgency: str = Field(default="medium", description="critical, high, medium, or low")
    missing_information: List[MissingInformation] = Field(default_factory=list, description="Clarifying questions needed")
    status: str = Field(default="analyzed", description="analyzed, pending_clarification, resolved, or active")
    confidence_overall: float = Field(default=0.85, ge=0.0, le=1.0)
    degree_of_relevance: str = Field(default="Substantially relevant", description="Degree of statutory match")
    is_uncertain: bool = Field(default=False, description="True if classification is tentative/uncommon")
    sufficient_information: bool = Field(default=True, description="True if input has sufficient factual basis")
    unavailability_notice: Optional[str] = Field(default=None, description="Notice if database has insufficient grounding")
    explanation: str = Field(default="", description="Empathetic, plain-language legal explanation")
    created_at: str = Field(default="")
    updated_at: str = Field(default="")


class CaseAnalyzeRequest(BaseModel):
    """Payload to analyze a new or updated case in natural language."""
    description: str = Field(..., min_length=1, description="Natural language description of the legal problem")
    case_id: Optional[str] = Field(default=None, description="Optional custom case ID or existing case ID")
    jurisdiction_hint: Optional[str] = Field(default=None, description="Optional city, state, or court hint")


class CaseClarificationRequest(BaseModel):
    """Payload to clarify an existing case context."""
    clarification_text: str = Field(..., min_length=1, description="Additional facts or clarifications provided by user")
    answers: Optional[Dict[str, str]] = Field(default=None, description="Key-value answers to missing information questions")


class CaseSwitchResponse(BaseModel):
    """Response confirming switch of persistent current case."""
    success: bool
    current_case_id: str
    message: str
    case_summary: Optional[Dict[str, Any]] = None
