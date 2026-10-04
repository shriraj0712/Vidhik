"""
Vidhik Platform - Business & Query Services
===========================================
Dedicated service layer separating database access, business logic, and
query generation from FastAPI router endpoints.
"""

from .search_service import LegalSearchService
from .query_service import LegalQueryService
from .ranking_service import LegalRankingService
from .documentation_service import DocumentationService
from .knowledge_service import LegalKnowledgeService

__all__ = [
    "LegalSearchService",
    "LegalQueryService",
    "LegalRankingService",
    "DocumentationService",
    "LegalKnowledgeService"
]


