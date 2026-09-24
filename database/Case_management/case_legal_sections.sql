CREATE TABLE IF NOT EXISTS case_legal_sections (
    case_id BIGINT NOT NULL,

    section_id BIGINT NOT NULL,

    relevance_score NUMERIC(5,2) NOT NULL DEFAULT 0,

    explanation TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (case_id, section_id),

    CONSTRAINT fk_case_legal_section_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_case_legal_section_section
        FOREIGN KEY (section_id)
        REFERENCES sections(section_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_case_section_relevance
        CHECK (relevance_score BETWEEN 0 AND 100)
);