CREATE TABLE IF NOT EXISTS provider_tokens (
    provider TEXT NOT NULL,
    profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    encrypted_refresh_token TEXT NOT NULL,
    iv TEXT NOT NULL,
    key_version TEXT NOT NULL DEFAULT 'v1',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, profile_id)
);

CREATE INDEX IF NOT EXISTS idx_provider_tokens_updated_at
    ON provider_tokens(updated_at);
