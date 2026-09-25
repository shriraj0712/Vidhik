"""
Vidhik Platform - API Routers
"""

from .health import router as health_router
from .laws import router as laws_router
from .sections import router as sections_router
from .search import router as search_router
from .rag import router as rag_router

__all__ = ["health_router", "laws_router", "sections_router", "search_router", "rag_router"]

