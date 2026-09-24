CREATE INDEX IF NOT EXISTS idx_complaints_case
ON complaints(case_id);

CREATE INDEX IF NOT EXISTS idx_complaints_authority
ON complaints(authority_id);

CREATE INDEX IF NOT EXISTS idx_complaints_status
ON complaints(status);

CREATE INDEX IF NOT EXISTS idx_complaints_type
ON complaints(complaint_type);

CREATE INDEX IF NOT EXISTS idx_complaints_date
ON complaints(complaint_date);