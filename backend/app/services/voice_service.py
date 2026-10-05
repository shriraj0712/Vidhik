import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from app.schemas.voice import VoiceTranscriptionRequest, VoiceTranscriptionResponse

logger = logging.getLogger(__name__)


class BaseVoiceProvider(ABC):
    """
    Abstract contract for Indian multilingual Speech-to-Text (STT) providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    def transcribe(self, request: VoiceTranscriptionRequest) -> VoiceTranscriptionResponse:
        pass


class UnconfiguredVoiceProvider(BaseVoiceProvider):
    """
    Default unconfigured voice provider.
    Explicitly informs callers that no external STT provider is active rather than fabricating results.
    """

    @property
    def provider_name(self) -> str:
        return "unconfigured_stt_provider"

    @property
    def is_configured(self) -> bool:
        return False

    def transcribe(self, request: VoiceTranscriptionRequest) -> VoiceTranscriptionResponse:
        return VoiceTranscriptionResponse(
            is_available=False,
            provider_name=self.provider_name,
            transcription_text=None,
            confidence=None,
            detected_language=None,
            status_message=(
                "Voice Speech-to-Text (STT) backend is currently unconfigured. "
                "VIDHIK AI supports pluggable STT adapters (e.g., Bhashini, Google Cloud Speech, OpenAI Whisper) "
                "when appropriate API credentials are configured in the environment."
            ),
            metadata={
                "supported_languages": ["en-IN", "hi-IN", "mr-IN"],
                "supported_codecs": ["wav", "mp3", "ogg", "webm"],
                "adapter_status": "standby"
            }
        )


class VoiceService:
    """
    Voice Intelligence Service Manager.
    Orchestrates speech transcription requests through configured Indian language speech providers.
    """

    SUPPORTED_LANGUAGES = {
        "en-IN": "Indian English",
        "hi-IN": "Hindi (Devanagari)",
        "mr-IN": "Marathi (Devanagari)"
    }

    @classmethod
    def get_active_provider(cls) -> BaseVoiceProvider:
        # Check if any live provider credentials are set
        if os.getenv("BHASHINI_API_KEY") or os.getenv("GOOGLE_SPEECH_API_KEY"):
            # Future integration hook for live provider
            pass
        return UnconfiguredVoiceProvider()

    @classmethod
    def transcribe_audio(cls, request: VoiceTranscriptionRequest) -> VoiceTranscriptionResponse:
        provider = cls.get_active_provider()
        return provider.transcribe(request)

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        provider = cls.get_active_provider()
        return {
            "status": "operational" if provider.is_configured else "unconfigured_standby",
            "active_provider": provider.provider_name,
            "is_available": provider.is_configured,
            "supported_languages": cls.SUPPORTED_LANGUAGES,
            "supported_formats": ["wav", "mp3", "ogg", "webm"]
        }
