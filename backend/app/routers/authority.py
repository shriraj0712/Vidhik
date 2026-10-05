import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.authority import AuthorityRecommendationRequest, AuthorityRecommendationResponse
from app.services.authority_service import AuthorityService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/authority", tags=["Authority Recommendation Intelligence"])


@router.post("/recommend", response_model=AuthorityRecommendationResponse)
def recommend_authority(request: AuthorityRecommendationRequest):
    """
    Recommends verified public authorities, tribunals, and statutory ombudsmen based on issue and jurisdiction.
    """
    try:
        return AuthorityService.recommend_authority(request)
    except Exception as e:
        logger.error(f"Error recommending authority: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while recommending statutory authority."
        )


@router.get("/domains")
def list_supported_authority_domains():
    """
    Lists registered authority domains and primary bodies.
    """
    return {
        "status": "success",
        "domains": [
            {
                "key": k,
                "primary_authority": v["primary"].name,
                "portal": v["primary"].official_portal
            }
            for k, v in AuthorityService.AUTHORITIES_DB.items()
        ]
    }


@router.get("/health")
def authority_health():
    """
    Health check for Authority Recommendation Intelligence service.
    """
    return {
        "status": "healthy",
        "service": "authority_service",
        "registered_domains_count": len(AuthorityService.AUTHORITIES_DB)
    }
