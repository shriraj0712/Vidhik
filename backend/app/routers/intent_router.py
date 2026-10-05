import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.intent_router import IntentRoutingRequest, IntentRoutingResponse
from app.services.intent_router_service import IntentRouterService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intent", tags=["Intent Router"])


@router.post("/route", response_model=IntentRoutingResponse)
def route_intent(request: IntentRoutingRequest):
    """
    Deterministically routes user input to the appropriate specialized legal engine.
    """
    try:
        return IntentRouterService.route_intent(request)
    except Exception as e:
        logger.error(f"Error during intent routing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while routing user intent."
        )


@router.get("/health")
def intent_health():
    """
    Health check and supported intents probe.
    """
    return {
        "status": "healthy",
        "service": "intent_router_service",
        "supported_intents": [c["intent"] for c in IntentRouterService.INTENT_CONFIG] + ["legal_question"]
    }
