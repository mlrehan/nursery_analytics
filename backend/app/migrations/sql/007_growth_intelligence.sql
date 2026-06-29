-- ============================================================================
-- 007_growth_intelligence.sql
-- Business-Intelligence + Growth-Intelligence layer:
--   * enquiry "source" + a "visit" stage for the marketing funnel
--   * new widgets under Analytics & BI, Multi-Site, and Advanced AI
-- ============================================================================

-- enquiry source (Google / Referral / Walk-in / Social / Other) on enquiry events
ALTER TABLE fact_enrollment_event ADD COLUMN IF NOT EXISTS source VARCHAR(30);

-- ─── New widgets ──────────────────────────────────────────────────────────────
INSERT INTO dashboard_widgets (module_id, key, title, viz_type, description, span, sort_order) VALUES
  -- Analytics & BI (growth intelligence)
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.enroll_growth',   'Enrollment Growth',      'kpi',   'Net new children vs leavers in the period', 3, 10),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.churn',            'Churn Rate',             'kpi',   'Children leaving as % of roll', 3, 11),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.retention',        'Retention Rate',         'kpi',   'Children retained (100% − churn)', 3, 12),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.staff_cost_ratio', 'Staff Cost Ratio',       'kpi',   'Staff cost as % of revenue', 3, 13),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.collection_eff',   'Fee Collection Efficiency','gauge','Collected ÷ billed', 4, 14),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.discount_leakage', 'Discount Leakage',       'kpi',   'Revenue given away in discounts', 4, 15),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.engagement',       'Parent Engagement',      'gauge', 'Notifications read by parents', 4, 16),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.dev_score',        'Development Progress',   'gauge', 'Cohort EYFS on-track score', 4, 17),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.transition_ready', 'Room Transition Readiness','kpi', 'Children old enough to move room', 3, 18),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.enquiry_sources',  'Enquiry Sources',        'pie',   'Where new enquiries come from', 6, 19),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.visit_funnel',     'Enquiry → Visit → Enrolled','funnel','Marketing conversion funnel', 6, 20),

  -- Multi-Site (branch comparison)
  ((SELECT id FROM dashboard_modules WHERE key='multisite'), 'ms.profit',     'Profit by Site (MTD est.)', 'bar',   'Revenue − payroll − overhead per site', 6, 4),
  ((SELECT id FROM dashboard_modules WHERE key='multisite'), 'ms.staff_eff',  'Staff Efficiency by Site',  'bar',   'Children supported per staff member', 6, 5),
  ((SELECT id FROM dashboard_modules WHERE key='multisite'), 'ms.best_worst', 'Best vs Worst Branch',      'table', 'Top and bottom performer with the gap', 12, 6),

  -- Advanced AI (predictive growth)
  ((SELECT id FROM dashboard_modules WHERE key='ai'), 'ai.empty_seat',   'Predicted Empty Seats', 'kpi',   'Forecast vacant places next month', 3, 4),
  ((SELECT id FROM dashboard_modules WHERE key='ai'), 'ai.revenue_risk', 'Revenue at Risk',       'kpi',   'Monthly income lost to empty seats', 3, 5),
  ((SELECT id FROM dashboard_modules WHERE key='ai'), 'ai.waitlist_prob','Waitlist Conversion',   'kpi',   'Historic chance a waitlisted child enrols', 3, 6),
  ((SELECT id FROM dashboard_modules WHERE key='ai'), 'ai.fee_risk',     'Fee Collection Risk',   'table', 'Families most likely to fall into arrears', 12, 7)
ON CONFLICT (key) DO NOTHING;

-- Grant the new widgets to every role that already has the module's view permission
INSERT INTO role_widget_access (role_id, widget_id, is_enabled, position)
SELECT rp.role_id, w.id, TRUE, w.sort_order
FROM role_permissions rp
JOIN permissions p        ON p.id = rp.permission_id AND p.code LIKE 'view.%'
JOIN dashboard_modules m  ON m.key = substring(p.code FROM 6)
JOIN dashboard_widgets w  ON w.module_id = m.id
WHERE w.key IN ('bi.enroll_growth','bi.churn','bi.retention','bi.staff_cost_ratio','bi.collection_eff',
                'bi.discount_leakage','bi.engagement','bi.dev_score','bi.transition_ready',
                'bi.enquiry_sources','bi.visit_funnel','ms.profit','ms.staff_eff','ms.best_worst',
                'ai.empty_seat','ai.revenue_risk','ai.waitlist_prob','ai.fee_risk')
ON CONFLICT DO NOTHING;
