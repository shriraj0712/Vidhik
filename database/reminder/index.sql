CREATE INDEX IF NOT EXISTS idx_reminders_case
ON reminders(case_id);

CREATE INDEX IF NOT EXISTS idx_reminders_user
ON reminders(user_id);

CREATE INDEX IF NOT EXISTS idx_reminders_date
ON reminders(reminder_date);

CREATE INDEX IF NOT EXISTS idx_reminders_status
ON reminders(status);

CREATE INDEX IF NOT EXISTS idx_notifications_reminder
ON notifications(reminder_id);

CREATE INDEX IF NOT EXISTS idx_notifications_user
ON notifications(user_id);

CREATE INDEX IF NOT EXISTS idx_notifications_read
ON notifications(is_read);