CREATE TABLE IF NOT EXISTS keyword_mappings (
    mapping_id BIGSERIAL PRIMARY KEY,

    keyword_id BIGINT NOT NULL,

    section_id BIGINT NOT NULL,

    relevance_score NUMERIC(5,2) NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_keyword_mapping_keyword
        FOREIGN KEY (keyword_id)
        REFERENCES keywords(keyword_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_keyword_mapping_section
        FOREIGN KEY (section_id)
        REFERENCES sections(section_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_keyword_section
        UNIQUE (keyword_id, section_id),

    CONSTRAINT chk_relevance_score
        CHECK (relevance_score BETWEEN 0 AND 100)
);
CREATE INDEX IF NOT EXISTS idx_keyword_mappings_keyword
ON keyword_mappings(keyword_id);

CREATE INDEX IF NOT EXISTS idx_keyword_mappings_section
ON keyword_mappings(section_id);