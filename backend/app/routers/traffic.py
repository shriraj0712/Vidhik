import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.traffic import TrafficAnalysisRequest, TrafficAnalysisResponse
from app.services.traffic_service import TrafficService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/traffic", tags=["Traffic Legal Engine"])


@router.post("/analyze", response_model=TrafficAnalysisResponse)
def analyze_traffic_matter(request: TrafficAnalysisRequest):
    """
    Analyzes traffic citations, e-challans, and MVA statutory penalties and dispute workflows.
    """
    try:
        return TrafficService.analyze_traffic(request)
    except Exception as e:
        logger.error(f"Error during traffic analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing traffic legal inquiry."
        )


@router.get("/offences")
def list_traffic_offences():
    """
    Lists common statutory traffic offences and penalties under MVA.
    """
    return {
        "status": "success",
        "offences": [
            {
                "key": o["key"],
                "name": o["name"],
                "section": o["section"],
                "penalty": o["penalty"],
                "court_required": o["court_required"]
            }
            for o in TrafficService.OFFENCES_DB
        ]
    }


@router.get("/health")
def traffic_health():
    """
    Health check for Traffic Legal Engine.
    """
    return {
        "status": "healthy",
        "service": "traffic_service",
        "indexed_offence_count": len(TrafficService.OFFENCES_DB)
    }
