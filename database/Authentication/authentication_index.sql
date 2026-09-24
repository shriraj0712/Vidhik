CREATE INDEX IF NOT EXISTS idx_user_profiles_user
ON user_profiles(user_id);

CREATE INDEX IF NOT EXISTS idx_user_roles_user
ON user_roles(user_id);

CREATE INDEX IF NOT EXISTS idx_user_roles_role
ON user_roles(role_id);

CREATE INDEX IF NOT EXISTS idx_login_sessions_user
ON login_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_login_sessions_expires
ON login_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_password_resets_user
ON password_resets(user_id);

CREATE INDEX IF NOT EXISTS idx_password_resets_expires
ON password_resets(expires_at);