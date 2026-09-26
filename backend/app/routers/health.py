"""
Vidhik Platform - Health Check Router
====================================
Endpoint for verifying service status and database connectivity.
"""

from datetime import datetime
from fastapi import APIRouter
from app.database import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service Health Check")
def health_check():
    """
    Returns service health status and PostgreSQL database connection state.
    """
    db_health = check_db_connection()
    status = "healthy" if db_health.get("status") == "connected" else "degraded"

    return {
        "status": status,
        "service": "Vidhik Legal Platform API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": db_health
    }
