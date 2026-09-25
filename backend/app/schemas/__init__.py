"""
Vidhik Platform - Pydantic Response & Request Schemas
"""

from .law import LawResponse, LawSummaryResponse, LawListResponse
from .section import SectionResponse, SectionSummaryResponse, SectionListResponse
from .search import SearchResponse, SearchResultItem
from .query import LegalQueryAnalysis, MatchedTerm, MatchedConcept, MatchedSynonym
from .rag import (
    LegalSourceCitation,
    RetrievedSectionContext,
    RetrievalMetadata,
    RAGQueryRequest,
    RAGResponse
)
from .assistant import (
    ChatMessage,
    AssistantChatRequest,
    AssistantChatResponse
)

__all__ = [
    "LawResponse",
    "LawSummaryResponse",
    "LawListResponse",
    "SectionResponse",
    "SectionSummaryResponse",
    "SectionListResponse",
    "SearchResponse",
    "SearchResultItem",
    "LegalQueryAnalysis",
    "MatchedTerm",
    "MatchedConcept",
    "MatchedSynonym",
    "LegalSourceCitation",
    "RetrievedSectionContext",
    "RetrievalMetadata",
    "RAGQueryRequest",
    "RAGResponse",
    "ChatMessage",
    "AssistantChatRequest",
    "AssistantChatResponse"
]


