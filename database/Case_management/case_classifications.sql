CREATE TABLE IF NOT EXISTS case_classifications (
    classification_id BIGSERIAL PRIMARY KEY,

    case_id BIGINT NOT NULL,

    classification VARCHAR(200) NOT NULL,

    confidence_score NUMERIC(5,2),

    classified_by VARCHAR(50) DEFAULT 'system',

    explanation TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_case_classification_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_classification_confidence
        CHECK (
            confidence_score IS NULL
            OR confidence_score BETWEEN 0 AND 100
        )
);