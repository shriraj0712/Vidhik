"""
Vidhik Platform - Legal Search API Router
=========================================
Thin API endpoint layer for legal search request validation and dispatch.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.search import SearchResponse
from app.services.search_service import LegalSearchService

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("", response_model=SearchResponse, summary="Search Legal Corpus")
def search_legal_corpus(
    q: str = Query(..., min_length=1, description="Required search text across laws and sections"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum records to return (1-50)"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    law_id: Optional[int] = Query(default=None, gt=0, description="Filter by parent Law ID (must be > 0)"),
    jurisdiction: Optional[str] = Query(default=None, description="Filter by jurisdiction (e.g., India, Maharashtra)"),
    db: RealDictCursor = Depends(get_db)
):
    """
    Performs a safe, parameterized ILIKE search across statutory laws and provisions.
    Delegates query building, execution, and snippet extraction to LegalSearchService.
    
    All database operations are strictly read-only.
    """
    clean_q = q.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Search query 'q' must not be empty or whitespace only."
        )

    return LegalSearchService.search(
        db=db,
        query=q,
        limit=limit,
        offset=offset,
        law_id=law_id,
        jurisdiction=jurisdiction
    )

