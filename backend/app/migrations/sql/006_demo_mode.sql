-- ============================================================================
-- 006_demo_mode.sql
-- A flag that shows a "fictional / demo data" banner everywhere (incl. public
-- share pages). Admins turn it OFF once real nursery data is loaded.
-- ============================================================================
ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS demo_mode BOOLEAN NOT NULL DEFAULT TRUE;
