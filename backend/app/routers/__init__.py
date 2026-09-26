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
from .knowledge_base import router as knowledge_base_router

__all__ = [
    "health_router",
    "laws_router",
    "sections_router",
    "search_router",
    "auth_router",
    "lawyer_router",
    "documentation_router",
    "knowledge_base_router",
]


