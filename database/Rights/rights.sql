CREATE TABLE IF NOT EXISTS rights (
    right_id BIGSERIAL PRIMARY KEY,

    right_name VARCHAR(300) NOT NULL,

    description TEXT,

    category VARCHAR(150),

    constitutional_basis TEXT,

    remedy TEXT,

    applicable_to VARCHAR(300),

    language VARCHAR(30) NOT NULL DEFAULT 'en',

    source_url TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_right_name_language
        UNIQUE (right_name, language)
);