-- ====================================================================
-- VIDHIK LEGAL PLATFORM - PHASE 11: LEGAL DOCUMENT ANALYSIS SCHEMA
-- Schema Migration 006: Legal Document Analyses & Grounded References
-- ====================================================================
-- Provides persistent storage for structured document analysis results,
-- entity extractions, clause detections, risk flags, action items,
-- and grounded statutory section references.
-- Fully relational, non-destructive, and idempotent.
-- ====================================================================

BEGIN;

-- 1. LEGAL DOCUMENT ANALYSES TABLE
CREATE TABLE IF NOT EXISTS legal_document_analyses (
    analysis_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    lawyer_id BIGINT REFERENCES lawyers(lawyer_id) ON DELETE SET NULL,
    case_id BIGINT REFERENCES cases(case_id) ON DELETE SET NULL,
    document_name VARCHAR(300) NOT NULL,
    document_type VARCHAR(100) DEFAULT 'Unknown / Unclassified',
    file_type VARCHAR(50) NOT NULL DEFAULT 'text',
    file_size_bytes BIGINT DEFAULT 0,
    file_hash_sha256 VARCHAR(64),
    summary TEXT NOT NULL,
    executive_takeaways JSONB DEFAULT '[]'::jsonb,
    structured_entities JSONB DEFAULT '{}'::jsonb,
    structured_clauses JSONB DEFAULT '[]'::jsonb,
    identified_risks JSONB DEFAULT '[]'::jsonb,
    missing_information JSONB DEFAULT '[]'::jsonb,
    action_items JSONB DEFAULT '[]'::jsonb,
    raw_text_excerpt TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lda_user ON legal_document_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_lda_lawyer ON legal_document_analyses(lawyer_id);
CREATE INDEX IF NOT EXISTS idx_lda_case ON legal_document_analyses(case_id);
CREATE INDEX IF NOT EXISTS idx_lda_created ON legal_document_analyses(created_at);

-- 2. ANALYSIS LEGAL REFERENCES JUNCTION TABLE
CREATE TABLE IF NOT EXISTS analysis_legal_references (
    ref_id BIGSERIAL PRIMARY KEY,
    analysis_id BIGINT NOT NULL REFERENCES legal_document_analyses(analysis_id) ON DELETE CASCADE,
    section_id BIGINT REFERENCES sections(section_id) ON DELETE SET NULL,
    law_id BIGINT REFERENCES laws(law_id) ON DELETE SET NULL,
    citation_text VARCHAR(500) NOT NULL,
    reference_type VARCHAR(50) NOT NULL DEFAULT 'explicit_statutory_mention',
    is_verified_in_db BOOLEAN NOT NULL DEFAULT FALSE,
    relevance_explanation TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alr_analysis ON analysis_legal_references(analysis_id);
CREATE INDEX IF NOT EXISTS idx_alr_section ON analysis_legal_references(section_id);
CREATE INDEX IF NOT EXISTS idx_alr_law ON analysis_legal_references(law_id);
CREATE INDEX IF NOT EXISTS idx_alr_verified ON analysis_legal_references(is_verified_in_db);

COMMIT;
