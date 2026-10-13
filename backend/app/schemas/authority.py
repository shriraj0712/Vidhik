from typing import List, Optional, Dict, Any
from datetime import date

from pydantic import BaseModel, Field


class AuthorityRecommendationRequest(BaseModel):
    issue_description: str = Field(
        ..., min_length=3, max_length=5000,
        description="Legal issue or grievance description"
    )
    category: Optional[str] = Field(
        None, description="Optional legal category"
    )
    state_or_ut: Optional[str] = Field(
        "All India", description="State or Union Territory"
    )
    is_urgent: bool = Field(
        False, description="Whether immediate intervention is needed"
    )


class AuthorityDetail(BaseModel):
    name: str = Field(..., description="Official authority name")
    authority_type: str = Field(
        ..., description="Quasi-judicial, Judicial, Regulatory, Administrative, Law Enforcement"
    )
    jurisdiction_level: str = Field(
        ..., description="District, State, National, Specialized"
    )
    official_portal: Optional[str] = None
    statutory_basis: str
    filing_procedure: str


class StatutoryAuthorityRecommendationResponse(BaseModel):
    """Response for statutory authority recommendations."""
    primary_authority: AuthorityDetail
    alternative_authorities: List[AuthorityDetail] = Field(default_factory=list)
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    escalation_hierarchy: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LinkedSectionInfo(BaseModel):
    """Details of a statutory provision linked to a judgment."""
    law_name: str
    section_number: str
    relationship_type: str = "Interpreted"
    relevance: str = "Direct"
    explanation: Optional[str] = None


class AuthorityResult(BaseModel):
    """Verified judicial authority recommendation."""
    authority_id: int
    case_name: str
    court: str
    judgment_date: Optional[date] = None
    citation: Optional[str] = None
    legal_proposition: str
    linked_law_id: Optional[int] = None
    linked_law_name: Optional[str] = None
    linked_section_number: Optional[str] = None
    matched_sections: List[str] = Field(default_factory=list)
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    match_type: str
    reason: str
    source: str = "Supreme Court of India Official Repository"
    verification_status: str = "verified"


class JudicialAuthorityRecommendationResponse(BaseModel):
    """Response for verified judicial authority recommendations."""
    query: Optional[str] = None
    law_id: Optional[int] = None
    section_number: Optional[str] = None
    total: int = 0
    source_status: str = "verified"
    recommendations: List[AuthorityResult] = Field(default_factory=list)
    statutory_results: List[dict] = Field(default_factory=list)


# Backward compatibility for existing imports.
# In judicial context (routers/authorities and test_authority_recommendation), this maps to JudicialAuthorityRecommendationResponse.
AuthorityRecommendationResponse = JudicialAuthorityRecommendationResponse
