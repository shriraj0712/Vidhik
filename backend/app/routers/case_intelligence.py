"""
Vidhik Platform - Case Intelligence Router
==========================================
Exposes RESTful endpoints for the generalized, dynamic Case Intelligence Engine:
- Analyze natural language legal matters dynamically
- Retrieve persistent current case context
- Switch active current case
- Submit case clarifications and missing information
- List case history
"""

from typing import Optional, List, Dict, Any, Generator
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.case_intelligence import (
    CaseContext,
    CaseAnalyzeRequest,
    CaseClarificationRequest,
    CaseSwitchResponse
)
from app.services.case_intelligence_service import CaseIntelligenceService, CaseStore

router = APIRouter(prefix="/api/case", tags=["Case Intelligence"])


def get_optional_db() -> Generator[Optional[Any], None, None]:
    """
    Yields database cursor if connected, otherwise yields None
    for resilient dual-mode operation.
    """
    try:
        from app.database import get_db_cursor
        with get_db_cursor() as cur:
            yield cur
    except Exception:
        yield None


@router.post(
    "/analyze",
    response_model=CaseContext,
    status_code=status.HTTP_200_OK,
    summary="Analyze Natural Language Legal Matter"
)
def analyze_matter(
    payload: CaseAnalyzeRequest,
    db: Optional[Any] = Depends(get_optional_db)
):
    """
    Dynamically analyzes ANY legal matter described in natural language.
    Executes fact extraction, multi-issue identification, 24-Act statutory search,
    deterministic ranking, authority matching, lawyer matching, action plan generation,
    document checklist, procedural roadmap, and emotional indicators.

    Sets the analyzed case as the persistent current active case.
    """
    if not payload.description or not payload.description.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description cannot be empty."
        )

    context = CaseIntelligenceService.analyze_case(
        description=payload.description,
        case_id=payload.case_id,
        jurisdiction_hint=payload.jurisdiction_hint,
        db_cursor=db
    )
    return context


@router.get(
    "/current",
    response_model=CaseContext,
    summary="Get Persistent Current Case Context"
)
def get_current_case():
    """
    Retrieves the persistent active case currently in session.
    All platform modules connect dynamically to this active case context.
    """
    current = CaseStore.get_current_case()
    if not current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active current case found in session. Please submit a legal matter first via POST /api/case/analyze."
        )
    return current


@router.get(
    "/{case_id}",
    response_model=CaseContext,
    summary="Get Case Context by ID"
)
def get_case_by_id(case_id: str):
    """
    Retrieves full CaseContext for a specific case identifier (e.g. CASE-001).
    """
    case = CaseStore.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found."
        )
    return case


@router.post(
    "/{case_id}/switch",
    response_model=CaseSwitchResponse,
    summary="Switch Persistent Current Case"
)
def switch_current_case(case_id: str):
    """
    Switches the persistent session focus to another existing case.
    Subsequent module queries will automatically refer to this case.
    """
    case = CaseStore.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot switch: Case ID '{case_id}' does not exist."
        )

    success = CaseStore.set_current_case_id(case_id)
    return CaseSwitchResponse(
        success=success,
        current_case_id=case_id,
        message=f"Current case successfully switched to {case_id}.",
        case_summary={
            "case_id": case.case_id,
            "title": case.issues[0].title if case.issues else "Legal Matter",
            "domains": case.legal_domains,
            "urgency": case.urgency
        }
    )


@router.post(
    "/{case_id}/clarify",
    response_model=CaseContext,
    summary="Clarify Case & Incorporate Missing Information"
)
def clarify_case(
    case_id: str,
    payload: CaseClarificationRequest,
    db: Optional[Any] = Depends(get_optional_db)
):
    """
    Incorporates user follow-up clarifications and answers to missing information,
    re-running the dynamic intelligence pipeline with updated factual grounds.
    """
    case = CaseStore.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found."
        )

    updated_context = CaseIntelligenceService.clarify_case(
        case_id=case_id,
        clarification_text=payload.clarification_text,
        answers=payload.answers,
        db_cursor=db
    )
    return updated_context


@router.get(
    "",
    response_model=List[Dict[str, Any]],
    summary="List All Analyzed Cases"
)
def list_cases():
    """
    Lists all analyzed cases in the session store with summary metadata.
    """
    return CaseStore.list_all()
