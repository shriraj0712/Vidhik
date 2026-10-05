import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.element_verification import ElementVerificationRequest, ElementVerificationResponse
from app.services.element_verification_service import ElementVerificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/elements", tags=["Statutory Element Verification"])


@router.post("/verify", response_model=ElementVerificationResponse)
def verify_statutory_elements(request: ElementVerificationRequest):
    """
    Evaluates factual alignment against statutory elements without drawing guilt determinations.
    """
    try:
        return ElementVerificationService.verify_elements(request)
    except Exception as e:
        logger.error(f"Error during statutory element verification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while verifying statutory elements."
        )


@router.get("/health")
def element_verification_health():
    """
    Health check and supported statutory provisions list.
    """
    return {
        "status": "healthy",
        "service": "element_verification_service",
        "supported_provisions": list(ElementVerificationService.STATUTORY_ELEMENTS_DB.keys())
    }
