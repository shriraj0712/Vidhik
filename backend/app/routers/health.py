"""
Vidhik Platform - Health Check Router
====================================
Endpoint for verifying service status and database connectivity.
"""

from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.database import check_db_connection
from app.services.llm_provider import check_llm_provider_readiness

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service Health Check")
@router.get("/api/health", include_in_schema=False)
def health_check():
    """
    Fast liveness endpoint that does not wait on external dependencies.
    """
    return {
        "status": "alive",
        "application": {"status": "alive"},
        "service": "Vidhik Legal Platform API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {"status": "not_checked", "readiness_endpoint": "/health/ready"},
        "llm_provider": {"status": "not_checked", "readiness_endpoint": "/health/ready"},
    }


@router.get("/health/ready", summary="Dependency Readiness Check")
@router.get("/api/health/ready", include_in_schema=False)
def readiness_check():
    """Check database and configured LLM provider with bounded network waits."""
    database = check_db_connection()
    llm = check_llm_provider_readiness()
    ready = database.get("status") == "connected" and llm.get("ready") is True
    payload = {
        "status": "ready" if ready else "not_ready",
        "application": {"status": "alive"},
        "database": database,
        "llm_provider": llm,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)
