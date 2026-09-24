CREATE TABLE IF NOT EXISTS case_keywords (
    case_id BIGINT NOT NULL,

    keyword_id BIGINT NOT NULL,

    relevance_score NUMERIC(5,2) NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (case_id, keyword_id),

    CONSTRAINT fk_case_keyword_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_case_keyword_keyword
        FOREIGN KEY (keyword_id)
        REFERENCES keywords(keyword_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_case_keyword_relevance
        CHECK (relevance_score BETWEEN 0 AND 100)
);