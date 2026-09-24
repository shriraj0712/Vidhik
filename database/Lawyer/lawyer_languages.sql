CREATE TABLE IF NOT EXISTS lawyer_languages (
    language_id BIGSERIAL PRIMARY KEY,
    lawyer_id BIGINT NOT NULL,
    language VARCHAR(100) NOT NULL,

    CONSTRAINT fk_lawyer_language
        FOREIGN KEY (lawyer_id)
        REFERENCES lawyers(lawyer_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_lawyer_language
        UNIQUE (lawyer_id, language)
);