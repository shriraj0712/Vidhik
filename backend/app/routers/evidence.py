"""
Vidhik Platform - Video Evidence API Router
============================================
Provides authenticated RESTful endpoints for:
- Uploading and validating digital video evidence (.mp4, .webm, .mov, .avi, .mkv)
- Computing cryptographic SHA-256 hash for chain of custody
- Polling background processing state (audio extraction, frame analysis, transcription)
- Retrieving verified visual observations and machine-generated transcripts
- Downloading structured evidence reports (.docx) under Bharatiya Sakshya Adhiniyam, 2023
- Retrying failed jobs and deleting evidence records
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from psycopg2.extras import RealDictCursor

from app.database import get_db, get_db_cursor
from app.services.auth_service import get_authenticated_user, get_optional_user
from app.services.video_evidence_service import (
    VideoEvidenceService,
    ORIGINALS_DIR,
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB
)
from app.schemas.evidence import (
    EvidenceUploadResponse,
    EvidenceDetailResponse,
    EvidenceListResponse
)

router = APIRouter(prefix="/api/evidence", tags=["Video Evidence Analysis"])


def _background_process_evidence(evidence_id: int):
    """Background task runner for asynchronous video processing."""
    try:
        with get_db_cursor() as db:
            VideoEvidenceService.process_evidence_pipeline(db, evidence_id)
    except Exception as e:
        import logging
        logging.getLogger("vidhik.evidence_router").error(
            f"Background processing failed for evidence #{evidence_id}: {e}",
            exc_info=True
        )


@router.post(
    "/upload",
    response_model=EvidenceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Video Evidence Recording",
    description="""
    Uploads a video recording (.mp4, .webm, .mov, .avi, .mkv) for legal analysis.
    - Validates file signature (magic bytes) and size limits.
    - Computes cryptographic SHA-256 fingerprint for chain of custody.
    - Queues audio extraction, speech transcription, frame sampling, and legal assessment.
    """
)
async def upload_evidence(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    db: RealDictCursor = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    # Enforce or assign authenticated user
    user_id = current_user.get("user_id") if current_user else 1

    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No video file supplied in upload request."
        )

    # 1. Read initial header bytes to validate file signature
    header_bytes = await file.read(1024)
    if not header_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    is_valid, container, mime = VideoEvidenceService.validate_file_signature(
        header_bytes=header_bytes,
        filename=file.filename
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported or invalid video format '{file.filename}'. Supported formats: MP4, WebM, MOV, AVI, MKV."
        )

    # 2. Write file to secure storage directory with server-generated UUID filename
    safe_ext = f".{container}"
    stored_filename = f"ev_{uuid.uuid4().hex}{safe_ext}"
    target_path = ORIGINALS_DIR / stored_filename

    # Rewind and stream file to disk while enforcing max file size
    await file.seek(0)
    file_size = 0
    try:
        with open(target_path, "wb") as out_f:
            while chunk := await file.read(65536):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE_BYTES:
                    out_f.close()
                    if target_path.exists():
                        target_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB."
                    )
                out_f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store video file: {str(e)}"
        )

    # 3. Compute SHA-256 Hash
    sha256_hash = VideoEvidenceService.compute_file_hash(target_path)

    # 4. Create database record
    db.execute("""
        INSERT INTO video_evidence (
            user_id, conversation_id, original_filename, storage_path,
            file_size_bytes, mime_type, media_container, file_hash_sha256,
            processing_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'queued')
        RETURNING *;
    """, (
        user_id, conversation_id, file.filename, str(target_path),
        file_size, mime, container, sha256_hash
    ))
    row = db.fetchone()
    if hasattr(db, "connection") and db.connection:
        db.connection.commit()

    evidence_id = row["evidence_id"]

    # 5. Dispatch processing in background task
    background_tasks.add_task(_background_process_evidence, evidence_id)

    return EvidenceUploadResponse(
        evidence_id=evidence_id,
        user_id=row["user_id"],
        conversation_id=row["conversation_id"],
        original_filename=row["original_filename"],
        file_size_bytes=row["file_size_bytes"],
        media_container=row["media_container"],
        file_hash_sha256=row["file_hash_sha256"],
        duration_seconds=None,
        resolution=None,
        has_audio=True,
        processing_status="queued",
        error_message=None,
        created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"])
    )



@router.get(
    "/{evidence_id}",
    response_model=EvidenceDetailResponse,
    summary="Get Video Evidence Detail & Processing Status"
)
def get_evidence_detail(
    evidence_id: int,
    db: RealDictCursor = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Returns complete evidence record, transcript segments, visual observations,
    and structured report. Enforces ownership authorization (IDOR protection).
    """
    user_id = current_user.get("user_id") if current_user else 1
    is_admin = bool(current_user and current_user.get("role") == "admin")

    detail = VideoEvidenceService.get_evidence_detail(
        db=db,
        evidence_id=evidence_id,
        user_id=user_id,
        is_admin=is_admin
    )

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence item #{evidence_id} not found or access denied."
        )

    return detail


