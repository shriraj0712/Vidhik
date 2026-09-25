"""
Vidhik Platform - Business & Query Services
===========================================
Dedicated service layer separating database access, business logic, and
query generation from FastAPI router endpoints.
"""

from .search_service import LegalSearchService
from .query_service import LegalQueryService
from .ranking_service import LegalRankingService
from .context_builder import LegalContextBuilder
from .rag_service import LegalRAGService
from .llm_provider import BaseLLMProvider, get_llm_provider

__all__ = [
    "LegalSearchService",
    "LegalQueryService",
    "LegalRankingService",
    "LegalContextBuilder",
    "LegalRAGService",
    "BaseLLMProvider",
    "get_llm_provider"
]

