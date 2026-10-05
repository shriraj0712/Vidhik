from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LegalClassificationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="Legal query or factual description to classify")
    language: Optional[str] = Field("en", description="Query language code (en, hi, mr)")


class AreaScore(BaseModel):
    category: str = Field(..., description="Legal category identifier")
    score: float = Field(..., description="Relevance score (0.0 to 1.0)")
    matched_terms: List[str] = Field(default_factory=list, description="Matched keywords/concepts")
    applicable_acts: List[str] = Field(default_factory=list, description="Candidate Bare Acts for this category")


class LegalClassificationResponse(BaseModel):
    category: str = Field(..., description="Primary legal domain identified")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    matched_terms: List[str] = Field(default_factory=list, description="Key matched legal keywords")
    possible_legal_areas: List[AreaScore] = Field(default_factory=list, description="All evaluated candidate legal areas")
    requires_more_information: bool = Field(False, description="True if query is too brief, ambiguous, or lacks factual grounding")
    explanation: str = Field(..., description="Citizen-friendly explanation of classification reasoning")
    candidate_acts: List[str] = Field(default_factory=list, description="Recommended Bare Acts to consult")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic and latency metadata")
