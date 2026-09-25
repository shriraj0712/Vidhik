"""
Vidhik Platform - Services Layer Module
=======================================
Unified export of business logic services across statutory search,
relevance ranking, terminology analysis, RAG pipeline, AI legal assistant,
documentation support, document analysis, lawyer workspace, citizen portal,
and authentication & security services.
"""

from .search_service import LegalSearchService
from .query_service import LegalQueryService
from .ranking_service import LegalRankingService
from .context_builder import LegalContextBuilder
from .rag_service import LegalRAGService
from .llm_provider import BaseLLMProvider, get_llm_provider
from .assistant_service import (
    LegalAssistantService,
    BaseConversationStore,
    InMemoryConversationStore,
    ConversationContextHandler,
    get_conversation_store
)
from .documentation_service import DocumentationService
from .document_parser_service import DocumentParserService
from .document_analysis_service import DocumentAnalysisService
from .lawyer_service import LawyerService
from .citizen_service import CitizenService
from .auth_service import (
    AuthService,
    get_authenticated_user,
    get_current_user,
    get_optional_user,
    require_citizen,
    require_lawyer,
    require_admin
)

__all__ = [
    # Statutory Core (Phases 1-8)
    "LegalSearchService",
    "LegalQueryService",
    "LegalRankingService",
    # RAG & Assistant (Phases 9-10)
    "LegalContextBuilder",
    "LegalRAGService",
    "BaseLLMProvider",
    "get_llm_provider",
    "LegalAssistantService",
    "BaseConversationStore",
    "InMemoryConversationStore",
    "ConversationContextHandler",
    "get_conversation_store",
    # Documentation & Analysis (Phases 11-12)
    "DocumentationService",
    "DocumentParserService",
    "DocumentAnalysisService",
    # Role Workspaces (Phases 13-14)
    "LawyerService",
    "CitizenService",
    # Auth & Security (Phases 13-15)
    "AuthService",
    "get_authenticated_user",
    "get_current_user",
    "get_optional_user",
    "require_citizen",
    "require_lawyer",
    "require_admin"
]
