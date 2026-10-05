import logging
from fastapi import APIRouter, HTTPException, status
from app.services.ai_evaluation_service import AIEvaluationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-evaluation", tags=["AI Quality & Diagnostics"])


@router.get("/run-suite")
def run_ai_evaluation_suite():
    """
    Executes automated quality, safety, citation grounding, and multilingual benchmarks across all AI engines.
    """
    try:
        return AIEvaluationService.run_full_evaluation()
    except Exception as e:
        logger.error(f"Error executing AI evaluation suite: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while executing the AI evaluation suite."
        )


@router.get("/health")
def ai_evaluation_health():
    """
    Health check for AI Evaluation & Diagnostics service.
    """
    return {
        "status": "healthy",
        "service": "ai_evaluation_service",
        "benchmark_suites": [
            "prompt_injection_defense",
            "forgery_fabrication_defense",
            "emergency_interception",
            "multilingual_marathi_emergency",
            "legal_issue_classification",
            "statutory_element_verification",
            "constitutional_rights_engine",
            "traffic_legal_engine",
            "authority_recommendation",
            "intent_routing"
        ]
    }
