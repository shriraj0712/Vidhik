from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SafetyCheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=15000, description="Input text to scan for safety violations")
    context: Optional[str] = Field(None, max_length=5000, description="Optional conversation or document context")
    strict_mode: bool = Field(True, description="Enable strict multi-category safety auditing")


class SafetyViolation(BaseModel):
    category: str = Field(..., description="Safety category violated")
    description: str = Field(..., description="Human-readable description of violation")
    severity: str = Field(..., description="Severity level: high, medium, low")
    matched_patterns: List[str] = Field(default_factory=list, description="Sanitized pattern identifiers triggered")


class SafetyCheckResponse(BaseModel):
    is_safe: bool = Field(..., description="True if text passed all safety checks")
    risk_level: str = Field(..., description="Overall risk level: safe, low, medium, high, critical")
    violations: List[SafetyViolation] = Field(default_factory=list, description="Detected safety violations")
    contains_pii: bool = Field(False, description="True if PII was detected")
    sanitized_text: Optional[str] = Field(None, description="Redacted or sanitized text if PII was scrubbed")
    blocked_reason: Optional[str] = Field(None, description="Explanation if content is blocked")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic and latency metadata")
