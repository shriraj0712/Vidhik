CREATE TABLE IF NOT EXISTS reminders (
    reminder_id BIGSERIAL PRIMARY KEY,
    case_id BIGINT,
    user_id BIGINT,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    reminder_type VARCHAR(100),
    reminder_date DATE,
    reminder_time TIME,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority VARCHAR(50) NOT NULL DEFAULT 'normal',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_reminder_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE
);