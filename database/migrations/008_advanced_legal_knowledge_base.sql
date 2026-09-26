-- ====================================================================
-- VIDHIK LEGAL PLATFORM - PHASE 17: ADVANCED LEGAL KNOWLEDGE BASE
-- Schema Migration 008: BNS, BNSS, BSA Knowledge Structures,
-- Offences, Punishments, Procedures, Evidence Rules, Predecessors,
-- Legal Relationships, and Verified Judicial Interpretations.
-- ====================================================================
-- Fully relational, idempotent, non-destructive, with zero data loss.
-- ====================================================================

BEGIN;

-- 1. OFFENCES TABLE
CREATE TABLE IF NOT EXISTS offences (
    offence_id BIGSERIAL PRIMARY KEY,
    law_id BIGINT REFERENCES laws(law_id) ON DELETE CASCADE,
    section_id BIGINT REFERENCES sections(section_id) ON DELETE CASCADE,
    offence_name VARCHAR(500) NOT NULL,
    description TEXT,
    section_reference VARCHAR(100),
    cognizable_status VARCHAR(50) DEFAULT 'Cognizable',
    bailable_status VARCHAR(50) DEFAULT 'Non-Bailable',
    compoundable_status VARCHAR(50) DEFAULT 'Non-Compoundable',
    triable_by VARCHAR(150) DEFAULT 'Court of Session',
    source VARCHAR(255) DEFAULT 'Official Bharatiya Nyaya Sanhita, 2023',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_offences_law ON offences(law_id);
CREATE INDEX IF NOT EXISTS idx_offences_section ON offences(section_id);
CREATE INDEX IF NOT EXISTS idx_offences_name ON offences(offence_name);
CREATE INDEX IF NOT EXISTS idx_offences_bailable ON offences(bailable_status);

-- 2. PUNISHMENTS TABLE
CREATE TABLE IF NOT EXISTS punishments (
    punishment_id BIGSERIAL PRIMARY KEY,
    law_id BIGINT REFERENCES laws(law_id) ON DELETE CASCADE,
    section_id BIGINT REFERENCES sections(section_id) ON DELETE CASCADE,
    offence_id BIGINT REFERENCES offences(offence_id) ON DELETE SET NULL,
    punishment_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    minimum_punishment VARCHAR(200),
    maximum_punishment VARCHAR(200),
    fine_details TEXT,
    imprisonment_details TEXT,
    community_service BOOLEAN NOT NULL DEFAULT FALSE,
    other_penalty TEXT,
    source VARCHAR(255) DEFAULT 'Official Statutory Source',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_punishments_law ON punishments(law_id);
CREATE INDEX IF NOT EXISTS idx_punishments_section ON punishments(section_id);
CREATE INDEX IF NOT EXISTS idx_punishments_offence ON punishments(offence_id);
CREATE INDEX IF NOT EXISTS idx_punishments_type ON punishments(punishment_type);

-- 3. LEGAL PROCEDURES TABLE (BNSS PROCEDURAL MAPPING)
CREATE TABLE IF NOT EXISTS legal_procedures (
    procedure_id BIGSERIAL PRIMARY KEY,
    law_id BIGINT REFERENCES laws(law_id) ON DELETE CASCADE,
    section_id BIGINT REFERENCES sections(section_id) ON DELETE CASCADE,
    procedure_category VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    statutory_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    safeguards JSONB NOT NULL DEFAULT '[]'::jsonb,
    timeline_days INT,
    source VARCHAR(255) DEFAULT 'Official Bharatiya Nagarik Suraksha Sanhita, 2023',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_proc_law ON legal_procedures(law_id);
CREATE INDEX IF NOT EXISTS idx_proc_section ON legal_procedures(section_id);
CREATE INDEX IF NOT EXISTS idx_proc_category ON legal_procedures(procedure_category);

-- 4. EVIDENCE PROVISIONS TABLE (BSA EVIDENCE MAPPING)
CREATE TABLE IF NOT EXISTS evidence_provisions (
    evidence_provision_id BIGSERIAL PRIMARY KEY,
    law_id BIGINT REFERENCES laws(law_id) ON DELETE CASCADE,
    section_id BIGINT REFERENCES sections(section_id) ON DELETE CASCADE,
    provision_type VARCHAR(100) NOT NULL,
    rule_statement TEXT NOT NULL,
    statutory_condition TEXT,
    admissibility_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    source VARCHAR(255) DEFAULT 'Official Bharatiya Sakshya Adhiniyam, 2023',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evid_law ON evidence_provisions(law_id);
CREATE INDEX IF NOT EXISTS idx_evid_section ON evidence_provisions(section_id);
CREATE INDEX IF NOT EXISTS idx_evid_type ON evidence_provisions(provision_type);

-- 5. LEGAL RELATIONSHIPS JUNCTION TABLE (CROSS-STATUTE LINKAGES)
CREATE TABLE IF NOT EXISTS legal_relationships (
    rel_id BIGSERIAL PRIMARY KEY,
    source_law_id BIGINT NOT NULL REFERENCES laws(law_id) ON DELETE CASCADE,
    source_section_id BIGINT NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    target_law_id BIGINT NOT NULL REFERENCES laws(law_id) ON DELETE CASCADE,
    target_section_id BIGINT NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    confidence_score NUMERIC(5,2) NOT NULL DEFAULT 1.00,
    explanation TEXT,
    source VARCHAR(255) DEFAULT 'Authoritative Statutory Cross-Reference',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_legal_rel UNIQUE(source_section_id, target_section_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON legal_relationships(source_section_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON legal_relationships(target_section_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON legal_relationships(relationship_type);

-- 6. PREDECESSOR LAW MAPPINGS TABLE (IPC -> BNS, CrPC -> BNSS, IEA -> BSA)
CREATE TABLE IF NOT EXISTS predecessor_law_mappings (
    mapping_id BIGSERIAL PRIMARY KEY,
    new_law_id BIGINT REFERENCES laws(law_id) ON DELETE CASCADE,
    new_section_id BIGINT REFERENCES sections(section_id) ON DELETE CASCADE,
    new_section_number VARCHAR(50) NOT NULL,
    old_law_name VARCHAR(300) NOT NULL,
    old_section_number VARCHAR(50) NOT NULL,
    correspondence_type VARCHAR(100) NOT NULL DEFAULT 'Modified',
    key_changes_summary TEXT,
    source VARCHAR(255) DEFAULT 'Official Comparative Correlation Table',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pred_mapping UNIQUE(new_law_id, new_section_number, old_law_name, old_section_number)
);

CREATE INDEX IF NOT EXISTS idx_pred_new_sec ON predecessor_law_mappings(new_section_id);
CREATE INDEX IF NOT EXISTS idx_pred_old ON predecessor_law_mappings(old_law_name, old_section_number);

-- 7. JUDGMENTS / CASE-LAW TABLE
CREATE TABLE IF NOT EXISTS judgments (
    judgment_id BIGSERIAL PRIMARY KEY,
    case_title VARCHAR(500) NOT NULL,
    case_number VARCHAR(200),
    court VARCHAR(200) NOT NULL,
    bench VARCHAR(300),
    judgment_date DATE,
    citation VARCHAR(300) UNIQUE,
    judgment_text TEXT,
    headnotes TEXT,
    source_url TEXT,
    source_name VARCHAR(200) NOT NULL DEFAULT 'Supreme Court of India Official Repository',
    source_type VARCHAR(100) NOT NULL DEFAULT 'Supreme Court of India',
    language VARCHAR(50) NOT NULL DEFAULT 'en',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_judgments_court ON judgments(court);
CREATE INDEX IF NOT EXISTS idx_judgments_citation ON judgments(citation);
CREATE INDEX IF NOT EXISTS idx_judgments_date ON judgments(judgment_date);

-- 8. JUDGMENT LAWS JUNCTION TABLE
CREATE TABLE IF NOT EXISTS judgment_laws (
    id BIGSERIAL PRIMARY KEY,
    judgment_id BIGINT NOT NULL REFERENCES judgments(judgment_id) ON DELETE CASCADE,
    law_id BIGINT NOT NULL REFERENCES laws(law_id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL DEFAULT 'Mentioned',
    CONSTRAINT uq_judgment_law UNIQUE(judgment_id, law_id)
);

CREATE INDEX IF NOT EXISTS idx_jl_judgment ON judgment_laws(judgment_id);
CREATE INDEX IF NOT EXISTS idx_jl_law ON judgment_laws(law_id);

-- 9. JUDGMENT SECTIONS JUNCTION TABLE (STATUTE ↔ INTERPRETATION)
CREATE TABLE IF NOT EXISTS judgment_sections (
    id BIGSERIAL PRIMARY KEY,
    judgment_id BIGINT NOT NULL REFERENCES judgments(judgment_id) ON DELETE CASCADE,
    law_id BIGINT NOT NULL REFERENCES laws(law_id) ON DELETE CASCADE,
    section_id BIGINT NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL DEFAULT 'Interpreted',
    relevance VARCHAR(50) NOT NULL DEFAULT 'Direct',
    explanation TEXT,
    CONSTRAINT uq_judgment_section UNIQUE(judgment_id, section_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_js_judgment ON judgment_sections(judgment_id);
CREATE INDEX IF NOT EXISTS idx_js_section ON judgment_sections(section_id);
CREATE INDEX IF NOT EXISTS idx_js_rel_type ON judgment_sections(relationship_type);

COMMIT;
