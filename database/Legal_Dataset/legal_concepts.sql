CREATE TABLE IF NOT EXISTS legal_concepts (
    concept_id BIGSERIAL PRIMARY KEY,

    concept_name VARCHAR(200) NOT NULL UNIQUE,

    description TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);