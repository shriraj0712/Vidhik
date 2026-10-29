"""
Vidhik Platform - AI Legal Assistant API Router
================================================
FastAPI router providing conversational AI legal assistance and streaming chat on top of
the Phase 9 Legal RAG engine.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
import json
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.assistant_service import LegalAssistantService
from typing import Optional
from app.services.auth_service import get_optional_user
from app.services.llm_provider import check_llm_provider_readiness, get_llm_provider
from app.services.search_service import CandidateRetrievalError

logger = logging.getLogger("vidhik.assistant_router")

router = APIRouter(prefix="/api/assistant", tags=["Assistant"])


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="Chat with AI Legal Assistant",
    description="""
    Conversational AI Legal Assistant for Indian Statutory Law.
    
    1. Validates user prompt and session continuity (via `conversation_id` or `history`).
    2. Runs AI Safety Guardrails and Emergency Interception.
    3. Resolves contextual follow-up questions referencing prior turns.
    4. Delegates statutory retrieval and grounded synthesis to the Phase 9 Legal RAG engine.
    5. Enforces strict zero-hallucination standards with traceable database citations.
    """
)
def chat_with_assistant(
    request: AssistantChatRequest,
    db: RealDictCursor = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Primary chat endpoint for the AI Legal Assistant.
    """
    clean_msg = request.message.strip()
    if not clean_msg:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty or whitespace only."
        )

    # Validate against excessively large history payload
    if request.history is not None and len(request.history) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conversation history exceeds maximum permitted length of 100 turns."
        )

    try:
       response = LegalAssistantService.chat(
           db=db,
           request=request,
           current_user=current_user
       )

    except CandidateRetrievalError:
        logger.error("Assistant legal retrieval failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Legal retrieval is temporarily unavailable. Please try again."
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Assistant request failed (error_type=%s).", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the assistant request. Please try again later."
        )

    return response


@router.post(
    "/chat/stream",
    summary="Stream Chat with AI Legal Assistant",
    description="Streams conversational response tokens using Server-Sent Events (SSE)."
)
def stream_chat_with_assistant(
    request: AssistantChatRequest,
    db: RealDictCursor = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Streaming chat endpoint for the AI Legal Assistant.
    """
    clean_msg = request.message.strip()
    if not clean_msg:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty or whitespace only."
        )

    try:
        response = LegalAssistantService.chat(
            db=db,
            request=request,
            current_user=current_user
        )

        def event_stream():
            metadata = {"conversation_id": response.conversation_id, "is_grounded": response.is_grounded, "sources_count": len(response.sources)}
            yield "event: metadata\ndata: " + json.dumps(metadata) + "\n\n"
            words = response.answer.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield "event: message\ndata: " + json.dumps({"delta": chunk}) + "\n\n"
            yield "event: done\ndata: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error streaming assistant response: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while streaming assistant response."
        )


@router.get(
    "/health",
    summary="Assistant Subsystem Health & Status",
    description="Returns diagnostic status of the AI Legal Assistant orchestration layer."
)
def assistant_health():
    """
    Returns diagnostics on the Assistant subsystem and configured LLM provider.
    """
    provider = check_llm_provider_readiness()
    ready = provider.get("ready") is True
    payload = {
        "status": "operational" if ready else "degraded",
        "subsystem": "Vidhik AI Legal Assistant",
        "underlying_rag_engine": "Phase 9 Grounded Statutory RAG",
        "llm_provider": provider,
        "conversation_store": "InMemoryConversationStore (Bounded)",
        "multilingual_support": ["en", "mr", "hi"],
        "streaming_supported": True,
        "grounding_enforced": True
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)
