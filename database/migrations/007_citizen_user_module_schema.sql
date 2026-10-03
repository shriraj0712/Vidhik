-- ====================================================================
-- VIDHIK LEGAL PLATFORM - PHASE 14: CITIZEN / USER MODULE SCHEMA
-- Schema Migration 007: User Profiles, Bookmarks, Search History,
-- and Procedure Checklists
-- ====================================================================
-- Fully relational, idempotent, and non-destructive.
-- ====================================================================

BEGIN;

-- 1. USER PROFILES TABLE
CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
    date_of_birth DATE,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    preferred_language VARCHAR(50) DEFAULT 'en',
    profile_image_url TEXT,
    occupation VARCHAR(150),
    emergency_contact VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user ON user_profiles(user_id);

-- 2. USER SAVED SECTIONS (BOOKMARKS) TABLE
CREATE TABLE IF NOT EXISTS user_saved_sections (
    bookmark_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    section_id BIGINT NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    notes TEXT,
    tag VARCHAR(100) DEFAULT 'General',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_section_bookmark UNIQUE(user_id, section_id)
);

CREATE INDEX IF NOT EXISTS idx_user_bookmarks_user ON user_saved_sections(user_id);
CREATE INDEX IF NOT EXISTS idx_user_bookmarks_sec ON user_saved_sections(section_id);

-- 3. USER SEARCH HISTORY TABLE
CREATE TABLE IF NOT EXISTS user_search_history (
    search_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    query_text VARCHAR(500) NOT NULL,
    filters JSONB DEFAULT '{}'::jsonb,
    results_count INT DEFAULT 0,
    searched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_history_user ON user_search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_date ON user_search_history(searched_at DESC);

-- 4. USER PROCEDURE TRACKERS TABLE (PERSISTENT CHECKLISTS)
CREATE TABLE IF NOT EXISTS user_procedure_trackers (
    tracker_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    procedure_id BIGINT NOT NULL REFERENCES legal_procedures(procedure_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
    completed_documents JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_procedure UNIQUE(user_id, procedure_id)
);

CREATE INDEX IF NOT EXISTS idx_user_proc_tracker_user ON user_procedure_trackers(user_id);

-- 5. INITIALIZE BLANK PROFILES FOR EXISTING USERS
INSERT INTO user_profiles (user_id)
SELECT user_id FROM users
ON CONFLICT (user_id) DO NOTHING;

COMMIT;
