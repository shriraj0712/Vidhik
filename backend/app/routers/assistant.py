"""
Vidhik Platform - AI Legal Assistant API Router
================================================
FastAPI router providing conversational AI legal assistance and streaming chat on top of
the Phase 9 Legal RAG engine.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from psycopg2.extras import RealDictCursor

from app.database import get_db
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.assistant_service import LegalAssistantService
from app.services.llm_provider import get_llm_provider

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
    db: RealDictCursor = Depends(get_db)
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
            request=request
        )
        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing assistant chat '{clean_msg}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the assistant request. Please try again later."
        )


@router.post(
    "/chat/stream",
    summary="Stream Chat with AI Legal Assistant",
    description="Streams conversational response tokens using Server-Sent Events (SSE)."
)
def stream_chat_with_assistant(
    request: AssistantChatRequest,
    db: RealDictCursor = Depends(get_db)
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
        stream_generator = LegalAssistantService.chat_stream(
            db=db,
            request=request
        )
        return StreamingResponse(stream_generator, media_type="text/event-stream")
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
    provider = get_llm_provider()
    return {
        "status": "operational",
        "subsystem": "Vidhik AI Legal Assistant",
        "underlying_rag_engine": "Phase 9 Grounded Statutory RAG",
        "llm_provider": provider.provider_name,
        "conversation_store": "InMemoryConversationStore (Bounded)",
        "multilingual_support": ["en", "mr", "hi"],
        "streaming_supported": True,
        "grounding_enforced": True
    }
