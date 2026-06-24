-- ============================================================================
-- 003_profiles_and_widgets.sql
-- - user profile fields (all roles can maintain their own profile)
-- - a few high-value UK-specific dashboard widgets
-- Idempotent.
-- ============================================================================

-- ─── Profile fields on users ─────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone      VARCHAR(40);
ALTER TABLE users ADD COLUMN IF NOT EXISTS job_title  VARCHAR(120);
ALTER TABLE users ADD COLUMN IF NOT EXISTS address    TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS about       TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url  TEXT;   -- data-URL or http URL

-- ─── New widgets (UK nursery focus) ──────────────────────────────────────────
INSERT INTO dashboard_widgets (module_id, key, title, viz_type, description, span, sort_order) VALUES
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.rev_per_child', 'Revenue per Child', 'kpi',
     'Average monthly revenue per enrolled child', 3, 11),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.funding', 'Funded Hours Mix', 'pie',
     'Private vs 15h / 30h government-funded places', 4, 10),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.rev_per_child', 'Revenue per Child', 'kpi',
     'Average monthly revenue per enrolled child', 3, 11),
  ((SELECT id FROM dashboard_modules WHERE key='attendance'), 'att.time_of_day', 'Utilisation by Session', 'bar',
     'Average AM vs PM occupancy — spot afternoon gaps', 6, 8),
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.funding', 'Funded Hours Mix', 'pie',
     'Private vs 15h / 30h funded places', 6, 9)
ON CONFLICT (key) DO NOTHING;

-- Grant the new widgets to every role that already has the module's view permission
-- (mirrors the default-composition rule from migration 002, but only for these keys).
INSERT INTO role_widget_access (role_id, widget_id, is_enabled, position)
SELECT rp.role_id, w.id, TRUE, w.sort_order
FROM role_permissions rp
JOIN permissions p        ON p.id = rp.permission_id AND p.code LIKE 'view.%'
JOIN dashboard_modules m  ON m.key = substring(p.code FROM 6)
JOIN dashboard_widgets w  ON w.module_id = m.id
WHERE w.key IN ('exec.rev_per_child','fin.funding','fin.rev_per_child','att.time_of_day','occ.funding')
ON CONFLICT DO NOTHING;
