CREATE INDEX IF NOT EXISTS idx_lawyers_city
ON lawyers(city);

CREATE INDEX IF NOT EXISTS idx_lawyers_state
ON lawyers(state);

CREATE INDEX IF NOT EXISTS idx_lawyer_specializations_lawyer
ON lawyer_specializations(lawyer_id);

CREATE INDEX IF NOT EXISTS idx_lawyer_languages_lawyer
ON lawyer_languages(lawyer_id);

CREATE INDEX IF NOT EXISTS idx_lawyer_locations_lawyer
ON lawyer_locations(lawyer_id);

CREATE INDEX IF NOT EXISTS idx_case_lawyer_referrals_case
ON case_lawyer_referrals(case_id);

CREATE INDEX IF NOT EXISTS idx_case_lawyer_referrals_lawyer
ON case_lawyer_referrals(lawyer_id);