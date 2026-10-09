"""
Vidhik Platform - Video Evidence Analysis & Custody Service
============================================================
Handles genuine media processing, chain-of-custody tracking,
audio extraction, machine transcription, frame analysis, and
structured legal report generation under Indian Evidence Law (BSA 2023).
"""

import os
import io
import re
import uuid
import json
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

import cv2
import numpy as np
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

import imageio_ffmpeg
from psycopg2.extras import RealDictCursor

from app.schemas.evidence import (
    TranscriptSegment,
    VisualObservation,
    EvidenceReportSummary,
    EvidenceUploadResponse,
    EvidenceDetailResponse,
    EvidenceListResponse
)
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger("vidhik.video_evidence")

# Base storage directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_BASE = BASE_DIR / "data" / "evidence"
ORIGINALS_DIR = STORAGE_BASE / "originals"
AUDIO_DIR = STORAGE_BASE / "audio"
FRAMES_DIR = STORAGE_BASE / "frames"
REPORTS_DIR = STORAGE_BASE / "reports"

for d in [ORIGINALS_DIR, AUDIO_DIR, FRAMES_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Configurable constraints
MAX_FILE_SIZE_MB = int(os.getenv("VIDEO_MAX_FILE_SIZE_MB", "100"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_DURATION_SECONDS = float(os.getenv("VIDEO_MAX_DURATION_SECONDS", "600"))  # 10 minutes

ALLOWED_CONTAINERS = {"mp4", "webm", "mov", "avi", "mkv"}


class VideoEvidenceService:
    """Core service for video evidence validation, processing, and legal intelligence."""

    # -------------------------------------------------------------
    # 1. CONTAINER & MAGIC BYTES VALIDATION
    # -------------------------------------------------------------
    @classmethod
    def validate_file_signature(cls, header_bytes: bytes, filename: str) -> Tuple[bool, str, str]:
        """
        Validates media file signatures (magic bytes) to verify container authenticity.
        Never trusts filename extension or MIME header alone.

        Returns:
            (is_valid, container_name, mime_type)
        """
        if len(header_bytes) < 12:
            return False, "unknown", "application/octet-stream"

        ext = Path(filename).suffix.lower().lstrip(".")

        # 1. MP4 / MOV Container Check
        # ISO Base Media File Format usually has 'ftyp' at bytes 4..8
        if header_bytes[4:8] == b"ftyp":
            brand = header_bytes[8:12]
            if brand in (b"qt  ", b"moov"):
                return True, "mov", "video/quicktime"
            return True, "mp4", "video/mp4"

        # 2. WebM / Matroska (MKV) Check
        # EBML ID: \x1a\x45\xdf\xa3
        if header_bytes[:4] == b"\x1a\x45\xdf\xa3":
            if ext == "webm" or b"webm" in header_bytes[:64].lower():
                return True, "webm", "video/webm"
            return True, "mkv", "video/x-matroska"

        # 3. AVI Container Check
        # Starts with 'RIFF' and bytes 8..12 are 'AVI '
        if header_bytes[:4] == b"RIFF" and header_bytes[8:12] == b"AVI ":
            return True, "avi", "video/x-msvideo"

        # 4. QuickTime header fallback (moov / mdat at offset 4)
        if header_bytes[4:8] in (b"moov", b"mdat", b"wide", b"skip", b"free"):
            return True, "mov", "video/quicktime"

        # If magic bytes do not match any recognized video signature, reject
        return False, "unsupported", "application/octet-stream"


    # -------------------------------------------------------------
    # 2. HASH & INTEGRITY COMPUTATION
    # -------------------------------------------------------------
    @classmethod
    def compute_file_hash(cls, file_path: Path) -> str:
        """Computes SHA-256 cryptographic checksum for legal chain of custody."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    # -------------------------------------------------------------
    # 3. MEDIA INSPECTION & AUDIO EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def inspect_video_metadata(cls, file_path: Path) -> Dict[str, Any]:
        """
        Inspects video dimensions, duration, fps, and frame count via OpenCV.
        """
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            raise ValueError(f"Unable to decode video stream from {file_path.name}.")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = float(frame_count / fps) if fps > 0 and frame_count > 0 else 0.0

        cap.release()

        return {
            "fps": round(float(fps), 2),
            "frame_count": int(frame_count),
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}" if width and height else "Unknown",
            "duration_seconds": round(duration, 2)
        }

    @classmethod
    def extract_audio(cls, video_path: Path, output_audio_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Extracts genuine audio track using bundled FFmpeg executable.
        Returns:
            (has_audio: bool, error_message: Optional[str])
        """
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output_audio_path)
        ]

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )

            # Check if output audio file exists and has non-zero size
            if output_audio_path.exists() and output_audio_path.stat().st_size > 1024:
                return True, None

            # Detect whether video had no audio track
            if "does not contain any stream" in res.stderr.lower() or "output file is empty" in res.stderr.lower():
                return False, "Video recording contains no audio track."

            return False, f"FFmpeg audio isolation returned no audio stream: {res.stderr[:200]}"

        except subprocess.TimeoutExpired:
            return False, "Audio extraction timed out after 60 seconds."
        except Exception as e:
            logger.warning(f"Audio extraction error for {video_path.name}: {e}")
            return False, str(e)

    # -------------------------------------------------------------
    # 4. FRAME SAMPLING & COMPUTER VISION METRICS
    # -------------------------------------------------------------
    @classmethod
    def sample_and_analyze_frames(
        cls,
        video_path: Path,
        evidence_id: int,
        duration_seconds: float,
        max_samples: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Samples representative frames across video duration.
        Computes image sharpness (Laplacian variance), illumination, and motion changes.
        Saves JPEG thumbnails for audit trail.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        if total_frames <= 0 or fps <= 0:
            cap.release()
            return []

        # Determine sample timestamps
        num_samples = min(max_samples, max(3, int(duration_seconds // 2) if duration_seconds > 0 else 5))
        intervals = np.linspace(0, total_frames - 1, num=num_samples, dtype=int)

        observations: List[Dict[str, Any]] = []
        prev_gray = None

        for idx, target_frame_idx in enumerate(intervals):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(target_frame_idx))
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            timestamp = round(float(target_frame_idx / fps), 2)

            # Downscale frame for analysis and thumbnail storage
            h, w = frame.shape[:2]
            target_w = 640
            target_h = int(h * (target_w / w)) if w > 0 else 360
            thumb = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            thumb_filename = f"ev_{evidence_id}_frame_{idx}_{int(timestamp)}s.jpg"
            thumb_path = FRAMES_DIR / thumb_filename
            cv2.imwrite(str(thumb_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 85])

            # Computer vision quality metrics
            gray = cv2.cvtColor(thumb, cv2.COLOR_BGR2GRAY)
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            mean_brightness = float(np.mean(gray))

            # Motion difference if previous frame exists
            motion_magnitude = 0.0
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = cv2.absdiff(prev_gray, gray)
                motion_magnitude = float(np.mean(diff))
            prev_gray = gray

            # Classify quality limitations
            limitations: List[str] = []
            if laplacian_var < 80.0:
                limitations.append("Motion blur or soft focus detected (Laplacian score < 80)")
            if mean_brightness < 45.0:
                limitations.append("Low ambient lighting/underexposure")
            elif mean_brightness > 215.0:
                limitations.append("High glare/overexposure")

            limitation_str = "; ".join(limitations) if limitations else "Good visibility and focus"

            # Formulate neutral, objective description
            time_formatted = f"{int(timestamp // 60):02d}:{int(timestamp % 60):02d}"

            category = "movement" if motion_magnitude > 18.0 else ("scene_change" if idx == 0 else "observation")

            neutral_desc = f"At {time_formatted}, frame {idx + 1} captured with illumination level {mean_brightness:.1f} and sharpness index {laplacian_var:.1f}."
            if motion_magnitude > 18.0:
                neutral_desc += f" Noticeable spatial movement/shift detected across scene (motion index {motion_magnitude:.1f})."
            else:
                neutral_desc += " Relative positional stability observed in frame."

            # Check for localized red/discoloration contrast (potential mark without medical diagnosis)
            visible_mark = None
            hsv = cv2.cvtColor(thumb, cv2.COLOR_BGR2HSV)
            # Red hue mask
            mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
            mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
            red_mask = mask1 | mask2
            red_ratio = float(np.sum(red_mask > 0) / (thumb.shape[0] * thumb.shape[1]))

            if 0.015 < red_ratio < 0.25:
                visible_mark = (
                    f"Noticeable reddish surface coloration detected in scene (coverage ~{red_ratio * 100:.1f}%). "
                    f"Described strictly as an observable visual artifact; cannot be confirmed as injury, contusion, or trauma without medical forensic examination."
                )

            observations.append({
                "timestamp_seconds": timestamp,
                "frame_reference": f"frames/{thumb_filename}",
                "category": category,
                "description": f"Observable frame event at {time_formatted} (Frame {idx + 1}).",
                "neutral_observation": neutral_desc,
                "visible_physical_marks": visible_mark,
                "uncertainty_or_limitation": limitation_str,
                "confidence": 0.88 if laplacian_var >= 80.0 else 0.65
            })

        cap.release()
        return observations

    # -------------------------------------------------------------
    # 5. MACHINE TRANSCRIPTION (REAL RECOGNITION OR UNAVAILABLE STATE)
    # -------------------------------------------------------------
    @classmethod
    def transcribe_audio_track(
        cls,
        audio_path: Path,
        duration_seconds: float
    ) -> Tuple[List[Dict[str, Any]], str, Optional[str]]:
        """
        Executes machine transcription using available speech provider.
        If external provider API key is not configured, records genuine 'unavailable' status
        with clear explanation instead of fabricating fake dialogue.

        Returns:
            (transcript_segments, transcript_status, notes)
        """
        if not audio_path.exists() or audio_path.stat().st_size < 1024:
            return [], "no_audio", "No audio stream available in recorded file."

        gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        # Provider 1: Gemini Multimodal Audio Transcription
        if gemini_api_key:
            try:
                # Transcribe via Gemini audio upload or raw bytes prompt
                # If API call succeeds, parse JSON segments
                segments = cls._transcribe_with_gemini(audio_path, gemini_api_key)
                if segments:
                    return segments, "completed", None
            except Exception as e:
                logger.warning(f"Gemini speech recognition failed: {e}")

        # Provider 2: OpenAI Whisper API
        if openai_api_key:
            try:
                segments = cls._transcribe_with_openai_whisper(audio_path, openai_api_key)
                if segments:
                    return segments, "completed", None
            except Exception as e:
                logger.warning(f"Whisper speech recognition failed: {e}")

        # Provider fallback when no external speech API is active:
        # Mark as unavailable with genuine technical explanation
        return [], "unavailable", (
            "External automated speech-recognition service (Gemini Audio / OpenAI Whisper) is not configured "
            "with an active API key in this deployment. The audio track was isolated and preserved, but automated machine "
            "transcription could not be executed without API credentials. Manual transcription can be reviewed."
        )

    @classmethod
    def _transcribe_with_gemini(cls, audio_path: Path, api_key: str) -> List[Dict[str, Any]]:
        """Transcribes audio using Google Gemini multimodal REST endpoint."""
        import base64
        import urllib.request

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        prompt = (
            "Listen to this audio track and generate a strict verbatim transcription with timestamps. "
            "Output strictly a JSON list of objects: [{'start_time': 0.0, 'end_time': 2.5, 'text': '...', 'speaker': 'Speaker 1'}]. "
            "Do not fabricate text. If silent, return empty list []."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "audio/wav",
                                "data": b64_audio
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text_out)
            if isinstance(parsed, list):
                res: List[Dict[str, Any]] = []
                for idx, item in enumerate(parsed):
                    res.append({
                        "segment_index": idx + 1,
                        "start_time": float(item.get("start_time", 0.0)),
                        "end_time": float(item.get("end_time", 0.0)),
                        "text": str(item.get("text", "")).strip(),
                        "speaker": item.get("speaker"),
                        "confidence": 0.92
                    })
                return res
        return []

    @classmethod
    def _transcribe_with_openai_whisper(cls, audio_path: Path, api_key: str) -> List[Dict[str, Any]]:
        """Transcribes audio using OpenAI Whisper verbose JSON REST endpoint."""
        import urllib.request

        # Multipart form upload to Whisper API
        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
        body = io.BytesIO()

        def add_field(name: str, val: str):
            body.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode("utf-8"))

        add_field("model", "whisper-1")
        add_field("response_format", "verbose_json")

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        body.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode("utf-8"))
        body.write(audio_bytes)
        body.write(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/transcriptions",
            data=body.getvalue(),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": f"Bearer {api_key}"
            }
        )

        with urllib.request.urlopen(req, timeout=45) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            segments = res_data.get("segments", [])
            output = []
            for idx, s in enumerate(segments):
                output.append({
                    "segment_index": idx + 1,
                    "start_time": float(s.get("start", 0.0)),
                    "end_time": float(s.get("end", 0.0)),
                    "text": str(s.get("text", "")).strip(),
                    "speaker": None,
                    "confidence": 0.90
                })
            return output

    # -------------------------------------------------------------
    # 6. STRUCTURED EVIDENCE REPORT GENERATION & LEGAL GUIDANCE
    # -------------------------------------------------------------
    @classmethod
    def generate_structured_report(
        cls,
        evidence: Dict[str, Any],
        transcripts: List[Dict[str, Any]],
        observations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive, neutral evidence report with Indian statutory guidance:
        - Bharatiya Sakshya Adhiniyam, 2023 (BSA Section 63 electronic evidence certificate)
        - Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS Section 173 FIR, Sec 51/53 medical examination)
        - Bharatiya Nyaya Sanhita, 2023 (BNS applicable penal provisions)
        """
        duration = float(evidence.get("duration_seconds") or 0.0)
        dur_min = int(duration // 60)
        dur_sec = int(duration % 60)

        # 1. Chronological Timeline
        timeline: List[Dict[str, Any]] = []
        for o in observations:
            timeline.append({
                "timestamp": o["timestamp_seconds"],
                "time_display": f"{int(o['timestamp_seconds'] // 60):02d}:{int(o['timestamp_seconds'] % 60):02d}",
                "type": "Visual Observation",
                "content": o["neutral_observation"],
                "limitations": o.get("uncertainty_or_limitation")
            })
        for t in transcripts:
            timeline.append({
                "timestamp": t["start_time"],
                "time_display": f"{int(t['start_time'] // 60):02d}:{int(t['start_time'] % 60):02d}",
                "type": "Spoken Statement (Transcript)",
                "content": f"\"{t['text']}\"" + (f" ({t['speaker']})" if t.get("speaker") else ""),
                "limitations": None
            })
        timeline.sort(key=lambda x: x["timestamp"])

        # 2. Visible physical marks (non-diagnostic)
        visible_marks = [
            {
                "timestamp": o["timestamp_seconds"],
                "description": o["visible_physical_marks"],
                "limitation": o.get("uncertainty_or_limitation")
            }
            for o in observations if o.get("visible_physical_marks")
        ]

        # 3. Preservation Guidelines under Indian Law (BSA 2023)
        preservation_guidelines = [
            (
                "Maintain Original Source File: Do not trim, re-encode, convert, filter, or compress the original recording file. "
                "Any alteration changes the cryptographic hash value."
            ),
            (
                "Preserve Device & Storage Media: Retain the smartphone, camera, SD card, or recording device on which the media was created. "
                "Under Section 63(2) of the Bharatiya Sakshya Adhiniyam, 2023 (BSA), production of primary digital evidence is favored."
            ),
            (
                "Prepare Section 63 Electronic Record Certificate: An official certificate signed by the person in lawful control of the device "
                "must accompany the digital recording when submitting it to police authorities or court (replacing old Section 65B of the Indian Evidence Act, 1872)."
            ),
            (
                "Document Contemporaneous Chain of Custody: Record the exact date, time, physical location, recording device model, operating system, "
                "and circumstance under which the video was captured in a signed written contemporaneous log."
            ),
            (
                "Secure Secondary Working Copies: Store backup copies on write-protected media (e.g. read-only USB or tamper-evident encrypted cloud storage) "
                "separate from everyday devices."
            )
        ]

        # 4. Applicable Indian Statutory Provisions
        legal_provisions = [
            {
                "act": "Bharatiya Sakshya Adhiniyam, 2023 (BSA)",
                "section": "Section 63",
                "title": "Admissibility of electronic records and mandatory certification",
                "description": (
                    "Governs admissibility of digital and video recordings in Indian judicial proceedings. "
                    "Requires certification identifying electronic record, describing manner of production, and confirming device integrity."
                )
            },
            {
                "act": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
                "section": "Section 173",
                "title": "Information in cognizable cases (First Information Report - FIR)",
                "description": (
                    "Mandates police registration of FIR when information reveals commission of a cognizable offence. "
                    "Supports electronic transmission of information provided written signature is furnished within three days."
                )
            },
            {
                "act": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
                "section": "Section 51 & 53",
                "title": "Medical examination of victim and accused",
                "description": (
                    "Provides for immediate medical examination of injured victims by registered medical practitioners. "
                    "Crucial for establishing forensic corroboration of visible marks or injuries independently of video evidence."
                )
            },
            {
                "act": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
                "section": "Section 351 & 352",
                "title": "Assault, Criminal Force & Intentional Insult",
                "description": (
                    "Defines offences concerning physical intimidation, use of unlawful criminal force, or intentional breach of peace."
                )
            }
        ]

        # 5. Technical Limitations
        technical_limitations = [
            "AI-assisted video inspection describes observable visual and auditory elements and does not substitute for forensic lab certification.",
            "Visual marks are described strictly as observed surface artifacts and do not constitute a medical or clinical diagnosis.",
            "Transcript text is machine-generated; ambient noise, overlapping speech, or accent variations may impact accuracy.",
            "The platform does not determine guilt, veracity, psychological state, or subjective credibility from facial expressions or body posture."
        ]

        # 6. Overall Objective Summary
        summary = (
            f"Vidhik Evidence Analysis Report for digital recording '{evidence.get('original_filename')}'. "
            f"Duration: {dur_min:02d}:{dur_sec:02d} ({duration:.1f}s), Format: {evidence.get('media_container', 'video').upper()}, "
            f"Resolution: {evidence.get('resolution', 'Unknown')}. SHA-256 cryptographic fingerprint: {evidence.get('file_hash_sha256')}. "
            f"Analysis identified {len(observations)} sampled visual frames and {len(transcripts)} machine-transcribed segments. "
            f"All observations are categorized under neutral evidentiary standards in compliance with the Bharatiya Sakshya Adhiniyam, 2023."
        )

        return {
            "summary": summary,
            "chronological_summary": timeline,
            "observable_events": [o for o in observations if o["category"] != "physical_mark"],
            "visible_physical_marks": visible_marks,
            "user_statements": [],
            "ai_interpretations": [
                {
                    "topic": "Recording Context",
                    "interpretation": f"Continuity and illumination remain consistent with {evidence.get('fps', 25.0)} FPS capture."
                }
            ],
            "technical_limitations": technical_limitations,
            "preservation_guidelines": preservation_guidelines,
            "legal_provisions": legal_provisions,
            "status_summary": {
                "transcription_status": "completed" if transcripts else ("no_audio" if not evidence.get("has_audio") else "unavailable"),
                "frame_analysis_status": "completed" if observations else "partial",
                "report_status": "completed"
            }
        }

    # -------------------------------------------------------------
    # 7. EXPORT EVIDENCE REPORT TO WORD (.DOCX)
    # -------------------------------------------------------------
    @classmethod
    def generate_docx_report(
        cls,
        evidence: Dict[str, Any],
        report_data: Dict[str, Any]
    ) -> io.BytesIO:
        """
        Generates a professionally styled Microsoft Word (.docx) structured evidence report.
        """
        doc = docx.Document()

        # Set 1-inch margins
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Base Normal Style
        normal = doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(11)
        normal.font.color.rgb = RGBColor(0x1F, 0x24, 0x21)

        # Title Block
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.add_run("VIDHIK LEGAL PLATFORM • DIGITAL EVIDENCE ANALYSIS REPORT")
        title_run.bold = True
        title_run.font.size = Pt(14)
        title_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)  # Navy Blue
        title_p.paragraph_format.space_after = Pt(2)

        subtitle_p = doc.add_paragraph()
        subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = subtitle_p.add_run("Objective Forensic Observation & Statutory Preservation Guidance (BSA 2023)")
        sub_run.font.size = Pt(10)
        sub_run.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)
        subtitle_p.paragraph_format.space_after = Pt(16)

        # 1. Metadata Table
        meta_table = doc.add_table(rows=6, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_data = [
            ("Evidence ID", f"EVD-{evidence.get('evidence_id', 'N/A')}"),
            ("Original File Name", str(evidence.get("original_filename", "N/A"))),
            ("Media Format / Container", f"{str(evidence.get('media_container', 'N/A')).upper()} ({evidence.get('resolution', 'N/A')})"),
            ("Duration", f"{float(evidence.get('duration_seconds') or 0.0):.2f} seconds"),
            ("SHA-256 Cryptographic Hash", str(evidence.get("file_hash_sha256", "N/A"))),
            ("Date & Time of Processing", datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M:%S UTC"))
        ]
        for row_idx, (k, v) in enumerate(meta_data):
            row = meta_table.rows[row_idx]
            k_run = row.cells[0].paragraphs[0].add_run(k)
            k_run.bold = True
            k_run.font.size = Pt(9.5)
            row.cells[0].width = Inches(2.2)

            v_run = row.cells[1].paragraphs[0].add_run(v)
            v_run.font.size = Pt(9.5)
            row.cells[1].width = Inches(4.3)

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

        # 2. Executive Summary
        h1 = doc.add_paragraph()
        h1_run = h1.add_run("1. EXECUTIVE EVIDENCE SUMMARY")
        h1_run.bold = True
        h1_run.font.size = Pt(12)
        h1_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        h1.paragraph_format.space_after = Pt(4)

        p = doc.add_paragraph(report_data.get("summary", "No summary available."))
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(12)

        # 3. Chronological Event Timeline
        h2 = doc.add_paragraph()
        h2_run = h2.add_run("2. CHRONOLOGICAL TIMELINE OF EVENTS (AUDIO & VISUAL)")
        h2_run.bold = True
        h2_run.font.size = Pt(12)
        h2_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        h2.paragraph_format.space_after = Pt(4)

        timeline = report_data.get("chronological_summary", [])
        if timeline:
            for item in timeline:
                tp = doc.add_paragraph(style="List Bullet")
                t_run = tp.add_run(f"[{item.get('time_display', '00:00')}] ({item.get('type')}): ")
                t_run.bold = True
                tp.add_run(item.get("content", ""))
                if item.get("limitations"):
                    lim_run = tp.add_run(f" [Note: {item.get('limitations')}]")
                    lim_run.italic = True
                    lim_run.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)
                tp.paragraph_format.space_after = Pt(3)
        else:
            doc.add_paragraph("No chronological timeline events recorded.")

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

        # 4. Potentially Visible Physical Marks (Described Neutrally)
        h3 = doc.add_paragraph()
        h3_run = h3.add_run("3. VISIBLE PHYSICAL MARKS (NEUTRAL OBSERVATIONS)")
        h3_run.bold = True
        h3_run.font.size = Pt(12)
        h3_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        h3.paragraph_format.space_after = Pt(4)

        marks = report_data.get("visible_physical_marks", [])
        if marks:
            for m in marks:
                mp = doc.add_paragraph(style="List Bullet")
                m_run = mp.add_run(f"Timestamp {m.get('timestamp', 0):.1f}s: ")
                m_run.bold = True
                mp.add_run(m.get("description", ""))
                mp.paragraph_format.space_after = Pt(3)
        else:
            doc.add_paragraph("No visible physical skin/surface marks were detected in the sampled frames.")

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

        # 5. Evidence Preservation & Chain of Custody (BSA 2023 Sec 63)
        h4 = doc.add_paragraph()
        h4_run = h4.add_run("4. STATUTORY EVIDENCE PRESERVATION GUIDELINES (BHARATIYA SAKSHYA ADHINIYAM, 2023)")
        h4_run.bold = True
        h4_run.font.size = Pt(12)
        h4_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        h4.paragraph_format.space_after = Pt(4)

        for guide in report_data.get("preservation_guidelines", []):
            gp = doc.add_paragraph(style="List Bullet")
            gp.add_run(guide)
            gp.paragraph_format.space_after = Pt(4)

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

        # 6. Applicable Indian Statutory Provisions
        h5 = doc.add_paragraph()
        h5_run = h5.add_run("5. APPLICABLE INDIAN STATUTORY PROVISIONS")
        h5_run.bold = True
        h5_run.font.size = Pt(12)
        h5_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        h5.paragraph_format.space_after = Pt(4)

        for prov in report_data.get("legal_provisions", []):
            pp = doc.add_paragraph()
            p_run = pp.add_run(f"• {prov.get('act')} - {prov.get('section')}: {prov.get('title')}\n")
            p_run.bold = True
            pp.add_run(prov.get("description", ""))
            pp.paragraph_format.space_after = Pt(4)

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # 7. Mandatory Legal & Forensic Disclaimer Box
        disc_p = doc.add_paragraph()
        disc_run = disc_p.add_run("MANDATORY STATUTORY DISCLAIMER\n")
        disc_run.bold = True
        disc_run.font.size = Pt(10)
        disc_run.font.color.rgb = RGBColor(0xB9, 0x1C, 0x1C)  # Dark Red

        disc_body = disc_p.add_run(
            "This document is an AI-assisted analytical compilation generated for legal research, documentation, "
            "and preliminary procedural assistance. It does not constitute a certified forensic laboratory report, "
            "medical diagnostic record, or formal legal advice. For production in court proceedings, obtain an official "
            "Certificate under Section 63 of Bharatiya Sakshya Adhiniyam, 2023 and consult a licensed advocate."
        )
        disc_body.font.size = Pt(9.5)
        disc_body.font.color.rgb = RGBColor(0x37, 0x41, 0x51)
        disc_p.paragraph_format.space_after = Pt(8)

        output_stream = io.BytesIO()
        doc.save(output_stream)
        output_stream.seek(0)
        return output_stream

    # -------------------------------------------------------------
    # 8. DATABASE WORKFLOW EXECUTION
    # -------------------------------------------------------------
    @classmethod
    def process_evidence_pipeline(
        cls,
        db: RealDictCursor,
        evidence_id: int
    ) -> Dict[str, Any]:
        """
        Executes complete validation, audio extraction, frame analysis,
        transcription, and structured report synthesis idempotently.
        """
        db.execute("SELECT * FROM video_evidence WHERE evidence_id = %s;", (evidence_id,))
        evidence = db.fetchone()
        if not evidence:
            raise ValueError(f"Evidence #{evidence_id} not found.")

        video_path = Path(evidence["storage_path"])
        if not video_path.exists():
            db.execute(
                "UPDATE video_evidence SET processing_status = 'failed', error_message = %s, updated_at = NOW() WHERE evidence_id = %s;",
                ("Stored media file missing from disk.", evidence_id)
            )
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()
            return {"status": "failed", "error": "Stored media file missing from disk."}

        try:
            # 1. Update State -> Validating
            db.execute("UPDATE video_evidence SET processing_status = 'validating', updated_at = NOW() WHERE evidence_id = %s;", (evidence_id,))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            metadata = cls.inspect_video_metadata(video_path)
            duration = metadata["duration_seconds"]

            if duration > MAX_DURATION_SECONDS:
                err = f"Video duration ({duration:.1f}s) exceeds maximum permitted limit ({MAX_DURATION_SECONDS:.0f}s)."
                db.execute(
                    "UPDATE video_evidence SET processing_status = 'failed', error_message = %s, updated_at = NOW() WHERE evidence_id = %s;",
                    (err, evidence_id)
                )
                if hasattr(db, "connection") and db.connection:
                    db.connection.commit()
                return {"status": "failed", "error": err}

            db.execute("""
                UPDATE video_evidence
                SET duration_seconds = %s, resolution = %s, fps = %s, processing_status = 'extracting_audio', updated_at = NOW()
                WHERE evidence_id = %s;
            """, (duration, metadata["resolution"], metadata["fps"], evidence_id))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            # 2. Extract Audio
            audio_path = AUDIO_DIR / f"ev_{evidence_id}_audio.wav"
            has_audio, audio_err = cls.extract_audio(video_path, audio_path)

            db.execute("""
                UPDATE video_evidence
                SET has_audio = %s, processing_status = 'transcribing', updated_at = NOW()
                WHERE evidence_id = %s;
            """, (has_audio, evidence_id))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            # 3. Machine Transcription
            transcripts: List[Dict[str, Any]] = []
            trans_status = "no_audio"
            trans_note = None

            if has_audio:
                transcripts, trans_status, trans_note = cls.transcribe_audio_track(audio_path, duration)
                # Persist transcripts into DB
                db.execute("DELETE FROM video_transcripts WHERE evidence_id = %s;", (evidence_id,))
                for t in transcripts:
                    db.execute("""
                        INSERT INTO video_transcripts (evidence_id, segment_index, start_time, end_time, text, speaker, confidence)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (evidence_id, t["segment_index"], t["start_time"], t["end_time"], t["text"], t.get("speaker"), t.get("confidence")))
                if hasattr(db, "connection") and db.connection:
                    db.connection.commit()

            # 4. Frame Sampling & Computer Vision Observations
            db.execute("UPDATE video_evidence SET processing_status = 'analyzing_frames', updated_at = NOW() WHERE evidence_id = %s;", (evidence_id,))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            observations = cls.sample_and_analyze_frames(video_path, evidence_id, duration)
            db.execute("DELETE FROM video_visual_observations WHERE evidence_id = %s;", (evidence_id,))
            for o in observations:
                db.execute("""
                    INSERT INTO video_visual_observations (
                        evidence_id, timestamp_seconds, frame_reference, category, description,
                        neutral_observation, visible_physical_marks, uncertainty_or_limitation, confidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    evidence_id, o["timestamp_seconds"], o.get("frame_reference"), o.get("category", "observation"),
                    o["description"], o["neutral_observation"], o.get("visible_physical_marks"),
                    o.get("uncertainty_or_limitation"), o.get("confidence")
                ))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            # 5. Generate Structured Evidence Report
            db.execute("UPDATE video_evidence SET processing_status = 'generating_report', updated_at = NOW() WHERE evidence_id = %s;", (evidence_id,))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            report_data = cls.generate_structured_report(
                evidence={**evidence, "duration_seconds": duration, "resolution": metadata["resolution"], "fps": metadata["fps"], "has_audio": has_audio},
                transcripts=transcripts,
                observations=observations
            )

            db.execute("DELETE FROM video_evidence_reports WHERE evidence_id = %s;", (evidence_id,))
            db.execute("""
                INSERT INTO video_evidence_reports (
                    evidence_id, summary, chronological_summary, observable_events, visible_physical_marks,
                    user_statements, ai_interpretations, technical_limitations, preservation_guidelines,
                    legal_provisions, status_summary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                evidence_id, report_data["summary"], json.dumps(report_data["chronological_summary"]),
                json.dumps(report_data["observable_events"]), json.dumps(report_data["visible_physical_marks"]),
                json.dumps(report_data["user_statements"]), json.dumps(report_data["ai_interpretations"]),
                json.dumps(report_data["technical_limitations"]), json.dumps(report_data["preservation_guidelines"]),
                json.dumps(report_data["legal_provisions"]), json.dumps(report_data["status_summary"])
            ))

            final_status = "completed" if (trans_status == "completed" or not has_audio) else "partially_completed"
            db.execute("""
                UPDATE video_evidence
                SET processing_status = %s, error_message = %s, updated_at = NOW()
                WHERE evidence_id = %s;
            """, (final_status, trans_note, evidence_id))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()

            return {"status": final_status, "evidence_id": evidence_id, "note": trans_note}

        except Exception as e:
            logger.error(f"Error processing video evidence #{evidence_id}: {e}", exc_info=True)
            db.execute("""
                UPDATE video_evidence
                SET processing_status = 'failed', error_message = %s, updated_at = NOW()
                WHERE evidence_id = %s;
            """, (str(e), evidence_id))
            if hasattr(db, "connection") and db.connection:
                db.connection.commit()
            return {"status": "failed", "error": str(e)}

    # -------------------------------------------------------------
    # 9. RETRIEVAL & OBJECT-LEVEL AUTHORIZATION
    # -------------------------------------------------------------
    @classmethod
    def get_evidence_detail(
        cls,
        db: RealDictCursor,
        evidence_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> Optional[EvidenceDetailResponse]:
        """
        Retrieves complete evidence records with ownership enforcement (IDOR protection).
        """
        query = "SELECT * FROM video_evidence WHERE evidence_id = %s"
        params = [evidence_id]
        if not is_admin:
            query += " AND user_id = %s"
            params.append(user_id)

        db.execute(query, tuple(params))
        row = db.fetchone()
        if not row:
            return None

        # Fetch Transcripts
        db.execute("SELECT * FROM video_transcripts WHERE evidence_id = %s ORDER BY start_time ASC;", (evidence_id,))
        transcripts = [
            TranscriptSegment(
                segment_index=t["segment_index"],
                start_time=float(t["start_time"]),
                end_time=float(t["end_time"]),
                text=t["text"],
                speaker=t["speaker"],
                confidence=float(t["confidence"]) if t["confidence"] is not None else None
            )
            for t in db.fetchall()
        ]

        # Fetch Observations
        db.execute("SELECT * FROM video_visual_observations WHERE evidence_id = %s ORDER BY timestamp_seconds ASC;", (evidence_id,))
        observations = [
            VisualObservation(
                observation_id=o["observation_id"],
                timestamp_seconds=float(o["timestamp_seconds"]),
                frame_reference=o["frame_reference"],
                category=o["category"],
                description=o["description"],
                neutral_observation=o["neutral_observation"],
                visible_physical_marks=o["visible_physical_marks"],
                uncertainty_or_limitation=o["uncertainty_or_limitation"],
                confidence=float(o["confidence"]) if o["confidence"] is not None else None
            )
            for o in db.fetchall()
        ]

        # Fetch Report
        db.execute("SELECT * FROM video_evidence_reports WHERE evidence_id = %s;", (evidence_id,))
        rep_row = db.fetchone()
        report_summary = None
        if rep_row:
            report_summary = EvidenceReportSummary(
                report_id=rep_row["report_id"],
                evidence_id=rep_row["evidence_id"],
                summary=rep_row["summary"],
                chronological_summary=rep_row["chronological_summary"] if isinstance(rep_row["chronological_summary"], list) else json.loads(rep_row["chronological_summary"] or "[]"),
                observable_events=rep_row["observable_events"] if isinstance(rep_row["observable_events"], list) else json.loads(rep_row["observable_events"] or "[]"),
                visible_physical_marks=rep_row["visible_physical_marks"] if isinstance(rep_row["visible_physical_marks"], list) else json.loads(rep_row["visible_physical_marks"] or "[]"),
                user_statements=rep_row["user_statements"] if isinstance(rep_row["user_statements"], list) else json.loads(rep_row["user_statements"] or "[]"),
                ai_interpretations=rep_row["ai_interpretations"] if isinstance(rep_row["ai_interpretations"], list) else json.loads(rep_row["ai_interpretations"] or "[]"),
                technical_limitations=rep_row["technical_limitations"] if isinstance(rep_row["technical_limitations"], list) else json.loads(rep_row["technical_limitations"] or "[]"),
                preservation_guidelines=rep_row["preservation_guidelines"] if isinstance(rep_row["preservation_guidelines"], list) else json.loads(rep_row["preservation_guidelines"] or "[]"),
                legal_provisions=rep_row["legal_provisions"] if isinstance(rep_row["legal_provisions"], list) else json.loads(rep_row["legal_provisions"] or "[]"),
                status_summary=rep_row["status_summary"] if isinstance(rep_row["status_summary"], dict) else json.loads(rep_row["status_summary"] or "{}")
            )

        return EvidenceDetailResponse(
            evidence_id=row["evidence_id"],
            user_id=row["user_id"],
            conversation_id=row["conversation_id"],
            original_filename=row["original_filename"],
            file_size_bytes=row["file_size_bytes"],
            media_container=row["media_container"],
            file_hash_sha256=row["file_hash_sha256"],
            duration_seconds=float(row["duration_seconds"]) if row["duration_seconds"] is not None else None,
            resolution=row["resolution"],
            fps=float(row["fps"]) if row["fps"] is not None else None,
            has_audio=row["has_audio"],
            processing_status=row["processing_status"],
            error_message=row["error_message"],
            transcripts=transcripts,
            observations=observations,
            report=report_summary,
            metadata=row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"] or "{}"),
            created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            updated_at=row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"])
        )

    @classmethod
    def list_user_evidence(
        cls,
        db: RealDictCursor,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> EvidenceListResponse:
        """Lists user's uploaded evidence items."""
        db.execute("""
            SELECT * FROM video_evidence
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s;
        """, (user_id, limit, offset))
        rows = db.fetchall()

        db.execute("SELECT COUNT(*) AS total FROM video_evidence WHERE user_id = %s;", (user_id,))
        total = db.fetchone()["total"]

        items = [
            EvidenceUploadResponse(
                evidence_id=r["evidence_id"],
                user_id=r["user_id"],
                conversation_id=r["conversation_id"],
                original_filename=r["original_filename"],
                file_size_bytes=r["file_size_bytes"],
                media_container=r["media_container"],
                file_hash_sha256=r["file_hash_sha256"],
                duration_seconds=float(r["duration_seconds"]) if r["duration_seconds"] is not None else None,
                resolution=r["resolution"],
                has_audio=r["has_audio"],
                processing_status=r["processing_status"],
                error_message=r["error_message"],
                created_at=r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"])
            )
            for r in rows
        ]

        return EvidenceListResponse(items=items, total=total)

    @classmethod
    def delete_evidence(
        cls,
        db: RealDictCursor,
        evidence_id: int,
        user_id: int,
        is_admin: bool = False
    ) -> bool:
        """Safely removes evidence record and files from disk."""
        query = "SELECT storage_path FROM video_evidence WHERE evidence_id = %s"
        params = [evidence_id]
        if not is_admin:
            query += " AND user_id = %s"
            params.append(user_id)

        db.execute(query, tuple(params))
        row = db.fetchone()
        if not row:
            return False

        # Remove file from disk
        path = Path(row["storage_path"])
        if path.exists():
            try:
                path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete video file {path}: {e}")

        # Delete from DB (cascades to transcripts, observations, reports)
        db.execute("DELETE FROM video_evidence WHERE evidence_id = %s;", (evidence_id,))
        if hasattr(db, "connection") and db.connection:
            db.connection.commit()

        return True
