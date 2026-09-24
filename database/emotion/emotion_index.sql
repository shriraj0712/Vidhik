CREATE INDEX IF NOT EXISTS idx_case_emotions_case
ON case_emotions(case_id);

CREATE INDEX IF NOT EXISTS idx_case_emotions_emotion
ON case_emotions(emotion);

CREATE INDEX IF NOT EXISTS idx_emotion_responses_emotion
ON emotion_responses(emotion_id);

CREATE INDEX IF NOT EXISTS idx_emotion_responses_type
ON emotion_responses(response_type);