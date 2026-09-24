CREATE TABLE IF NOT EXISTS authorities (
    authority_id BIGSERIAL PRIMARY KEY,
    authority_name VARCHAR(300) NOT NULL,
    authority_type VARCHAR(100),
    designation VARCHAR(200),
    court_name VARCHAR(300),
    jurisdiction VARCHAR(200),
    description TEXT,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    contact_email VARCHAR(150),
    contact_phone VARCHAR(20),
    website TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_authority_name UNIQUE (authority_name)
);