import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.constitutional import ConstitutionalAnalysisRequest, ConstitutionalAnalysisResponse
from app.services.constitutional_service import ConstitutionalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/constitutional", tags=["Constitutional Rights Engine"])


@router.post("/analyze", response_model=ConstitutionalAnalysisResponse)
def analyze_constitutional_rights(request: ConstitutionalAnalysisRequest):
    """
    Identifies potentially applicable Fundamental Rights (Part III) and Constitutional remedies (Articles 32 & 226).
    """
    try:
        return ConstitutionalService.analyze(request)
    except Exception as e:
        logger.error(f"Error during constitutional analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing constitutional rights."
        )


@router.get("/rights")
def list_supported_rights():
    """
    Lists all indexed constitutional fundamental rights and their scope.
    """
    return {
        "status": "success",
        "rights": [
            {
                "article": r["article"],
                "title": r["title"],
                "category": r["category"],
                "explanation": r["citizen_explanation"]
            }
            for r in ConstitutionalService.CONSTITUTIONAL_RIGHTS_DB
        ]
    }


@router.get("/health")
def constitutional_health():
    """
    Health check for Constitutional Rights Engine.
    """
    return {
        "status": "healthy",
        "service": "constitutional_service",
        "indexed_articles_count": len(ConstitutionalService.CONSTITUTIONAL_RIGHTS_DB)
    }
