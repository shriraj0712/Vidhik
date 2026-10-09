-- ====================================================================
-- VIDHIK LEGAL PLATFORM - VIDEO EVIDENCE ANALYSIS & CHAIN OF CUSTODY
-- Migration 010: Video Evidence, Transcripts, Visual Observations & Reports
-- ====================================================================

BEGIN;

-- 1. VIDEO EVIDENCE RECORDS TABLE
CREATE TABLE IF NOT EXISTS video_evidence (
    evidence_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    conversation_id VARCHAR(64),
    original_filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    media_container VARCHAR(50) NOT NULL,
    file_hash_sha256 VARCHAR(64) NOT NULL,
    duration_seconds NUMERIC(8, 2),
    resolution VARCHAR(30),
    fps NUMERIC(6, 2),
    has_audio BOOLEAN NOT NULL DEFAULT TRUE,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    error_message TEXT,
    retry_count INT NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_video_evidence_user_id ON video_evidence(user_id);
CREATE INDEX IF NOT EXISTS idx_video_evidence_conversation_id ON video_evidence(conversation_id);
CREATE INDEX IF NOT EXISTS idx_video_evidence_status ON video_evidence(processing_status);
CREATE INDEX IF NOT EXISTS idx_video_evidence_hash ON video_evidence(file_hash_sha256);

-- 2. VIDEO AUDIO TRANSCRIPTS TABLE (Per segment timestamps)
CREATE TABLE IF NOT EXISTS video_transcripts (
    transcript_id BIGSERIAL PRIMARY KEY,
    evidence_id BIGINT NOT NULL REFERENCES video_evidence(evidence_id) ON DELETE CASCADE,
    segment_index INT NOT NULL,
    start_time NUMERIC(8, 2) NOT NULL,
    end_time NUMERIC(8, 2) NOT NULL,
    text TEXT NOT NULL,
    speaker VARCHAR(50),
    confidence NUMERIC(4, 3),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_video_transcripts_evidence_id ON video_transcripts(evidence_id);
CREATE INDEX IF NOT EXISTS idx_video_transcripts_time ON video_transcripts(evidence_id, start_time);

-- 3. VIDEO VISUAL OBSERVATIONS TABLE (Sampled frame analysis)
CREATE TABLE IF NOT EXISTS video_visual_observations (
    observation_id BIGSERIAL PRIMARY KEY,
    evidence_id BIGINT NOT NULL REFERENCES video_evidence(evidence_id) ON DELETE CASCADE,
    timestamp_seconds NUMERIC(8, 2) NOT NULL,
    frame_reference TEXT,
    category VARCHAR(50) NOT NULL DEFAULT 'observation',
    description TEXT NOT NULL,
    neutral_observation TEXT NOT NULL,
    visible_physical_marks TEXT,
    uncertainty_or_limitation TEXT,
    confidence NUMERIC(4, 3),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_video_observations_evidence_id ON video_visual_observations(evidence_id);
CREATE INDEX IF NOT EXISTS idx_video_observations_time ON video_visual_observations(evidence_id, timestamp_seconds);

-- 4. STRUCTURED EVIDENCE REPORTS TABLE
CREATE TABLE IF NOT EXISTS video_evidence_reports (
    report_id BIGSERIAL PRIMARY KEY,
    evidence_id BIGINT NOT NULL UNIQUE REFERENCES video_evidence(evidence_id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    chronological_summary JSONB NOT NULL DEFAULT '[]'::jsonb,
    observable_events JSONB NOT NULL DEFAULT '[]'::jsonb,
    visible_physical_marks JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_statements JSONB NOT NULL DEFAULT '[]'::jsonb,
    ai_interpretations JSONB NOT NULL DEFAULT '[]'::jsonb,
    technical_limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    preservation_guidelines JSONB NOT NULL DEFAULT '[]'::jsonb,
    legal_provisions JSONB NOT NULL DEFAULT '[]'::jsonb,
    status_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_video_reports_evidence_id ON video_evidence_reports(evidence_id);

COMMIT;
