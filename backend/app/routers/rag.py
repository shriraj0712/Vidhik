"""
Vidhik Platform - Legal RAG API Router
======================================
FastAPI endpoints for grounded legal question answering, statutory context
retrieval, and AI synthesis with verified citations.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.rag import RAGQueryRequest, RAGResponse
from app.services.rag_service import LegalRAGService
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger("vidhik.rag_router")

router = APIRouter(prefix="/api/rag", tags=["RAG"])


@router.post(
    "/query",
    response_model=RAGResponse,
    summary="Query Legal Knowledge (RAG)",
    description="""
    Performs grounded statutory legal retrieval and AI synthesis.
    
    1. Analyzes the question using `LegalQueryService` and resolves multilingual statutory terminology.
    2. Retrieves matching legal sections from the PostgreSQL database using deterministic multi-field search.
    3. Ranks candidates using `LegalRankingService` (10-tier legal evidence hierarchy).
    4. Packages verified provisions with `LegalContextBuilder`.
    5. Synthesizes a factual explanation strictly grounded in retrieved provisions, citing exact Act names and Section numbers.
    """
)
def query_legal_rag(
    request: RAGQueryRequest,
    db: RealDictCursor = Depends(get_db)
):
    """
    Primary RAG endpoint: accepts a legal question and returns an evidence-grounded answer.
    """
    clean_q = request.query.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Legal query must not be empty or whitespace only."
        )

    try:
        response = LegalRAGService.query(
            db=db,
            request=request
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing RAG query '{clean_q}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during legal retrieval and synthesis. Please try again later."
        )


@router.get(
    "/health",
    summary="RAG Subsystem Health & Status",
    description="Returns the active LLM provider and RAG subsystem operational status."
)
def rag_health():
    """
    Returns diagnostics on RAG subsystem and configured LLM provider.
    """
    provider = get_llm_provider()
    return {
        "status": "operational",
        "subsystem": "Vidhik Legal RAG Engine",
        "llm_provider": provider.provider_name,
        "retrieval_backend": "PostgreSQL (vidhik_db) + Deterministic Ranking",
        "grounding_enforced": True
    }
