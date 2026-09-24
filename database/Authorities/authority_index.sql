CREATE INDEX IF NOT EXISTS idx_case_authorities_case
ON case_authorities(case_id);

CREATE INDEX IF NOT EXISTS idx_case_authorities_authority
ON case_authorities(authority_id);

CREATE INDEX IF NOT EXISTS idx_authorities_type
ON authorities(authority_type);

CREATE INDEX IF NOT EXISTS idx_authorities_state
ON authorities(state);