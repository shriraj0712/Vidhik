CREATE TABLE IF NOT EXISTS laws (
    law_id BIGSERIAL PRIMARY KEY,

    law_name VARCHAR(300) NOT NULL,

    short_name VARCHAR(100),

    law_type VARCHAR(100),

    description TEXT,

    jurisdiction VARCHAR(100) NOT NULL DEFAULT 'India',

    enactment_date DATE,

    effective_date DATE,

    source_url TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_law_name UNIQUE (law_name)
);