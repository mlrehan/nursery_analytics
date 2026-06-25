-- ============================================================================
-- 004_app_settings.sql
-- Single-row table holding white-label branding the admin can change in-app:
-- product name, logo (letter or uploaded image), and browser/site icon (favicon).
-- ============================================================================
CREATE TABLE IF NOT EXISTS app_settings (
    id            SMALLINT PRIMARY KEY DEFAULT 1,
    brand_name    VARCHAR(120) NOT NULL DEFAULT 'Nursery Analytics',
    brand_tagline VARCHAR(160),
    logo_url      TEXT,          -- data-URL or http URL; NULL => first letter of name
    icon_url      TEXT,          -- favicon (data-URL or http URL); NULL => default
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT app_settings_singleton CHECK (id = 1)
);

INSERT INTO app_settings (id, brand_name, brand_tagline)
VALUES (1, 'Nursery Analytics', 'Early Years Intelligence')
ON CONFLICT (id) DO NOTHING;

-- capability for managing branding/settings (admins already get everything)
INSERT INTO permissions (code, description) VALUES
    ('admin.manage_settings', 'Manage branding and app settings')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = 'admin.manage_settings'
WHERE r.slug = 'admin'
ON CONFLICT DO NOTHING;
