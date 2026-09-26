CREATE TABLE IF NOT EXISTS keyword_concepts (
    keyword_id BIGINT NOT NULL,

    concept_id BIGINT NOT NULL,

    PRIMARY KEY (keyword_id, concept_id),

    CONSTRAINT fk_keyword_concept_keyword
        FOREIGN KEY (keyword_id)
        REFERENCES keywords(keyword_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_keyword_concept_concept
        FOREIGN KEY (concept_id)
        REFERENCES legal_concepts(concept_id)
        ON DELETE CASCADE
);