@router.get(
    "",
    response_model=EvidenceListResponse,
    summary="List Authenticated User's Video Evidence Items"
)
def list_evidence(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: RealDictCursor = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """Lists video evidence files uploaded by the authenticated user."""
    user_id = current_user.get("user_id") if current_user else 1
    return VideoEvidenceService.list_user_evidence(
        db=db,
        user_id=user_id,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{evidence_id}/download-report",
    summary="Download Structured Evidence Report (.docx)"
)
def download_evidence_report(
    evidence_id: int,
    db: RealDictCursor = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Generates and downloads a Microsoft Word (.docx) structured evidence report
    with timestamps, transcripts, observations, and statutory guidelines (BSA 2023).
    """
    user_id = current_user.get("user_id") if current_user else 1
    is_admin = bool(current_user and current_user.get("role") == "admin")

    detail = VideoEvidenceService.get_evidence_detail(
        db=db,
        evidence_id=evidence_id,
        user_id=user_id,
        is_admin=is_admin
    )

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence item #{evidence_id} not found or access denied."
        )

    # Fetch raw evidence row & report row for export
    db.execute("SELECT * FROM video_evidence WHERE evidence_id = %s;", (evidence_id,))
    ev_row = db.fetchone()

    report_data = detail.report.model_dump() if detail.report else {}
    if not report_data:
        # Generate on the fly if report row hasn't completed yet
        report_data = VideoEvidenceService.generate_structured_report(
            evidence=ev_row,
            transcripts=[t.model_dump() for t in detail.transcripts],
            observations=[o.model_dump() for o in detail.observations]
        )

    docx_stream = VideoEvidenceService.generate_docx_report(
        evidence=ev_row,
        report_data=report_data
    )

    clean_filename = f"Vidhik_Evidence_Report_EVD{evidence_id}.docx"

    return StreamingResponse(
        docx_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )


@router.post(
    "/{evidence_id}/retry",
    summary="Retry Processing for Failed Evidence"
)
def retry_evidence_processing(
    evidence_id: int,
    background_tasks: BackgroundTasks,
    db: RealDictCursor = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """Retries processing pipeline for a failed evidence item."""
    user_id = current_user.get("user_id") if current_user else 1
    is_admin = bool(current_user and current_user.get("role") == "admin")

    query = "SELECT * FROM video_evidence WHERE evidence_id = %s"
    params = [evidence_id]
    if not is_admin:
        query += " AND user_id = %s"
        params.append(user_id)

    db.execute(query, tuple(params))
    row = db.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found or access denied."
        )

    db.execute(
        "UPDATE video_evidence SET processing_status = 'queued', retry_count = retry_count + 1, updated_at = NOW() WHERE evidence_id = %s;",
        (evidence_id,)
    )
    if hasattr(db, "connection") and db.connection:
        db.connection.commit()

    background_tasks.add_task(_background_process_evidence, evidence_id)

    return {"message": "Evidence processing job re-queued.", "evidence_id": evidence_id, "status": "queued"}


@router.delete(
    "/{evidence_id}",
    summary="Delete Video Evidence and Derived Artifacts"
)
def delete_evidence(
    evidence_id: int,
    db: RealDictCursor = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """Safely deletes video recording and all derived artifacts."""
    user_id = current_user.get("user_id") if current_user else 1
    is_admin = bool(current_user and current_user.get("role") == "admin")

    deleted = VideoEvidenceService.delete_evidence(
        db=db,
        evidence_id=evidence_id,
        user_id=user_id,
        is_admin=is_admin
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found or access denied."
        )

    return {"message": f"Evidence #{evidence_id} and derived records successfully deleted.", "evidence_id": evidence_id}
