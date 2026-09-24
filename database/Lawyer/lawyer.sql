CREATE TABLE IF NOT EXISTS lawyer_specializations (
    specialization_id BIGSERIAL PRIMARY KEY,
    lawyer_id BIGINT NOT NULL,
    specialization VARCHAR(150) NOT NULL,

    CONSTRAINT fk_lawyer_specialization
        FOREIGN KEY (lawyer_id)
        REFERENCES lawyers(lawyer_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_lawyer_specialization
        UNIQUE (lawyer_id, specialization)
);