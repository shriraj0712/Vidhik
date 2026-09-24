CREATE TABLE IF NOT EXISTS case_updates (
    update_id BIGSERIAL PRIMARY KEY,

    case_id BIGINT NOT NULL,

    update_type VARCHAR(100),

    update_title VARCHAR(300),

    update_description TEXT NOT NULL,

    status VARCHAR(50),

    updated_by VARCHAR(100),

    update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_case_update_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_case_update_status
        CHECK (
            status IS NULL
            OR status IN (
                'active',
                'pending',
                'resolved',
                'closed',
                'withdrawn'
            )
        )
);