SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'users',
    'user_profiles',
    'roles',
    'user_roles',
    'login_sessions',
    'password_resets'
)
ORDER BY table_name;