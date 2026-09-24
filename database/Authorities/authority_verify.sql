SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'authorities',
    'case_authorities'
)
ORDER BY table_name;