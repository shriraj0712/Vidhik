CREATE TABLE IF NOT EXISTS section_right_mappings (
    section_id BIGINT NOT NULL,

    right_id BIGINT NOT NULL,

    relevance_score NUMERIC(5,2) NOT NULL DEFAULT 0,

    explanation TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (section_id, right_id),

    CONSTRAINT fk_section_right_section
        FOREIGN KEY (section_id)
        REFERENCES sections(section_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_section_right_right
        FOREIGN KEY (right_id)
        REFERENCES rights(right_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_section_right_relevance
        CHECK (relevance_score BETWEEN 0 AND 100)
);