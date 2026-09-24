CREATE TABLE IF NOT EXISTS password_resets (
    reset_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    reset_token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_password_reset_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);