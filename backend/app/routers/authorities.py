"""
Vidhik Platform - Judicial Authority Recommendation Router
==========================================================
Exposes read-only API endpoint for recommending verified judicial authorities
and controlling case-law based on legal query, statute, or section identifiers.
"""

from typing import Optional, Generator, Any
from fastapi import APIRouter, Depends, Query, status

from app.schemas.authority import AuthorityRecommendationResponse
from app.services.authority_service import AuthorityRecommendationService

router = APIRouter(prefix="/api/authorities", tags=["Judicial Authorities"])


def get_optional_db() -> Generator[Optional[Any], None, None]:
    """
    Yields database cursor if connected, otherwise yields None
    for resilient high-availability in-memory mode.
    """
    try:
        from app.database import get_db_cursor
        with get_db_cursor() as cur:
            yield cur
    except Exception:
        yield None


@router.get(
    "/recommend",
    response_model=AuthorityRecommendationResponse,
    summary="Recommend Verified Judicial Authorities"
)
def recommend_authorities(
    q: Optional[str] = Query(default=None, description="Search query or legal issue"),
    law_id: Optional[int] = Query(default=None, gt=0, description="Optional parent Law ID"),
    section_number: Optional[str] = Query(default=None, description="Optional statutory section number"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum recommendations to return"),
    db: Optional[Any] = Depends(get_optional_db)
):
    """
    Returns deterministically matched and ranked judicial authorities.
    Strictly read-only; never generates or fabricates cases or citations.
    
    If no verified authorities exist for a requested Act or domain,
    explicitly returns status 'NOT IN SOURCE'.
    """
    return AuthorityRecommendationService.recommend_authorities(
        query=q,
        law_id=law_id,
        section_number=section_number,
        limit=limit,
        db=db
    )
