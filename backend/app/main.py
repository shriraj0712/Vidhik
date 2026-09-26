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

from app.database import init_db_pool, close_db_pool
from app.routers import health_router, laws_router, sections_router, search_router


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
    **Vidhik** is a high-precision AI-native legal research platform for Indian statutory law.
    
    ### Available Modules:
    - **Health**: System status and PostgreSQL database connectivity checks.
    - **Laws**: Search, filter, and inspect Central and State Acts.
    - **Sections**: Paginated queries, title search, and detailed section inspection.
    - **Search**: Multi-field legal search across statutes, section numbers, titles, and legal text.
    
    *All database interactions are strictly read-only and consume environment-driven configurations.*
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(health_router)
app.include_router(laws_router)
app.include_router(sections_router)
app.include_router(search_router)


@app.get("/", tags=["Root"], summary="API Root Overview")
def root():
    """
    Root endpoint providing API information and documentation links.
    """
    return {
        "platform": "Vidhik Legal Platform",
        "description": "AI-native Indian Legal Knowledge & Research Engine",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/health",
        "endpoints": {
            "health": "GET /health",
            "laws_list": "GET /api/laws",
            "law_detail": "GET /api/laws/{law_id}",
            "sections_list": "GET /api/sections",
            "section_detail": "GET /api/sections/{section_id}",
            "legal_search": "GET /api/search"
        }
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
