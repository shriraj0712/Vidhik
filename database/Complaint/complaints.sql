CREATE TABLE IF NOT EXISTS complaints (
    complaint_id BIGSERIAL PRIMARY KEY,
    case_id BIGINT,
    complainant_name VARCHAR(200) NOT NULL,
    complainant_contact VARCHAR(100),
    complaint_type VARCHAR(150),
    subject VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    complaint_date DATE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority VARCHAR(50) NOT NULL DEFAULT 'normal',
    authority_id BIGINT,
    resolution TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_complaint_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_complaint_authority
        FOREIGN KEY (authority_id)
        REFERENCES authorities(authority_id)
        ON DELETE SET NULL
);