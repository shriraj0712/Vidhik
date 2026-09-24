CREATE TABLE IF NOT EXISTS notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    reminder_id BIGINT,
    user_id BIGINT,
    title VARCHAR(300) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(100),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_notification_reminder
        FOREIGN KEY (reminder_id)
        REFERENCES reminders(reminder_id)
        ON DELETE CASCADE
);