from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ConstitutionalAnalysisRequest(BaseModel):
    facts: str = Field(..., min_length=5, max_length=5000, description="Factual scenario or inquiry involving state action or fundamental rights")
    language: Optional[str] = Field("en", description="Preferred language code (en, hi, mr)")


class ConstitutionalRightMatch(BaseModel):
    article: str = Field(..., description="Constitutional Article number (e.g., 'Article 21')")
    title: str = Field(..., description="Title of the Constitutional Article")
    category: str = Field(..., description="Right category (e.g. Life & Personal Liberty, Equality, Arrest Safeguards, Writ Remedies)")
    citizen_explanation: str = Field(..., description="Plain-language explanation of how this right protects citizens")
    relevance_to_facts: str = Field(..., description="Factual connection explaining why this right is potentially engaged")
    key_doctrines: List[str] = Field(default_factory=list, description="Established judicial doctrines (e.g. Due Process, Proportionality, Maneka Gandhi)")
    remedy_available: str = Field(..., description="Constitutional remedy path (e.g., Writ under Article 32 / 226)")


class ConstitutionalAnalysisResponse(BaseModel):
    is_state_action_involved: bool = Field(..., description="Whether facts suggest public authority/government/police action")
    primary_rights_engaged: List[ConstitutionalRightMatch] = Field(default_factory=list, description="Potentially engaged Fundamental Rights")
    recommended_remedies: List[str] = Field(default_factory=list, description="Available procedural and writ remedies")
    summary_analysis: str = Field(..., description="Citizen-facing synthesis of constitutional protections")
    disclaimer: str = Field(
        default="Constitutional analysis is for informational and educational purposes. A writ petition or constitutional challenge requires formal evaluation by an Advocate or Senior Counsel.",
        description="Mandatory constitutional disclaimer"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and latency info")
