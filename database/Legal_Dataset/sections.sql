CREATE TABLE IF NOT EXISTS sections (
    section_id BIGSERIAL PRIMARY KEY,

    law_id BIGINT NOT NULL,

    section_number VARCHAR(50) NOT NULL,

    section_title VARCHAR(500),

    description TEXT,

    full_text TEXT,

    chapter VARCHAR(200),

    part VARCHAR(200),

    source_url TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sections_law
        FOREIGN KEY (law_id)
        REFERENCES laws(law_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_law_section
        UNIQUE (law_id, section_number)
);