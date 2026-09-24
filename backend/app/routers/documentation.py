"""
Vidhik Platform - Documentation Support API Router
===================================================
REST API endpoints for Indian legal procedures, statutory document checklists,
and procedural preparation guidance.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.services.documentation_service import DocumentationService
from app.schemas.documentation import (
    ProcedureSummary,
    ProcedureDetail,
    ChecklistResponse,
    CategoryResponse,
    ProcedureListResponse
)

router = APIRouter(prefix="/api/documentation", tags=["Documentation Support"])


@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="List Procedure Categories"
)
def get_categories(db: RealDictCursor = Depends(get_db)):
    """
    Returns available distinct procedure categories with count of procedures
    grounded in the database.
    """
    return DocumentationService.get_categories(db)


@router.get(
    "/procedures",
    response_model=ProcedureListResponse,
    summary="List & Search Legal Procedures"
)
def list_procedures(
    search: Optional[str] = Query(
        default=None,
        description="Search term matching procedure name, description, or authority"
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by legal category (e.g., Property, Government Applications, Court / Litigation)"
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum procedures to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: RealDictCursor = Depends(get_db)
):
    """
    Retrieves a searchable, category-filtered list of Indian legal procedures
    with governing statutory references and document requirement counts.
    """
    return DocumentationService.list_procedures(
        db=db,
        search=search,
        category=category,
        limit=limit,
        offset=offset
    )


@router.get(
    "/procedures/{procedure_id}",
    response_model=ProcedureDetail,
    summary="Get Procedure Details & Checklist"
)
def get_procedure_detail(
    procedure_id: int,
    db: RealDictCursor = Depends(get_db)
):
    """
    Returns complete procedural overview, statutory authorities, estimated timelines,
    and all partitioned document requirements (Mandatory and Supporting).
    """
    proc = DocumentationService.get_procedure_by_id(db, procedure_id)
    if not proc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal procedure with ID {procedure_id} not found."
        )
    return proc


@router.get(
    "/procedures/{procedure_id}/checklist",
    response_model=ChecklistResponse,
    summary="Get Structured Document Checklist"
)
def get_procedure_checklist(
    procedure_id: int,
    db: RealDictCursor = Depends(get_db)
):
    """
    Returns structured document checklist for a procedure, clearly isolating
    mandatory statutory requirements from supporting/practical documents,
    with direct references to underlying Acts and Sections.
    """
    checklist = DocumentationService.get_procedure_checklist(db, procedure_id)
    if not checklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document checklist for procedure ID {procedure_id} not found."
        )
    return checklist
