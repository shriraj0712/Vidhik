CREATE TABLE IF NOT EXISTS case_rights (
    case_id BIGINT NOT NULL,

    right_id BIGINT NOT NULL,

    relevance_score NUMERIC(5,2) NOT NULL DEFAULT 0,

    explanation TEXT,

    identified_by VARCHAR(50) DEFAULT 'system',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (case_id, right_id),

    CONSTRAINT fk_case_right_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_case_right_right
        FOREIGN KEY (right_id)
        REFERENCES rights(right_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_case_right_relevance
        CHECK (relevance_score BETWEEN 0 AND 100)
);