import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.voice import VoiceTranscriptionRequest, VoiceTranscriptionResponse
from app.services.voice_service import VoiceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["Voice / STT Intelligence"])


@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
def transcribe_voice(request: VoiceTranscriptionRequest):
    """
    Transcribes spoken voice queries in English, Hindi, or Marathi using configured speech providers.
    """
    try:
        return VoiceService.transcribe_audio(request)
    except Exception as e:
        logger.error(f"Error during voice transcription: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing voice transcription."
        )


@router.get("/status")
def get_voice_status():
    """
    Returns voice transcription adapter configuration status and supported language profiles.
    """
    return VoiceService.get_status()


@router.get("/health")
def voice_health():
    """
    Health check for Voice / STT subsystem.
    """
    return {
        "status": "healthy",
        "service": "voice_service",
        "supported_languages": list(VoiceService.SUPPORTED_LANGUAGES.keys())
    }
