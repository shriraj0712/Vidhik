import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.legal_classifier import LegalClassificationRequest, LegalClassificationResponse
from app.services.legal_classifier_service import LegalClassifierService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/classifier", tags=["Legal Issue Classifier"])


@router.post("/classify", response_model=LegalClassificationResponse)
def classify_legal_issue(request: LegalClassificationRequest):
    """
    Classifies legal questions and factual narratives into Indian legal domains deterministically.
    """
    try:
        return LegalClassifierService.classify(request)
    except Exception as e:
        logger.error(f"Error during legal classification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while classifying the legal query."
        )


@router.get("/health")
def classifier_health():
    """
    Health check and supported domain taxonomy probe.
    """
    return {
        "status": "healthy",
        "service": "legal_classifier_service",
        "supported_domains": list(LegalClassifierService.DOMAINS_CONFIG.keys()),
        "supported_languages": ["en", "hi", "mr"]
    }
