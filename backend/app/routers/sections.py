"""
Vidhik Platform - Sections API Router
=====================================
Read-only endpoints for querying statutory sections from the PostgreSQL database.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.section import SectionSummaryResponse, SectionResponse, SectionListResponse

router = APIRouter(prefix="/api/sections", tags=["Sections"])


@router.get("", response_model=SectionListResponse, summary="List Sections (Paginated)")
def get_sections(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return (1-100)"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    law_id: Optional[int] = Query(default=None, description="Filter by parent law ID"),
    section_number: Optional[str] = Query(default=None, description="Search or filter by section number"),
    section_title: Optional[str] = Query(default=None, description="Search term matching section title"),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves a paginated list of statutory sections from the PostgreSQL `sections` table.
    Operations are strictly read-only and use parameterized queries.
    """
    conditions = []
    params = []

    if law_id is not None:
        conditions.append("law_id = %s")
        params.append(law_id)

    if section_number:
        conditions.append("section_number ILIKE %s")
        params.append(f"%{section_number.strip()}%")

    if section_title:
        conditions.append("section_title ILIKE %s")
        params.append(f"%{section_title.strip()}%")

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total matching records
    count_sql = f"SELECT COUNT(*) AS total FROM sections{where_clause};"
    db.execute(count_sql, tuple(params))
    total_count = db.fetchone()["total"]

    # Fetch paginated rows with actual existing columns
    data_sql = f"""
        SELECT 
            section_id,
            law_id,
            section_number,
            section_title,
            section_uid,
            full_text AS section_text,
            full_text,
            chapter_number,
            chapter_title,
            source_pdf,
            source_page_start,
            source_page_end,
            source_page_start AS page_start,
            source_page_end AS page_end,
            manual_review_required,
            is_omitted
        FROM sections
        {where_clause}
        ORDER BY section_id ASC
        LIMIT %s OFFSET %s;
    """
    db.execute(data_sql, tuple(params + [limit, offset]))
    rows = db.fetchall()

    return SectionListResponse(
        total=total_count,
        limit=limit,
        offset=offset,
        sections=[SectionSummaryResponse(**row) for row in rows]
    )


@router.get("/{section_id}", response_model=SectionResponse, summary="Get Single Section by ID")
def get_section_by_id(
    section_id: int,
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves a single section record by its primary key `section_id`.
    """
    db.execute("""
        SELECT 
            section_id,
            law_id,
            section_number,
            section_title,
            section_uid,
            description,
            full_text,
            full_text AS section_text,
            chapter,
            part,
            chapter_number,
            chapter_title,
            part_number,
            part_title,
            source_url,
            source_pdf,
            source_page_start,
            source_page_end,
            source_page_start AS page_start,
            source_page_end AS page_end,
            jurisdiction,
            is_omitted,
            omission_note,
            is_definition_section,
            subsections_count,
            clauses_count,
            subclauses_count,
            has_proviso,
            has_explanation,
            has_illustration,
            has_schedule_ref,
            extraction_status,
            manual_review_required,
            parser_notes,
            text_sha256,
            created_at,
            updated_at
        FROM sections
        WHERE section_id = %s;
    """, (section_id,))

    row = db.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section with ID {section_id} not found."
        )

    return SectionResponse(**row)
