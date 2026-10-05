import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.emergency import EmergencyEvaluationRequest, EmergencyEvaluationResponse
from app.services.emergency_service import EmergencyInterceptorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/emergency", tags=["Emergency Interceptor"])


@router.post("/intercept", response_model=EmergencyEvaluationResponse)
def intercept_emergency(request: EmergencyEvaluationRequest):
    """
    Evaluates text for imminent physical danger, domestic violence, cyber fraud, and custody risks.
    """
    try:
        return EmergencyInterceptorService.evaluate(request)
    except Exception as e:
        logger.error(f"Error during emergency interception: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while evaluating emergency risk."
        )


@router.get("/helplines")
def get_verified_helplines():
    """
    Returns verified national emergency helplines.
    """
    return {
        "status": "success",
        "helplines": [
            {
                "category": k,
                "name": v.name,
                "number": v.number,
                "description": v.description
            }
            for k, v in EmergencyInterceptorService.VERIFIED_HELPLINES.items()
        ]
    }


@router.get("/health")
def emergency_health():
    """
    Health check for Emergency Interceptor service.
    """
    return {
        "status": "healthy",
        "service": "emergency_interceptor_service",
        "registered_rules": len(EmergencyInterceptorService.EMERGENCY_RULES),
        "verified_helpline_count": len(EmergencyInterceptorService.VERIFIED_HELPLINES)
    }
