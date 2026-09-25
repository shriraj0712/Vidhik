"""
Vidhik Platform - FastAPI Main Application Entry Point
======================================================
High-precision AI-native legal research, documentation, workspace,
and security platform for Indian statutory law.
Consolidates all system modules from Phase 1 through Phase 15.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db_pool, close_db_pool
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.routers import (
    health_router,
    laws_router,
    sections_router,
    search_router,
    rag_router,
    assistant_router,
    auth_router,
    lawyer_router,
    documentation_router,
    document_analysis_router,
    citizen_router,
    admin_router
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
    - **RAG (Phase 9)**: Grounded legal question answering and knowledge retrieval with verified citations.
    - **AI Assistant (Phase 10)**: Conversational multi-turn legal assistant with statutory grounding.
    - **Legal Document Analysis (Phase 11)**: Structured entity extraction, clause analysis, and statutory citation mapping.
    - **Documentation Support (Phase 12)**: Standard legal procedural checklists and required document catalogs.
    - **Lawyer Workspace (Phase 13)**: Professional workspace with client roster, case management, hearings, and notes.
    - **Citizen Portal (Phase 14)**: Citizen case filing, document tracking, statute bookmarks, search history, and reminders.
    - **Authentication & Security (Phase 15)**: Signed JWT tokens, bcrypt password hashing, session management, role guards, rate limiting, and audit logging.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 1. Security Headers Middleware (OWASP recommended)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Authentication Rate Limiting Middleware
rate_limit_per_min = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "60"))
app.add_middleware(RateLimiterMiddleware, limit_per_minute=rate_limit_per_min)

# 3. CORS Configuration
allowed_origins_raw = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
)
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# 4. Register Unified Routers (Phases 1-15)
app.include_router(health_router)
app.include_router(laws_router)
app.include_router(sections_router)
app.include_router(search_router)
app.include_router(rag_router)
app.include_router(assistant_router)
app.include_router(auth_router)
app.include_router(lawyer_router)
app.include_router(documentation_router)
app.include_router(document_analysis_router)
app.include_router(citizen_router)
app.include_router(admin_router)

# 5. Mount Static UI Directory
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


@app.get("/", tags=["Root"], summary="API Root & Workspace Overview")
def root(request: Request):
    """
    Root endpoint: serves the UI application if accessed via browser (HTML request),
    otherwise provides API information and documentation links in JSON format.
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
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
            "rag_query": "POST /api/rag/query",
            "rag_health": "GET /api/rag/health",
            "assistant_chat": "POST /api/assistant/chat",
            "assistant_health": "GET /api/assistant/health",
            "auth_login": "POST /api/auth/login",
            "auth_register": "POST /api/auth/register",
            "auth_logout": "POST /api/auth/logout",
            "citizen_dashboard": "GET /api/citizen/dashboard",
            "lawyer_dashboard": "GET /api/lawyer/dashboard",
            "admin_users": "GET /api/admin/users"
        }
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
