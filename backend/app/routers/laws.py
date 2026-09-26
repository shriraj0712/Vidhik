"""
Vidhik Platform - Laws API Router
=================================
Read-only endpoints for querying legal acts from the PostgreSQL database.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.law import LawSummaryResponse, LawResponse, LawListResponse

router = APIRouter(prefix="/api/laws", tags=["Laws"])


@router.get("", response_model=LawListResponse, summary="List Laws (Paginated)")
def get_laws(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    jurisdiction: Optional[str] = Query(default=None, description="Filter by jurisdiction (e.g., India, Maharashtra)"),
    search: Optional[str] = Query(default=None, description="Search term matching law name or slug"),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves a paginated list of laws from the PostgreSQL `laws` table.
    Operations are strictly read-only.
    """
    conditions = []
    params = []

    if jurisdiction:
        conditions.append("jurisdiction ILIKE %s")
        params.append(f"%{jurisdiction.strip()}%")

    if search:
        conditions.append("(law_name ILIKE %s OR law_slug ILIKE %s)")
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total matching records
    count_sql = f"SELECT COUNT(*) AS total FROM laws{where_clause};"
    db.execute(count_sql, tuple(params))
    total_row = db.fetchone()
    total_count = total_row["total"] if total_row else 0

    # Fetch paginated rows
    data_sql = f"""
        SELECT 
            law_id, law_name, law_slug, short_name, year,
            law_type, jurisdiction, total_sections_extracted, is_diglot
        FROM laws
        {where_clause}
        ORDER BY law_id ASC
        LIMIT %s OFFSET %s;
    """
    db.execute(data_sql, tuple(params + [limit, offset]))
    rows = db.fetchall()

    return LawListResponse(
        total=total_count,
        limit=limit,
        offset=offset,
        laws=[LawSummaryResponse(**row) for row in rows]
    )


@router.get("/{law_id}", response_model=LawResponse, summary="Get Single Law by ID")
def get_law_by_id(
    law_id: int,
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves a single law record by its primary key `law_id`.
    """
    db.execute("""
        SELECT 
            law_id, law_name, law_slug, short_name, year, law_type,
            description, jurisdiction, enactment_date, effective_date,
            source_url, source_pdf, total_pages, enactment_start_page,
            total_sections_extracted, is_diglot, extraction_status,
            manual_review_required, parser_notes, created_at, updated_at
        FROM laws
        WHERE law_id = %s;
    """, (law_id,))
    
    row = db.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Law with ID {law_id} not found."
        )

    return LawResponse(**row)
