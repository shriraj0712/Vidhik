"""
Vidhik Platform - AI Legal Assistant Schemas
=============================================
Pydantic models for natural-language legal assistant interactions,
conversation history, follow-up context management, and grounded responses.
"""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rag import (
    LegalSourceCitation,
    RetrievedSectionContext,
    RetrievalMetadata
)


class ChatMessage(BaseModel):
    """
    Individual turn within an assistant conversation history.
    """
    model_config = ConfigDict(from_attributes=True)

    role: str = Field(
        ...,
        description="Role of the message sender: 'user' or 'assistant'"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Text content of the message"
    )


class AssistantChatRequest(BaseModel):
    """
    Request payload for the AI Legal Assistant chat endpoint.
    Supports single queries, session continuity via conversation_id,
    and stateless conversation history arrays.
    """
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(
        ...,
        min_length=1,
        description="User's natural-language legal question or follow-up prompt"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional session / conversation UUID. If omitted, a new UUID is generated."
    )
    history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Optional prior conversation turns for follow-up resolution"
    )
    language: Optional[str] = Field(
        default="en",
        description="Preferred response language: 'en' (English), 'mr' (Marathi), 'hi' (Hindi)"
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Optional statutory jurisdiction filter (e.g. 'India', 'Maharashtra')"
    )
    law_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Optional parent statute filter"
    )
    max_sections: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of authoritative statutory sections to include in retrieval context"
    )
    temperature: Optional[float] = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Generation temperature (low value ensures deterministic, factual adherence)"
    )


class AssistantChatResponse(BaseModel):
    """
    Authoritative, grounded AI legal assistant response with citations and metadata.
    """
    model_config = ConfigDict(from_attributes=True)

    conversation_id: str = Field(
        description="Unique conversation or session identifier"
    )
    message: str = Field(
        description="The user's original question or follow-up message"
    )
    answer: str = Field(
        description="Assistant answer strictly grounded in verified statutory law"
    )
    language: str = Field(
        description="Language of the generated response ('en', 'mr', 'hi')"
    )
    grounding_status: str = Field(
        description="Grounding status: 'grounded_high', 'grounded_medium', 'insufficient_context', 'no_context', 'synthesis_failed'"
    )
    confidence: str = Field(
        description="Grounding confidence level, identical to grounding_status for compatibility"
    )
    is_grounded: bool = Field(
        description="Boolean indicating whether answer is anchored to verified statutory text"
    )
    sources: List[LegalSourceCitation] = Field(
        default_factory=list,
        description="Traceable statutory citations from the database"
    )
    retrieved_sections: List[RetrievedSectionContext] = Field(
        default_factory=list,
        description="Authoritative statutory provisions retrieved and evaluated"
    )
    retrieval_metadata: Optional[RetrievalMetadata] = Field(
        default=None,
        description="Audit telemetry of query analysis, lexicon matching, and ranking"
    )
    disclaimer: str = Field(
        default=(
            "This legal assistant provides informational and research support grounded in Indian statutory law "
            "from the Vidhik legal database. It does not constitute formal legal advice or substitute for consultation "
            "with a qualified legal professional."
        ),
        description="Mandatory legal information disclaimer"
    )
