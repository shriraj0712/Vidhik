INSERT INTO roles (role_name, description)
VALUES
    ('user', 'Regular application user'),
    ('lawyer', 'Verified legal professional'),
    ('admin', 'System administrator')
ON CONFLICT (role_name) DO NOTHING;