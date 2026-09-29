"""
Vidhik Platform - Judicial Authority & Case-Law Recommendation Schemas
======================================================================
Defines read-only Pydantic models for deterministic judicial authority
recommendations grounded strictly in verified project records.
Guarantees zero hallucination: never generates or invents citations or cases.
"""

from typing import Optional, List, Any
from datetime import date
from pydantic import BaseModel, Field


class LinkedSectionInfo(BaseModel):
    """Details of a statutory provision linked to an authoritative judgment."""
    law_name: str
    section_number: str
    relationship_type: str = "Interpreted"
    relevance: str = "Direct"
    explanation: Optional[str] = None


class AuthorityResult(BaseModel):
    """
    Structured judicial authority recommendation item.
    Provenance and verification status are strictly preserved.
    """
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
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_type: str  # e.g., 'exact_section_mapping', 'law_section_relationship', 'legal_proposition_match', 'concept_match', 'context_match'
    reason: str
    source: str = "Supreme Court of India Official Repository"
    verification_status: str = "verified"  # "verified" or "NOT IN SOURCE"


class AuthorityRecommendationResponse(BaseModel):
    """
    API response model for authority recommendations.
    Clearly separates statutory context, ranked authorities, and verification status.
    """
    query: Optional[str] = None
    law_id: Optional[int] = None
    section_number: Optional[str] = None
    total: int = 0
    source_status: str = "verified"  # "verified", "NOT IN SOURCE", "NO MATCH"
    recommendations: List[AuthorityResult] = Field(default_factory=list)
    statutory_results: List[dict] = Field(default_factory=list)
