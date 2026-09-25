"""
Vidhik Platform - Legal Document Analysis API Router (Phase 11)
===============================================================
RESTful endpoints for:
- Uploading and parsing legal documents (.pdf, .docx, .txt) and direct text paste
- Structured legal analysis extraction (parties, dates, values, clauses, risks, actions)
- Authentic statutory grounding verified against Vidhik's 41,442 sections
- Historical analysis inspection and deletion
- Explicit lawyer case brief integration (case_documents, case_notes, case_legal_sections)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Body, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.services.auth_service import get_current_user, require_lawyer
from app.services.document_parser_service import DocumentParserService, ParsedDocument
from app.services.document_analysis_service import DocumentAnalysisService
from app.schemas.document_analysis import (
    DocumentAnalysisResponse,
    AnalysisHistoryResponse,
    SaveToCaseRequest,
    SaveToCaseResponse,
    RawTextAnalysisRequest
)

router = APIRouter(prefix="/api/analysis", tags=["Legal Document Analysis"])


@router.post(
    "/upload",
    response_model=DocumentAnalysisResponse,
    summary="Upload & Analyze Legal Document"
)
async def upload_and_analyze(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    document_title: Optional[str] = Form(None),
    case_id: Optional[int] = Form(None),
    db: RealDictCursor = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Accepts a legal document as a file (.pdf, .docx, .txt) or direct text.
    Extracts text, identifies legal classification, parties, dates, financial values,
    core clauses, potential risks, and cross-references statutory provisions with Vidhik DB.
    """
    user_id = current_user.get("user_id") if current_user else None
    lawyer_id = current_user.get("lawyer_id") if current_user else None

    parsed_doc: Optional[ParsedDocument] = None

    if file and file.filename:
        parsed_doc = await DocumentParserService.parse_upload(file)
    elif text and text.strip():
        parsed_doc = DocumentParserService.parse_raw_text_input(
            text_input=text.strip(),
            document_title=document_title or "Pasted Legal Document"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a document file (.pdf, .docx, .txt) or direct text must be provided."
        )

    # Perform deterministic legal analysis and statutory grounding
    analysis_res = DocumentAnalysisService.analyze_document(
        db=db,
        parsed_doc=parsed_doc,
        user_id=user_id,
        lawyer_id=lawyer_id,
        case_id=case_id,
        persist=True
    )

    return analysis_res


@router.post(
    "/text",
    response_model=DocumentAnalysisResponse,
    summary="Analyze Raw Legal Text (JSON)"
)
def analyze_raw_text(
    payload: RawTextAnalysisRequest,
    db: RealDictCursor = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    JSON endpoint for analyzing raw pasted legal text or draft clauses.
    """
    user_id = current_user.get("user_id") if current_user else None
    lawyer_id = current_user.get("lawyer_id") if current_user else None

    parsed_doc = DocumentParserService.parse_raw_text_input(
        text_input=payload.text,
        document_title=payload.document_title or "Pasted Legal Text"
    )

    return DocumentAnalysisService.analyze_document(
        db=db,
        parsed_doc=parsed_doc,
        user_id=user_id,
        lawyer_id=lawyer_id,
        case_id=payload.case_id,
        persist=True
    )


@router.get(
    "/history",
    response_model=AnalysisHistoryResponse,
    summary="List Document Analysis History"
)
def get_analysis_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: RealDictCursor = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves previous document analyses for the active lawyer/user session.
    """
    lawyer_id = current_user.get("lawyer_id") if current_user else None
    user_id = current_user.get("user_id") if current_user else None

    return DocumentAnalysisService.list_history(
        db=db,
        lawyer_id=lawyer_id,
        user_id=user_id,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{analysis_id}",
    response_model=DocumentAnalysisResponse,
    summary="Get Analysis Report by ID"
)
def get_analysis_detail(
    analysis_id: int,
    db: RealDictCursor = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves complete structured analysis report, parties, clauses, risks,
    and verified statutory citations for a specific analysis ID.
    """
    report = DocumentAnalysisService.get_analysis_by_id(db, analysis_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document analysis with ID {analysis_id} not found."
        )
    return report


@router.post(
    "/{analysis_id}/save-to-case",
    response_model=SaveToCaseResponse,
    summary="Save Analysis Artifacts to Lawyer Case"
)
def save_analysis_to_case(
    analysis_id: int,
    payload: SaveToCaseRequest,
    db: RealDictCursor = Depends(get_db),
    current_lawyer: dict = Depends(require_lawyer)
):
    """
    Explicitly attaches analysis report to an active case:
    - Catalogs as Case Document (case_documents)
    - Saves Executive Summary and Issues Note (case_notes)
    - Links Verified Statutory References directly to case (case_legal_sections)
    Requires explicit user action; never mutates cases automatically.
    """
    lawyer_id = current_lawyer.get("lawyer_id", 1)
    try:
        return DocumentAnalysisService.save_analysis_to_case(
            db=db,
            analysis_id=analysis_id,
            req=payload,
            lawyer_id=lawyer_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{analysis_id}",
    summary="Delete Document Analysis Record"
)
def delete_analysis(
    analysis_id: int,
    db: RealDictCursor = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes an analysis record from the platform.
    """
    lawyer_id = current_user.get("lawyer_id") if current_user else None
    success = DocumentAnalysisService.delete_analysis(db, analysis_id, lawyer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found or unauthorized."
        )
    return {"status": "success", "message": "Analysis report deleted successfully."}
