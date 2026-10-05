import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.ai_safety import SafetyCheckRequest, SafetyCheckResponse
from app.services.ai_safety_service import AISafetyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/safety", tags=["AI Safety & Guardrails"])


@router.post("/check", response_model=SafetyCheckResponse)
def check_safety(request: SafetyCheckRequest):
    """
    Scans text against AI safety guardrails (prompt injection, fabrication, evasion, PII).
    """
    try:
        return AISafetyService.audit_text(request)
    except Exception as e:
        logger.error(f"Error during safety check: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while auditing safety guardrails."
        )


@router.get("/health")
def safety_health():
    """
    Health and readiness probe for the AI Safety Guardrails service.
    """
    return {
        "status": "healthy",
        "service": "ai_safety_service",
        "version": "1.0.0",
        "guardrail_categories": [
            "prompt_injection",
            "system_prompt_extraction",
            "fabrication_or_forgery",
            "obstruction_of_justice",
            "coercion_or_extortion",
            "pii_redaction"
        ]
    }
