CREATE TABLE IF NOT EXISTS lawyer_locations (
    location_id BIGSERIAL PRIMARY KEY,
    lawyer_id BIGINT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100),
    pincode VARCHAR(10),

    CONSTRAINT fk_lawyer_location
        FOREIGN KEY (lawyer_id)
        REFERENCES lawyers(lawyer_id)
        ON DELETE CASCADE
);