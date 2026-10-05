from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VoiceTranscriptionRequest(BaseModel):
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio stream")
    audio_format: Optional[str] = Field("wav", description="Audio format container (wav, mp3, ogg, webm)")
    language_code: Optional[str] = Field("en-IN", description="Target BCP-47 language tag (en-IN, hi-IN, mr-IN)")
    sample_rate_hertz: Optional[int] = Field(16000, description="Sample rate in Hz")


class VoiceTranscriptionResponse(BaseModel):
    is_available: bool = Field(..., description="Whether a live speech-to-text backend is currently connected and active")
    provider_name: str = Field(..., description="Configured or default STT provider identifier")
    transcription_text: Optional[str] = Field(None, description="Transcribed textual query")
    confidence: Optional[float] = Field(None, description="Transcription confidence (0.0 to 1.0)")
    detected_language: Optional[str] = Field(None, description="Detected audio language code")
    status_message: str = Field(..., description="Operational status or explicit unavailable provider notice")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic and provider metadata")
