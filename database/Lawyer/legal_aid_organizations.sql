CREATE TABLE IF NOT EXISTS legal_aid_organizations (
    organization_id BIGSERIAL PRIMARY KEY,
    organization_name VARCHAR(250) NOT NULL,
    organization_type VARCHAR(150),
    description TEXT,
    phone VARCHAR(20),
    email VARCHAR(150),
    website TEXT,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    provides_free_legal_aid BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);