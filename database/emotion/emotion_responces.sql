CREATE TABLE IF NOT EXISTS emotion_responses (
    response_id BIGSERIAL PRIMARY KEY,
    emotion_id BIGINT NOT NULL,
    response_type VARCHAR(100),
    response_text TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_emotion_response_emotion
        FOREIGN KEY (emotion_id)
        REFERENCES case_emotions(emotion_id)
        ON DELETE CASCADE
);