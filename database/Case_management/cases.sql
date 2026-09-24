CREATE TABLE IF NOT EXISTS cases (
    case_id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL,

    case_title VARCHAR(300) NOT NULL,

    case_description TEXT,

    case_type VARCHAR(100),

    status VARCHAR(50) NOT NULL DEFAULT 'active',

    filing_date DATE,

    incident_date DATE,

    location VARCHAR(300),

    police_station VARCHAR(300),

    court_name VARCHAR(300),

    case_number VARCHAR(100),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_case_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_case_status
        CHECK (
            status IN (
                'active',
                'pending',
                'resolved',
                'closed',
                'withdrawn'
            )
        )
);