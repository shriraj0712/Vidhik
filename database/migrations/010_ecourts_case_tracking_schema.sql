-- ====================================================================
-- VIDHIK LEGAL PLATFORM - PHASE 15: eCOURTS CASE TRACKING INTEGRATION
-- Schema Migration 010: eCourts CNR & Official Court Reference Schema
-- ====================================================================
-- Fully relational, idempotent, and non-destructive.
-- Preserves all existing cases, columns, relationships, and data.
-- ====================================================================

BEGIN;

-- 1. EXTEND 'cases' TABLE WITH OFFICIAL COURT REFERENCE COLUMNS
ALTER TABLE cases ADD COLUMN IF NOT EXISTS cnr_number VARCHAR(16);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS court_source VARCHAR(100) DEFAULT 'eCourts India';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS official_case_url TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS external_status VARCHAR(150);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS external_next_hearing_date DATE;

-- 2. CREATE INDEX FOR FAST CNR LOOKUPS
CREATE INDEX IF NOT EXISTS idx_cases_cnr_number ON cases(cnr_number);

COMMIT;
