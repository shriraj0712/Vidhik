"""
Vidhik Platform - FastAPI Main Application Entry Point
======================================================
Provides RESTful APIs for querying Indian statutory laws, legal sections,
terminology, constitutional provisions, legal AI assistant, grounded RAG,
and the advanced legal knowledge base from the Vidhik legal platform.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import init_db_pool, close_db_pool
from app.middleware import SecurityHeadersMiddleware, RateLimiterMiddleware
from app.routers import (
    health_router,
    laws_router,
    sections_router,
    search_router,
    auth_router,
    lawyer_router,
    documentation_router,
    document_analysis_router,
    citizen_router,
    assistant_router,
    rag_router,
    knowledge_base_router,
    authorities_router,
    case_intelligence_router,
    resolution_router,
    complaint_generator_router,
    admin_router,
    evidence_router
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes database pool on startup and gracefully terminates on shutdown.
    """
    init_db_pool()
    yield
    close_db_pool()


app = FastAPI(
    title="Vidhik Legal Platform API",
    description="""
    **Vidhik** is a high-precision AI-native legal research, intelligence, and workflow platform for Indian statutory law.
    
    ### Available Modules:
    - **Health**: System status and PostgreSQL database connectivity checks.
    - **Laws**: Search, filter, and inspect Central and State Acts.
    - **Sections**: Paginated queries, title search, and detailed section inspection.
    - **Search**: Multi-field legal search across statutes, section numbers, titles, and legal text.
    - **Authentication**: JWT & Bcrypt hardened Lawyer & Citizen session management with audit logging.
    - **Lawyer Module (Phase 13)**: Professional lawyer workspace with dashboard, client management, case lifecycle, document cataloging, court hearing scheduling, and confidential case notes.
    - **Citizen Module (Phase 14)**: Citizen legal workspace with procedure trackers, case bookmarking, and legal consultation records.
    - **Documentation Support (Phase 12)**: 25 authoritative citizen legal procedures, checklists, and document prerequisites.
    - **Legal Document Analysis (Phase 11)**: Contract and document parsing, clause risk assessment, and statutory cross-referencing.
    - **AI Legal Assistant (Phase 15)**: Multi-turn conversational legal assistant grounded in Indian statutes.
    - **Legal RAG Engine (Phase 15)**: Multi-field grounded retrieval and citation synthesis.
    - **Advanced Legal Knowledge Base (Phase 17)**: BNS, BNSS, BSA, 24 Bare Acts, offences, punishments, statutory procedures, evidence provisions, predecessor mappings, and verified Supreme Court judgments.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiter Middleware for Sensitive Endpoints
app.add_middleware(RateLimiterMiddleware)

# CORS Configuration
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(health_router)
app.include_router(laws_router)
app.include_router(sections_router)
app.include_router(search_router)
app.include_router(auth_router)
app.include_router(lawyer_router)
app.include_router(documentation_router)
app.include_router(document_analysis_router)
app.include_router(citizen_router)
app.include_router(assistant_router)
app.include_router(rag_router)
app.include_router(knowledge_base_router)
app.include_router(authorities_router)
app.include_router(case_intelligence_router)
app.include_router(resolution_router)
app.include_router(complaint_generator_router)
app.include_router(admin_router)
app.include_router(evidence_router)

# Mount Static UI directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/citizen", tags=["Citizen UI"], summary="Serve Citizen Portal UI")
def serve_citizen_ui():
    """Serves the single-page citizen workspace UI application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Citizen Module UI build is initializing."}


@app.get("/lawyer", tags=["Lawyer UI"], summary="Serve Lawyer Workspace UI")
def serve_lawyer_ui():
    """Serves the single-page lawyer workspace UI application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Lawyer Module UI build is initializing."}


@app.get("/", tags=["Root"], summary="API Root & Workspace Redirect")
def root():
    """
    Root endpoint: serves the UI application if accessed via browser,
    otherwise provides API information and documentation links.
    """
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return {
        "platform": "Vidhik Legal Platform",
        "description": "AI-native Indian Legal Knowledge & Research Engine",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/health",
        "lawyer_workspace": "/lawyer",
        "citizen_portal": "/citizen",
        "endpoints": {
            "health": "GET /health",
            "laws_list": "GET /api/laws",
            "law_detail": "GET /api/laws/{law_id}",
            "sections_list": "GET /api/sections",
            "section_detail": "GET /api/sections/{section_id}",
            "legal_search": "GET /api/search",
            "auth_login": "POST /api/auth/login",
            "auth_register": "POST /api/auth/register",
            "auth_logout": "POST /api/auth/logout",
            "citizen_dashboard": "GET /api/citizen/dashboard",
            "citizen_cases": "GET /api/citizen/cases",
            "citizen_documents": "GET /api/citizen/documents",
            "citizen_hearings": "GET /api/citizen/hearings",
            "citizen_profile": "GET /api/citizen/profile",
            "citizen_bookmarks": "GET /api/citizen/bookmarks",
            "citizen_search_history": "GET /api/citizen/search-history",
            "citizen_notifications": "GET /api/citizen/notifications",
            "citizen_procedures": "GET /api/citizen/procedures",
            "lawyer_dashboard": "GET /api/lawyer/dashboard",
            "lawyer_clients": "GET /api/lawyer/clients",
            "lawyer_cases": "GET /api/lawyer/cases",
            "lawyer_hearings": "GET /api/lawyer/hearings",
            "lawyer_documents": "GET /api/lawyer/documents",
            "lawyer_profile": "GET /api/lawyer/profile",
            "documentation_categories": "GET /api/documentation/categories",
            "documentation_procedures": "GET /api/documentation/procedures",
            "documentation_procedure_detail": "GET /api/documentation/procedures/{id}",
            "documentation_checklist": "GET /api/documentation/procedures/{id}/checklist",
            "analysis_upload": "POST /api/analysis/upload",
            "analysis_text": "POST /api/analysis/text",
            "analysis_history": "GET /api/analysis/history",
            "analysis_detail": "GET /api/analysis/{analysis_id}",
            "analysis_save_to_case": "POST /api/analysis/{analysis_id}/save-to-case",
            "assistant_chat": "POST /api/assistant/chat",
            "assistant_health": "GET /api/assistant/health",
            "rag_query": "POST /api/rag/query",
            "rag_health": "GET /api/rag/health",
            "knowledge_overview": "GET /api/knowledge/overview",
            "knowledge_offences": "GET /api/knowledge/offences",
            "knowledge_punishments": "GET /api/knowledge/punishments",
            "knowledge_procedures": "GET /api/knowledge/procedures",
            "knowledge_evidence": "GET /api/knowledge/evidence",
            "knowledge_predecessors": "GET /api/knowledge/predecessors",
            "knowledge_judgments": "GET /api/knowledge/judgments",
            "knowledge_section_context": "GET /api/knowledge/sections/{section_number}/context",
            "knowledge_acts": "GET /api/knowledge/acts",
            "knowledge_act_detail": "GET /api/knowledge/acts/{act_id}",
            "knowledge_search": "GET /api/knowledge/search",
            "case_active": "GET /api/cases/active",
            "case_set_active": "POST /api/cases/{case_id}/set-active",
            "case_create_and_analyze": "POST /api/cases/create-and-analyze",
            "case_context": "GET /api/cases/{case_id}/context",
            "case_situation_overview": "GET /api/cases/{case_id}/situation-overview",
            "case_legal_analysis": "GET /api/cases/{case_id}/legal-analysis",
            "case_legal_ranking": "GET /api/cases/{case_id}/legal-ranking",
            "case_action_plan": "GET /api/cases/{case_id}/action-plan",
            "case_documents": "GET /api/cases/{case_id}/documents",
            "case_procedure": "GET /api/cases/{case_id}/procedure",
            "case_emotional_analysis": "GET /api/cases/{case_id}/emotional-analysis",
            "case_lawyer_recommendation": "GET /api/cases/{case_id}/lawyer-recommendation",
            "case_authority_recommendation": "GET /api/cases/{case_id}/authority-recommendation",
            "case_update_and_reanalyze": "POST /api/cases/{case_id}/update-and-reanalyze"
        }
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
