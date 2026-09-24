CREATE TABLE IF NOT EXISTS feedback (
    feedback_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    case_id BIGINT,
    rating INTEGER,
    feedback_text TEXT,
    feedback_type VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_feedback_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_feedback_rating
        CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)
);