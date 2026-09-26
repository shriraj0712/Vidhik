CREATE TABLE IF NOT EXISTS keywords (
    keyword_id BIGSERIAL PRIMARY KEY,

    keyword VARCHAR(200) NOT NULL,

    language VARCHAR(30) NOT NULL DEFAULT 'en',

    keyword_type VARCHAR(50),

    description TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_keyword_language
        UNIQUE (keyword, language)
);