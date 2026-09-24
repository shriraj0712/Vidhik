CREATE INDEX IF NOT EXISTS idx_feedback_user
ON feedback(user_id);

CREATE INDEX IF NOT EXISTS idx_feedback_case
ON feedback(case_id);

CREATE INDEX IF NOT EXISTS idx_feedback_status
ON feedback(status);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user
ON audit_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action
ON audit_logs(action);

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity
ON audit_logs(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created
ON audit_logs(created_at);