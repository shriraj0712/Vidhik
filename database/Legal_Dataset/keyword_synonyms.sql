CREATE TABLE IF NOT EXISTS keyword_synonyms (
    synonym_id BIGSERIAL PRIMARY KEY,

    keyword_id BIGINT NOT NULL,

    synonym VARCHAR(200) NOT NULL,

    language VARCHAR(30) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_keyword_synonym_keyword
        FOREIGN KEY (keyword_id)
        REFERENCES keywords(keyword_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_keyword_synonym
        UNIQUE (keyword_id, synonym, language)
);CREATE TABLE IF NOT EXISTS keyword_synonyms (
    synonym_id BIGSERIAL PRIMARY KEY,

    keyword_id BIGINT NOT NULL,

    synonym VARCHAR(200) NOT NULL,

    language VARCHAR(30) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_keyword_synonym_keyword
        FOREIGN KEY (keyword_id)
        REFERENCES keywords(keyword_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_keyword_synonym
        UNIQUE (keyword_id, synonym, language)
);