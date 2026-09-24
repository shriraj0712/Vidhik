SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'reminders',
    'notifications'
)
ORDER BY table_name;