CREATE TABLE IF NOT EXISTS case_authorities (
    case_authority_id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL,
    authority_id BIGINT NOT NULL,
    authority_role VARCHAR(150),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_case_authority_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_case_authority_authority
        FOREIGN KEY (authority_id)
        REFERENCES authorities(authority_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_case_authority
        UNIQUE (case_id, authority_id)
);