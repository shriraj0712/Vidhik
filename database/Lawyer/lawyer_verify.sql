SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'lawyers',
    'lawyer_specializations',
    'lawyer_languages',
    'lawyer_locations',
    'legal_aid_organizations',
    'case_lawyer_referrals'
)
ORDER BY table_name;