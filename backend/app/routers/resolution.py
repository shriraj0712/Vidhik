"""
Vidhik Platform - Legal Resolution Decision Engine API Router
=======================================================FastAPI route controllers for evaluating citizen legal disputes,
assessing risk levels, and recommending self-resolution vs lawyer consultation.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.resolution import (
    ResolutionEvaluationRequest,
    ResolutionEvaluationResponse
)
from app.services.resolution_service import (
    ResolutionDecisionEngine,
    VERIFIED_PROCEDURES,
    VERIFIED_EMERGENCY_DATA
)

logger = logging.getLogger("vidhik.resolution_router")

router = APIRouter(prefix="/api/resolution", tags=["Resolution Decision Engine"])


@router.post(
    "/evaluate",
    response_model=ResolutionEvaluationResponse,
    summary="Evaluate Legal Resolution & Triage",
    description="""
    Deterministic legal triage engine for citizen inquiries:
    

    1. Evaluates user situation against verified statutory risk matrices.
    2. Identifies urgent safety/custodial threats (Critical Risk).
    3. Identifies court/penal proceedings requiring professional counsel (High/Medium Risk).
    4. Identifies administrative and consumer matters suitable for self-resolution (Low Risk).
    5. Returns actionable step-by-step checklists, verified procedure links, and mandatory disclaimers.
    """
)
def evaluate_resolution(
    request: ResolutionEvaluationRequest
):
    """
    Primary legal triage endpoint.
    """
    clean_sit = request.situation.strip()
    if not clean_sit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Situation description cannot be empty or whitespace only."
        )

    try:
        response = ResolutionDecisionEngine.evaluate(request)
        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error evaluating resolution for situation '{clean_sit[:50]}...': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during resolution evaluation. Please try again later."
        )


@router.get(
    "/health",
    summary="Resolution Engine Health & Diagnostic Status",
    description="Returns operational status, total loaded rules, and supported resolution tiers."
)
def resolution_health():
    """
    Returns diagnostic telemetry on the Resolution Decision Engine subsystem.
    """
    return {
        "status": "operational",
        "subsystem": "Vidhik Resolution Decision Engine",
        "engine_version": "1.0.0",
        "precedence_hierarchy": "URGENT > LAWYER_REQUIRED > SELF_RESOLVABLE > CAUTIOUS_FALLBACK",
        "total_verified_procedures_linked": len(VERIFIED_PROCEDURES),
        "total_emergency_helplines": len(VERIFIED_EMERGENCY_DATA),
        "supported_languages": ["en", "mr", "hi"],
        "deterministic_classification": True
    }
