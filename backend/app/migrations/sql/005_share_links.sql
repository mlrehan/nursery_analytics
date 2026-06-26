-- ============================================================================
-- 005_share_links.sql
-- Managed public share links: each is revocable, has its own expiry, and counts
-- views. The token is an opaque, unguessable random string (the public URL id).
-- ============================================================================
CREATE TABLE IF NOT EXISTS share_links (
    token          VARCHAR(64) PRIMARY KEY,
    module_key     VARCHAR(60) NOT NULL,
    site_id        INTEGER,
    child_id       INTEGER,
    window_days    INTEGER NOT NULL DEFAULT 90,
    label          VARCHAR(160),
    created_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at     TIMESTAMPTZ,                 -- NULL = never expires
    revoked        BOOLEAN NOT NULL DEFAULT FALSE,
    view_count     INTEGER NOT NULL DEFAULT 0,
    last_viewed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_share_links_creator ON share_links(created_by);
