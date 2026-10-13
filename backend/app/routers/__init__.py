"""
Vidhik Platform - API Routers
"""
from .resolution import router as resolution_router
from .complaint_generator import router as complaint_generator_router
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
from .resolution import router as resolution_router
from .complaint_generator import router as complaint_generator_router
from .ai_safety import router as ai_safety_router
from .legal_classifier import router as legal_classifier_router
from .intent_router import router as intent_router
from .emergency import router as emergency_router
from .element_verification import router as element_verification_router
from .constitutional import router as constitutional_router
from .traffic import router as traffic_router
from .authority import router as authority_router
from .voice import router as voice_router
from .ai_evaluation import router as ai_evaluation_router
from .authorities import router as authorities_router
from .case_intelligence import router as case_intelligence_router
from .admin import router as admin_router
from .evidence import router as evidence_router

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
    "resolution_router",
    "complaint_generator_router",
    "ai_safety_router",
    "legal_classifier_router",
    "intent_router",
    "emergency_router",
    "element_verification_router",
    "constitutional_router",
    "traffic_router",
    "authority_router",
    "voice_router",
    "ai_evaluation_router",
    "authorities_router",
    "case_intelligence_router",
    "resolution_router",
    "complaint_generator_router",
    "admin_router",
    "evidence_router",
]
