"""
Vidhik Platform - Complaint / FIR Generator API Router
=======================================================
FastAPI endpoints for generating factual citizen complaints, requests for
registration of FIR (BNSS Sec 173), non-cognizable reports, and Word (.docx) exports.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas.complaint_generator import (
    ComplaintGenerateRequest,
    ComplaintGenerateResponse,
    ComplaintExportDocxRequest
)
from app.services.complaint_generator_service import ComplaintGeneratorService

logger = logging.getLogger("vidhik.complaint_generator_router")

router = APIRouter(prefix="/api/v1/complaint-generator", tags=["Complaint / FIR Generator"])


@router.post(
    "/generate",
    response_model=ComplaintGenerateResponse,
    summary="Generate Factual Complaint / FIR Request Draft",
    description="""
    Generates a structured, non-assertive written complaint / FIR registration request:

    1. Validates and sanitizes user factual inputs (dates, location, description).
    2. Runs anti-fabrication and prompt-injection safety filters.
    3. Runs upstream Resolution Decision Engine triage for emergency risks.
    4. Deterministically retrieves applicable BNS, BNSS, and Bare Act statutory provisions.
    5. Formats chronological facts and BNSS Section 173(2) statutory procedural guidance.
    6. Appends mandatory statutory disclaimer regarding police authority.
    """
)
def generate_complaint(
    request: ComplaintGenerateRequest
):
    """
    Primary complaint generation endpoint.
    """
    clean_desc = request.incident_description.strip()
    if not clean_desc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Incident description cannot be empty or whitespace only."
        )

    try:
        response = ComplaintGeneratorService.generate_complaint(
            request=request
        )
        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error generating complaint draft: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while generating the legal complaint draft. Please try again."
        )


@router.post(
    "/export-docx",
    summary="Export Complaint Draft to Word (.docx)",
    description="Generates an in-memory downloadable Microsoft Word (.docx) document formatted to standard Indian legal layout."
)
def export_docx(
    request: ComplaintExportDocxRequest
):
    """
    Exports a generated complaint response or raw complaint request payload into a .docx stream.
    """
    try:
        # If draft response is provided directly
        if request.draft:
            draft_obj = request.draft
        elif request.request_data:
            draft_obj = ComplaintGeneratorService.generate_complaint(
                request=request.request_data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either 'draft' response or 'request_data' must be supplied for DOCX export."
            )

        docx_stream = ComplaintGeneratorService.generate_docx(draft_obj)
        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.strftime("%Y%m%d_%H%M%S")
        filename = f"Vidhik_Complaint_Draft_{timestamp}.docx"

        return StreamingResponse(
            docx_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating DOCX export: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate DOCX document."
        )


@router.get(
    "/health",
    summary="Complaint Generator Subsystem Health",
    description="Returns operational status and capabilities of the Complaint / FIR generator."
)
def complaint_generator_health():
    """
    Returns diagnostic health information for the Complaint / FIR Generator.
    """
    return {
        "status": "operational",
        "subsystem": "Vidhik Complaint / FIR Generator",
        "version": "1.0.0",
        "supported_complaint_types": [
            "police_fir_request",
            "police_nc_complaint"
        ],
        "supported_languages": ["en", "mr", "hi"],
        "docx_export_enabled": True,
        "anti_fabrication_safety": True,
        "prompt_injection_defense": True,
        "pii_logging_protection": True,
        "statutory_grounding": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS Sec 173/174)"
    }
