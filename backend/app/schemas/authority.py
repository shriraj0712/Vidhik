from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AuthorityRecommendationRequest(BaseModel):
    issue_description: str = Field(..., min_length=3, max_length=5000, description="Legal issue or grievance description")
    category: Optional[str] = Field(None, description="Optional category (criminal, cyber, consumer, rti, labour, tenancy, banking, property, etc.)")
    state_or_ut: Optional[str] = Field("All India", description="State or Union Territory for jurisdiction routing")
    is_urgent: bool = Field(False, description="Whether immediate intervention is needed")


class AuthorityDetail(BaseModel):
    name: str = Field(..., description="Official name of the authority / body")
    authority_type: str = Field(..., description="Quasi-judicial, Judicial, Regulatory, Administrative, Law Enforcement")
    jurisdiction_level: str = Field(..., description="District, State, National, Specialized")
    official_portal: Optional[str] = Field(None, description="Official government web portal / filing system")
    statutory_basis: str = Field(..., description="Governing statute or enabling legal provision")
    filing_procedure: str = Field(..., description="Standard procedure for submitting grievance/complaint")


class AuthorityRecommendationResponse(BaseModel):
    primary_authority: AuthorityDetail = Field(..., description="Most appropriate primary statutory authority")
    alternative_authorities: List[AuthorityDetail] = Field(default_factory=list, description="Appellate or alternate grievance bodies")
    reasoning: str = Field(..., description="Why this authority is recommended")
    confidence: float = Field(..., description="Recommendation confidence score (0.0 to 1.0)")
    escalation_hierarchy: List[str] = Field(default_factory=list, description="Step-by-step statutory escalation path")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and latency info")
