from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ElementVerificationRequest(BaseModel):
    facts: str = Field(..., min_length=5, max_length=10000, description="Factual narrative to verify against statutory elements")
    provision: Optional[str] = Field(None, description="Target provision to test (e.g. 'theft', 'cheating', 'criminal_intimidation', 'cheque_bounce', 'cyber_fraud', 'defamation')")
    act_name: Optional[str] = Field(None, description="Optional Act name (e.g. 'Bharatiya Nyaya Sanhita, 2023')")


class ElementMatch(BaseModel):
    element_name: str = Field(..., description="Statutory element requirement")
    is_present: bool = Field(..., description="Whether the factual narrative provides evidence for this element")
    matched_facts: List[str] = Field(default_factory=list, description="Specific factual phrases supporting the element")
    significance: str = Field(..., description="Why this element is required under the statute")


class ElementVerificationResponse(BaseModel):
    provision_name: str = Field(..., description="Legal provision evaluated")
    act_name: str = Field(..., description="Statutory Act")
    section_reference: str = Field(..., description="Section number or citation")
    verification_status: str = Field(..., description="supported, partially_supported, insufficient_facts, not_supported")
    required_elements: List[str] = Field(default_factory=list, description="All elements required by statute")
    element_evaluations: List[ElementMatch] = Field(default_factory=list, description="Detailed per-element analysis")
    missing_elements: List[str] = Field(default_factory=list, description="Elements not substantiated by current narrative")
    factual_analysis: str = Field(..., description="Objective analysis of facts in relation to statutory requirements")
    disclaimer: str = Field(
        default="This analysis assesses factual correspondence with statutory elements for informational purposes only. It is not a determination of guilt, liability, or official police/judicial finding.",
        description="Statutory non-adjudication disclaimer"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and diagnostic info")
