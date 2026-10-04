"""
Vidhik Platform - API Routers
"""

from .health import router as health_router
from .laws import router as laws_router
from .sections import router as sections_router
from .search import router as search_router
from .auth import router as auth_router
from .lawyer import router as lawyer_router
from .documentation import router as documentation_router
from .document_analysis import router as document_analysis_router
from .citizen import router as citizen_router
from .assistant import router as assistant_router
from .rag import router as rag_router
from .knowledge_base import router as knowledge_base_router
from .authorities import router as authorities_router

__all__ = [
    "health_router",
    "laws_router",
    "sections_router",
    "search_router",
    "auth_router",
    "lawyer_router",
    "documentation_router",
    "document_analysis_router",
    "citizen_router",
    "assistant_router",
    "rag_router",
    "knowledge_base_router",
    "authorities_router",
]
