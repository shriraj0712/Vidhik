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

from app.database import close_db_pool
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
    resolution_router,
    complaint_generator_router,
    ai_safety_router,
    legal_classifier_router,
    intent_router,
    emergency_router,
    element_verification_router,
    constitutional_router,
    traffic_router,
    authority_router,
    voice_router,
    ai_evaluation_router,
    authorities_router,
    case_intelligence_router,
    admin_router,
    evidence_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Keep HTTP startup independent from database and provider availability.
    Dependencies are checked by the readiness endpoint and initialized lazily.
    """
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
    - **Lawyer Module**: Professional lawyer workspace with dashboard, client management, case lifecycle, document cataloging, court hearing scheduling, and confidential case notes.
    - **Citizen Module**: Citizen legal workspace with procedure trackers, case bookmarking, and legal consultation records.
    - **Documentation Support**: 25 authoritative citizen legal procedures, checklists, and document prerequisites.
    - **Legal Document Analysis**: Contract and document parsing, clause risk assessment, and statutory cross-referencing.
    - **AI Legal Assistant**: Multi-turn conversational legal assistant grounded in Indian statutes with streaming support.
    - **Legal RAG Engine**: Multi-field grounded retrieval and citation synthesis.
    - **Advanced Legal Knowledge Base**: BNS, BNSS, BSA, 24 Bare Acts, offences, punishments, statutory procedures, evidence provisions, predecessor mappings, and verified Supreme Court judgments.
    - **Resolution Decision Engine**: Triage between self-resolution and lawyer necessity.
    - **Complaint / FIR Generator**: Factual citizen written complaints, FIR registration requests under BNSS Section 173, non-cognizable complaints, and DOCX export.
    - **AI Safety Guardrails**: Deterministic detection of prompt injection, jailbreaks, fabrication, evasion, and PII protection.
    - **Legal Issue Classifier**: Deterministic multilingual domain classification across Indian legal taxonomy.
    - **Intent Router**: Deterministic intent classification and service routing.
    - **Emergency Interceptor**: Immediate life-safety, domestic violence, cyber fraud, and custody emergency escalation.
    - **Statutory Element Verification**: Factual correspondence testing against statutory elements without guilt determination.
    - **Constitutional Rights Engine**: Grounded analysis of Fundamental Rights (Part III) and Writ remedies (Articles 32/226).
    - **Traffic Legal Engine**: Motor Vehicles Act violation analysis, e-challan dispute workflows, and statutory penalties.
    - **Authority Recommendation**: Routing to verified statutory bodies, commissions, and ombudsmen.
    - **Voice / STT Backend**: Speech-to-text provider abstraction for Indian languages.
    - **AI Quality & Diagnostics**: Automated quality, safety, citation grounding, and multilingual evaluation suite.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
app.include_router(resolution_router)
app.include_router(complaint_generator_router)
app.include_router(ai_safety_router)
app.include_router(legal_classifier_router)
app.include_router(intent_router)
app.include_router(emergency_router)
app.include_router(element_verification_router)
app.include_router(constitutional_router)
app.include_router(traffic_router)
app.include_router(authority_router)
app.include_router(voice_router)
app.include_router(ai_evaluation_router)
app.include_router(authorities_router)
app.include_router(case_intelligence_router)
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
    otherwise returns platform metadata and active module registry.
    """
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "platform": "Vidhik AI-Native Legal Platform",
        "version": "1.0.0",
        "description": "Comprehensive Indian Legal Knowledge Base, Citizen & Lawyer Workspaces, and Grounded AI Legal Assistant",
        "documentation": "/docs",
        "health": "/api/health",
        "health_check": "/health",
        "lawyer_workspace": "/lawyer",
        "citizen_portal": "/citizen",
        "modules": {
            "health": "/api/health",
            "laws": "/api/laws",
            "sections": "/api/sections",
            "search": "/api/search",
            "auth": "/api/auth",
            "lawyer": "/api/lawyer",
            "citizen": "/api/citizen",
            "documentation": "/api/documentation",
            "document_analysis": "/api/document-analysis",
            "assistant": "/api/assistant/chat",
            "assistant_stream": "/api/assistant/chat/stream",
            "rag": "/api/rag/query",
            "knowledge_base": "/api/knowledge",
            "resolution": "/api/resolution/evaluate",
            "complaint_generator": "/api/complaints/generate",
            "safety": "/api/safety/check",
            "classifier": "/api/classifier/classify",
            "intent": "/api/intent/route",
            "emergency": "/api/emergency/intercept",
            "element_verification": "/api/elements/verify",
            "constitutional": "/api/constitutional/analyze",
            "traffic": "/api/traffic/analyze",
            "authority": "/api/authority/recommend",
            "voice": "/api/voice/transcribe",
            "ai_evaluation": "/api/ai-evaluation/run-suite",
            "authorities": "/api/authorities",
            "case_intelligence": "/api/cases/active",
            "admin": "/api/admin",
            "evidence": "/api/evidence"
        },
        "endpoints": {
            "auth_login": "POST /api/auth/login",
            "auth_register": "POST /api/auth/register",
            "auth_logout": "POST /api/auth/logout",
            "assistant_chat": "POST /api/assistant/chat",
            "case_active": "GET /api/cases/active",
            "case_create_and_analyze": "POST /api/cases/create-and-analyze"
        }
    }
