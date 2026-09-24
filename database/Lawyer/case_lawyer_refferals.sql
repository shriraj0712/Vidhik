CREATE TABLE IF NOT EXISTS case_lawyer_referrals (
    referral_id BIGSERIAL PRIMARY KEY,
    case_id BIGINT NOT NULL,
    lawyer_id BIGINT NOT NULL,
    organization_id BIGINT,
    referral_reason TEXT,
    referral_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    referred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_referral_case
        FOREIGN KEY (case_id)
        REFERENCES cases(case_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_referral_lawyer
        FOREIGN KEY (lawyer_id)
        REFERENCES lawyers(lawyer_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_referral_organization
        FOREIGN KEY (organization_id)
        REFERENCES legal_aid_organizations(organization_id)
        ON DELETE SET NULL
);