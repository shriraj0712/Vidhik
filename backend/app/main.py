"""
Vidhik Platform - FastAPI Main Application Entry Point
======================================================
Provides RESTful APIs for querying Indian statutory laws, legal sections,
terminology, and constitutional provisions from the Vidhik legal database.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import init_db_pool, close_db_pool
from app.routers import (
    health_router,
    laws_router,
    sections_router,
    search_router,
    auth_router,
    lawyer_router,
    documentation_router,
    knowledge_base_router,
    authorities_router,
    case_intelligence_router
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
    **Vidhik** is a high-precision AI-native legal research and workflow platform for Indian statutory law.
    
    ### Available Modules:
    - **Health**: System status and PostgreSQL database connectivity checks.
    - **Laws**: Search, filter, and inspect Central and State Acts.
    - **Sections**: Paginated queries, title search, and detailed section inspection.
    - **Search**: Multi-field legal search across statutes, section numbers, titles, and legal text.
    - **Authentication**: Lawyer & Client session management.
    - **Lawyer Module (Phase 13)**: Professional lawyer workspace with dashboard, client management, case lifecycle, document cataloging, court hearing scheduling, confidential case notes, and integrated legal research cross-referencing.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

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
app.include_router(knowledge_base_router)
app.include_router(authorities_router)
app.include_router(case_intelligence_router)

# Mount Static UI directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/lawyer", tags=["Lawyer UI"], summary="Serve Lawyer Workspace UI")
def serve_lawyer_ui():
    """Serves the single-page lawyer workspace UI application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Lawyer Module UI build is initializing."}


@app.get("/", tags=["Root"], summary="API Root & Lawyer Workspace Redirect")
def root():
    """
    Root endpoint: serves the Lawyer Module UI if accessed via browser,
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
        "endpoints": {
            "health": "GET /health",
            "laws_list": "GET /api/laws",
            "law_detail": "GET /api/laws/{law_id}",
            "sections_list": "GET /api/sections",
            "section_detail": "GET /api/sections/{section_id}",
            "legal_search": "GET /api/search",
            "auth_login": "POST /api/auth/login",
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
            "case_analyze": "POST /api/case/analyze",
            "case_current": "GET /api/case/current",
            "case_detail": "GET /api/case/{case_id}",
            "case_switch": "POST /api/case/{case_id}/switch",
            "case_clarify": "POST /api/case/{case_id}/clarify",
            "case_list": "GET /api/case"
        }
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
