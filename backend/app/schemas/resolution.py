"""
Vidhik Platform - Legal Resolution Decision Engine Schemas
===========================================================
Pydantic validation and response serialization models for:
- Citizen legal triage & recommendation (Self-Resolvable vs Lawyer vs Urgent)
- Deterministic risk assessment and machine-readable triggered rules
- Step-by-step self-help checklists, verified procedure references, and safety guidance
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class RecommendationType(str, Enum):
    """Primary outcome of legal resolution triage."""
    SELF_RESOLVABLE = "self_resolvable"
    LAWYER_CONSULTATION_REQUIRED = "lawyer_consultation_required"
    URGENT_LEGAL_INTERVENTION = "urgent_legal_intervention"


class RiskLevel(str, Enum):
    """Categorical legal and physical safety risk level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TriggeredRuleInfo(BaseModel):
    """Machine-readable metadata for a deterministic rule that fired during evaluation."""
    model_config = ConfigDict(from_attributes=True)

    rule_id: str = Field(description="Unique deterministic rule identifier")
    category: str = Field(description="Rule domain category (e.g. 'Urgent', 'Criminal', 'Property', 'RTI')")
    rule_description: str = Field(description="Human-readable explanation of why the rule triggered")
    severity: str = Field(description="Rule severity level: 'critical', 'high', 'medium', 'low'")


class RelevantProcedureRef(BaseModel):
    """Reference to a verified citizen procedural guide from Phase 12/16."""
    model_config = ConfigDict(from_attributes=True)

    procedure_id: Optional[int] = Field(default=None, description="Database ID of the procedure if available")
    procedure_name: str = Field(description="Official title of the legal procedure")
    procedure_slug: str = Field(description="URL-safe slug for the procedure")
    category: str = Field(description="Procedure classification category")
    authority_type: str = Field(description="Competent administrative authority or nodal department")
    estimated_days: Optional[int] = Field(default=None, description="Statutory estimated processing timeline in days")
    portal_url: Optional[str] = Field(default=None, description="Official government filing portal URL")
    required_documents_count: int = Field(default=0, description="Number of prerequisite documents needed")


class ResolutionEvaluationRequest(BaseModel):
    """
    Request payload for the Legal Resolution Decision Engine.
    Operates from a natural-language legal narrative with optional structured signals.
    """
    model_config = ConfigDict(from_attributes=True)

    situation: str = Field(
        ...,
        min_length=3,
        description="Natural-language description of the legal problem, incident, or dispute."
    )
    issue_category: Optional[str] = Field(
        default=None,
        description="Optional category hint (e.g. 'Criminal', 'Family', 'Consumer', 'Property', 'RTI', 'Traffic')"
    )
    jurisdiction: Optional[str] = Field(
        default="India",
        description="Jurisdiction / State (default: 'India')"
    )
    monetary_amount: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Estimated monetary value, claim amount, or financial exposure in INR (₹)"
    )

    # Optional Structured Boolean Signals
    has_police_involvement: Optional[bool] = Field(
        default=None,
        description="Whether police have registered an FIR, called for questioning, or issued notice"
    )
    has_court_notice: Optional[bool] = Field(
        default=None,
        description="Whether a formal summons, court notice, or legal notice has been received"
    )
    has_arrest_threat: Optional[bool] = Field(
        default=None,
        description="Whether there is imminent threat of arrest or custodial detention"
    )
    is_physical_danger: Optional[bool] = Field(
        default=None,
        description="Whether immediate physical danger, assault, or threat to life exists"
    )
    involves_children: Optional[bool] = Field(
        default=None,
        description="Whether minor children are involved, abused, or subject to custody dispute"
    )
    involves_domestic_violence: Optional[bool] = Field(
        default=None,
        description="Whether active domestic violence, dowry harassment, or physical abuse is present"
    )
    has_urgent_deadline: Optional[bool] = Field(
        default=None,
        description="Whether an urgent statutory filing or limitation deadline exists (< 7 days)"
    )
    language: Optional[str] = Field(
        default="en",
        description="Preferred language for explanations and checklist: 'en' (English), 'mr' (Marathi), 'hi' (Hindi)"
    )


class ResolutionEvaluationResponse(BaseModel):
    """
    Deterministic triage decision, risk evaluation, and step-by-step guidance response.
    """
    model_config = ConfigDict(from_attributes=True)

    recommendation_type: RecommendationType = Field(
        description="Triage outcome: 'self_resolvable', 'lawyer_consultation_required', or 'urgent_legal_intervention'"
    )
    risk_level: RiskLevel = Field(
        description="Overall legal and safety risk level: 'low', 'medium', 'high', 'critical'"
    )
    primary_reason: str = Field(
        description="Concise, clear explanation of why this recommendation was reached"
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="All contributing legal, procedural, and factual factors"
    )
    triggered_rules: List[TriggeredRuleInfo] = Field(
        default_factory=list,
        description="Machine-readable rule identifiers that fired during evaluation"
    )
    self_help_checklist: List[str] = Field(
        default_factory=list,
        description="Step-by-step actionable checklist (for self-resolvable matters or preliminary prep)"
    )
    lawyer_specialization_needed: Optional[str] = Field(
        default=None,
        description="Recommended legal practice domain (e.g. 'Criminal Defense & Bail', 'Family & Matrimonial')"
    )
    applicable_areas: List[str] = Field(
        default_factory=list,
        description="Legal domains and governing statutory frameworks involved"
    )
    next_steps: List[str] = Field(
        default_factory=list,
        description="Immediate advised course of action"
    )
    emergency_guidance: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Emergency helplines and immediate protective measures if urgent"
    )
    relevant_procedures: List[RelevantProcedureRef] = Field(
        default_factory=list,
        description="Cross-referenced VIDHIK procedure guides from Phase 12/16"
    )
    confidence: str = Field(
        default="high",
        description="Evaluation certainty: 'high', 'medium', or 'cautious_fallback'"
    )
    disclaimer: str = Field(
        default=(
            "This automated resolution assessment is for informational and educational triage only and does not "
            "constitute formal legal advice or create an attorney-client relationship. If in doubt, consult a licensed advocate."
        ),
        description="Mandatory legal disclaimer"
    )
