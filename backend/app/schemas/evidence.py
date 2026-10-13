"""
Vidhik Platform - Video Evidence Schemas
========================================
Pydantic models for video evidence upload, chain-of-custody tracking,
audio transcript segments, visual frame observations, and structured legal reports.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegment(BaseModel):
    """Machine-generated transcript segment with precise timestamps."""
    model_config = ConfigDict(from_attributes=True)

    segment_index: int = Field(..., description="Chronological index of segment")
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    text: str = Field(..., description="Recognized speech text")
    speaker: Optional[str] = Field(default=None, description="Speaker identifier if detected")
    confidence: Optional[float] = Field(default=None, description="Recognition confidence score")


class VisualObservation(BaseModel):
    """Neutral visual observation from sampled video frames."""
    model_config = ConfigDict(from_attributes=True)

    observation_id: Optional[int] = Field(default=None, description="Unique observation ID")
    timestamp_seconds: float = Field(..., description="Frame timestamp in seconds")
    frame_reference: Optional[str] = Field(default=None, description="Relative path or reference to frame thumbnail")
    category: str = Field(default="observation", description="Category: movement, person, object, physical_mark, scene_change")
    description: str = Field(..., description="Detailed neutral description of observable elements")
    neutral_observation: str = Field(..., description="Non-assertive description avoiding intent/guilt inferences")
    visible_physical_marks: Optional[str] = Field(default=None, description="Neutral description of any observable mark, strictly non-diagnostic")
    uncertainty_or_limitation: Optional[str] = Field(default=None, description="Image quality limitations (blur, low light, occlusion)")
    confidence: Optional[float] = Field(default=None, description="Observation confidence score")


class EvidenceReportSummary(BaseModel):
    """Structured evidence-analysis report and Indian legal guidance."""
    model_config = ConfigDict(from_attributes=True)

    report_id: Optional[int] = Field(default=None)
    evidence_id: int = Field(...)
    summary: str = Field(..., description="Comprehensive objective summary of video evidence")
    chronological_summary: List[Dict[str, Any]] = Field(default_factory=list, description="Ordered timeline of audio and visual events")
    observable_events: List[Dict[str, Any]] = Field(default_factory=list, description="Neutral visual events identified")
    visible_physical_marks: List[Dict[str, Any]] = Field(default_factory=list, description="Observable physical marks with disclaimers")
    user_statements: List[Dict[str, Any]] = Field(default_factory=list, description="Separately attributed user statements")
    ai_interpretations: List[Dict[str, Any]] = Field(default_factory=list, description="Clearly labeled AI analytical observations")
    technical_limitations: List[str] = Field(default_factory=list, description="Technical boundaries, unverified elements, and media limitations")
    preservation_guidelines: List[str] = Field(default_factory=list, description="Chain of custody and BSA 2023 Sec 63 guidance")
    legal_provisions: List[Dict[str, Any]] = Field(default_factory=list, description="Applicable Indian statutory provisions (BNS, BNSS, BSA)")
    status_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of completed, partial, or unavailable components")


class EvidenceUploadResponse(BaseModel):
    """Initial upload and processing acknowledgment."""
    model_config = ConfigDict(from_attributes=True)

    evidence_id: int = Field(..., description="Unique evidence tracking identifier")
    user_id: int = Field(..., description="Authenticated owner user ID")
    conversation_id: Optional[str] = Field(default=None, description="Associated assistant conversation ID")
    original_filename: str = Field(..., description="Original client filename")
    file_size_bytes: int = Field(..., description="File size in bytes")
    media_container: str = Field(..., description="Verified container format (mp4, webm, mov, avi, mkv)")
    file_hash_sha256: str = Field(..., description="Cryptographic SHA-256 integrity hash")
    duration_seconds: Optional[float] = Field(default=None, description="Duration in seconds")
    resolution: Optional[str] = Field(default=None, description="Video dimensions WxH")
    has_audio: bool = Field(default=True, description="Whether recording contains an audio track")
    processing_status: str = Field(..., description="Current processing state: uploaded, validating, transcribing, analyzing_frames, completed, etc.")
    error_message: Optional[str] = Field(default=None, description="Error explanation if processing failed")
    created_at: str = Field(..., description="Upload timestamp")


class EvidenceDetailResponse(BaseModel):
    """Full evidence detail including transcripts, observations, and structured report."""
    model_config = ConfigDict(from_attributes=True)

    evidence_id: int
    user_id: int
    conversation_id: Optional[str] = None
    original_filename: str
    file_size_bytes: int
    media_container: str
    file_hash_sha256: str
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    has_audio: bool = True
    processing_status: str
    error_message: Optional[str] = None
    transcripts: List[TranscriptSegment] = Field(default_factory=list)
    observations: List[VisualObservation] = Field(default_factory=list)
    report: Optional[EvidenceReportSummary] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class EvidenceListResponse(BaseModel):
    """List of evidence items for the authenticated user."""
    model_config = ConfigDict(from_attributes=True)

    items: List[EvidenceUploadResponse] = Field(default_factory=list)
    total: int = 0
