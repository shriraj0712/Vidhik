from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EmergencyEvaluationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="User narrative or legal query to evaluate for emergency risk")
    language: Optional[str] = Field("en", description="Preferred language code (en, hi, mr)")


class HelplineInfo(BaseModel):
    name: str = Field(..., description="Service or agency name")
    number: str = Field(..., description="Emergency contact number")
    description: str = Field(..., description="Purpose of helpline")


class EmergencyEvaluationResponse(BaseModel):
    is_emergency: bool = Field(..., description="True if an active emergency or immediate threat is detected")
    urgency_level: str = Field(..., description="Urgency classification: critical, high, moderate, none")
    emergency_type: Optional[str] = Field(None, description="Category of emergency (e.g. physical_danger, domestic_violence, cyber_financial, child_endangerment)")
    immediate_actions: List[str] = Field(default_factory=list, description="Immediate safety steps to take")
    verified_helplines: List[HelplineInfo] = Field(default_factory=list, description="Verified emergency contact numbers")
    escalation_message: Optional[str] = Field(None, description="Citizen-facing emergency banner / guidance")
    can_proceed_with_legal_assistance: bool = Field(True, description="Whether general legal information can also be provided safely")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata and latency")
