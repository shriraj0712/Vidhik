from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IntentRoutingRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000, description="User query to route")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional conversational context")


class IntentRoutingResponse(BaseModel):
    intent: str = Field(..., description="Recognized primary intent")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    suggested_target_service: str = Field(..., description="Internal service recommended for this intent")
    suggested_api_endpoint: str = Field(..., description="REST API endpoint suited for this request")
    matched_triggers: List[str] = Field(default_factory=list, description="Keywords/patterns that triggered the intent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Routing metadata")
