-- ============================================================================
-- 002_reference_data.sql
-- Roles, permissions, the 15 dashboard modules + their widgets, and the
-- per-role DEFAULT dashboard composition. Admins can later add/remove widgets
-- per role via the role_widget_access table (API: /admin/dashboard-config).
-- Idempotent via ON CONFLICT.
-- ============================================================================

-- ─── Roles ──────────────────────────────────────────────────────────────────
INSERT INTO roles (slug, name, description, is_system) VALUES
    ('admin',      'Administrator',     'Full access; configures dashboards & users', TRUE),
    ('management', 'Management / Owner','Executive and operational oversight',        TRUE),
    ('accounts',   'Accounts / Finance','Billing, revenue and arrears',               TRUE),
    ('teacher',    'Teacher / Practitioner','Room attendance, EYFS, meals & parents', TRUE),
    ('parent',     'Parent / Guardian', 'Their own child only',                       TRUE)
ON CONFLICT (slug) DO NOTHING;

-- ─── Permissions (coarse, module-level + admin capabilities) ─────────────────
INSERT INTO permissions (code, description) VALUES
    ('admin.manage_users',      'Create and manage users'),
    ('admin.manage_dashboards', 'Configure which widgets each role sees'),
    ('admin.manage_roles',      'Manage roles and permissions'),
    ('view.executive',    'View Executive Overview'),
    ('view.occupancy',    'View Enrollment & Occupancy'),
    ('view.finance',      'View Financial & Billing'),
    ('view.staff',        'View Staff Management'),
    ('view.compliance',   'View Compliance & Regulatory'),
    ('view.eyfs',         'View Child Development / EYFS'),
    ('view.attendance',   'View Attendance & Check-in'),
    ('view.parent_comms', 'View Parent Communication'),
    ('view.nutrition',    'View Meal, Health & Nutrition'),
    ('view.multisite',    'View Multi-Site Management'),
    ('view.analytics',    'View Analytics & BI'),
    ('view.alerts',       'View Alerts & Risk'),
    ('view.operations',   'View Operations Control Panel'),
    ('view.mobile',       'View Mobile Parent/Staff'),
    ('view.ai',           'View Advanced AI / Smart Dashboard')
ON CONFLICT (code) DO NOTHING;

-- ─── Dashboard modules (15) ──────────────────────────────────────────────────
INSERT INTO dashboard_modules (key, name, icon, description, sort_order) VALUES
    ('executive',    'Executive Overview',        'gauge',      'Top decision-making layer', 1),
    ('occupancy',    'Enrollment & Occupancy',    'users',      'Capacity and utilisation', 2),
    ('finance',      'Financial & Billing',       'pound',      'Revenue, invoices, arrears', 3),
    ('staff',        'Staff Management',          'badge',      'Ratios, shifts, payroll', 4),
    ('compliance',   'Compliance & Regulatory',   'shield',     'Ofsted inspection readiness', 5),
    ('eyfs',         'Child Development (EYFS)',   'sparkles',   'Learning & development progress', 6),
    ('attendance',   'Attendance & Check-in',     'clipboard',  'Live presence and trends', 7),
    ('parent_comms', 'Parent Communication',      'chat',       'Engagement & responsiveness', 8),
    ('nutrition',    'Meal, Health & Nutrition',  'apple',      'Wellbeing tracking', 9),
    ('multisite',    'Multi-Site Management',     'building',   'Cross-branch performance', 10),
    ('analytics',    'Analytics & BI',            'trending',   'Trends and forecasting', 11),
    ('alerts',       'Alerts & Risk',             'alert',      'What needs attention now', 12),
    ('operations',   'Operations Control Panel',  'cog',        'Daily nursery control', 13),
    ('mobile',       'Mobile Parent / Staff',     'phone',      'App summary view', 14),
    ('ai',           'Advanced AI / Smart',       'cpu',        'Predictive intelligence', 15)
ON CONFLICT (key) DO NOTHING;

-- ─── Widgets ──────────────────────────────────────────────────────────────────
-- helper: module id by key resolved inline via subquery
INSERT INTO dashboard_widgets (module_id, key, title, viz_type, description, span, sort_order) VALUES
  -- Executive
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.enrolled',       'Enrolled vs Capacity',        'kpi',         'Children enrolled against licensed capacity', 3, 1),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.occupancy',      'Occupancy Rate',              'gauge',       'Group occupancy %', 3, 2),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.revenue_mtd',    'Revenue (MTD)',               'kpi',         'Month-to-date billed revenue', 3, 3),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.arrears',        'Outstanding Arrears',         'kpi',         'Unpaid + overdue balance', 3, 4),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.revenue_trend',  'Revenue Trend & Forecast',    'line',        'Monthly revenue with 90-day forecast', 8, 5),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.profit',         'Profit Estimate',             'kpi',         'Income vs staffing + overhead', 4, 6),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.waitlist',       'Waiting List',                'kpi',         'Children on the waiting list', 3, 7),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.staff_status',   'Staff Coverage',              'kpi',         'Ratio safety status', 3, 8),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.alerts',         'Alerts Summary',              'table',       'Open compliance / staffing / payment alerts', 6, 9),
  ((SELECT id FROM dashboard_modules WHERE key='executive'), 'exec.site_breakdown', 'Occupancy by Site',           'bar',         'Occupancy across sites', 6, 10),

  -- Occupancy
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.capacity',        'Capacity vs Filled',          'kpi',         'Filled places vs capacity', 3, 1),
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.rate',            'Occupancy Rate',              'gauge',       'Overall occupancy %', 3, 2),
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.admissions',      'New Admissions (30d)',        'kpi',         'Admissions in last 30 days', 3, 3),
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.withdrawals',     'Withdrawals (30d)',           'kpi',         'Withdrawals in last 30 days', 3, 4),
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.by_room',         'Occupancy by Room Type',      'bar',         'Baby / Toddler / Preschool', 6, 5),
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.age_dist',        'Age Distribution',            'bar',         'Children by age band', 6, 6),
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.waitlist_conv',   'Waitlist Conversion',         'funnel',      'Enquiry → waitlist → enrolled', 6, 7),
  ((SELECT id FROM dashboard_modules WHERE key='occupancy'), 'occ.forecast',        'Occupancy Forecast (6m)',     'line',        'Projected occupancy', 6, 8),

  -- Finance
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.billed',          'Billed This Month',           'kpi',         'Invoiced amount (current month)', 3, 1),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.collected',       'Collected This Month',        'kpi',         'Payments received', 3, 2),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.arrears',         'Outstanding Debt',            'kpi',         'Aged receivables total', 3, 3),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.success_rate',    'Payment Success Rate',        'gauge',       'Successful payment attempts %', 3, 4),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.paid_unpaid',     'Paid vs Unpaid',              'pie',         'Invoice status split', 4, 5),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.aged',            'Aged Receivables',            'bar',         'Debt by ageing bucket', 4, 6),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.breakdown',       'Revenue Breakdown',           'stacked_bar', 'Private vs funding vs discount', 8, 7),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.per_room',        'Profit per Room Type',        'bar',         'Contribution by room type', 4, 8),
  ((SELECT id FROM dashboard_modules WHERE key='finance'), 'fin.late_alerts',     'Late Payment Alerts',         'table',       'Overdue invoices', 6, 9),

  -- Staff
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.on_duty',       'Staff On Duty Today',         'kpi',         'Headcount present today', 3, 1),
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.ratio',         'Ratio Compliance',            'gauge',       'Rooms meeting EYFS ratio %', 3, 2),
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.absence',       'Absence Rate (30d)',          'kpi',         'Shifts lost to absence', 3, 3),
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.overtime',      'Overtime Hours (30d)',        'kpi',         'Total overtime', 3, 4),
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.ratio_room',    'Ratio by Room',               'bar',         'Children-per-staff vs required', 6, 5),
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.quals',         'Qualification Mix',           'pie',         'EYFS qualification levels', 6, 6),
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.utilisation',   'Staff Utilisation Trend',     'line',        'Hours worked vs scheduled', 6, 7),
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.payroll',       'Payroll Summary',             'kpi',         'Estimated payroll cost (30d)', 3, 8),
  ((SELECT id FROM dashboard_modules WHERE key='staff'), 'staff.agency',        'Agency Usage',                'kpi',         'Agency share of hours', 3, 9),

  -- Compliance
  ((SELECT id FROM dashboard_modules WHERE key='compliance'), 'comp.readiness',     'Audit Readiness Score',       'gauge',       'Composite inspection-readiness %', 4, 1),
  ((SELECT id FROM dashboard_modules WHERE key='compliance'), 'comp.incidents_open','Open Incidents',              'kpi',         'Incidents not yet closed', 4, 2),
  ((SELECT id FROM dashboard_modules WHERE key='compliance'), 'comp.dbs',           'DBS Checks',                  'kpi',         'Valid / expiring / expired', 4, 3),
  ((SELECT id FROM dashboard_modules WHERE key='compliance'), 'comp.incident_type', 'Incidents by Type',           'bar',         'Accident / safeguarding / medication', 6, 4),
  ((SELECT id FROM dashboard_modules WHERE key='compliance'), 'comp.incident_trend','Incident Trend',              'line',        'Reported vs closed over time', 6, 5),
  ((SELECT id FROM dashboard_modules WHERE key='compliance'), 'comp.checklist',     'Ofsted Checklist',            'table',       'Inspection checklist status', 12, 6),

  -- EYFS
  ((SELECT id FROM dashboard_modules WHERE key='eyfs'), 'eyfs.on_track',      'Children On Track',           'gauge',       '% meeting expected development', 4, 1),
  ((SELECT id FROM dashboard_modules WHERE key='eyfs'), 'eyfs.observations',  'Observations (30d)',          'kpi',         'Observations logged', 4, 2),
  ((SELECT id FROM dashboard_modules WHERE key='eyfs'), 'eyfs.at_risk',       'At-Risk Children',            'kpi',         'Flagged below expected', 4, 3),
  ((SELECT id FROM dashboard_modules WHERE key='eyfs'), 'eyfs.by_area',       'Progress by Area',            'bar',         'Seven areas of EYFS', 6, 4),
  ((SELECT id FROM dashboard_modules WHERE key='eyfs'), 'eyfs.by_age',        'Progress by Age Group',       'stacked_bar', 'Status mix per age band', 6, 5),
  ((SELECT id FROM dashboard_modules WHERE key='eyfs'), 'eyfs.heatmap',       'Development Heatmap',         'heatmap',     'Area × age-group on-track %', 12, 6),

  -- Attendance
  ((SELECT id FROM dashboard_modules WHERE key='attendance'), 'att.present',       'Present Today',               'kpi',         'Children checked in', 3, 1),
  ((SELECT id FROM dashboard_modules WHERE key='attendance'), 'att.rate',          'Attendance Rate (30d)',       'gauge',       'Present vs expected', 3, 2),
  ((SELECT id FROM dashboard_modules WHERE key='attendance'), 'att.absent',        'Absent Today',                'kpi',         'Illness / holiday / unexplained', 3, 3),
  ((SELECT id FROM dashboard_modules WHERE key='attendance'), 'att.late',          'Late Pickups (30d)',          'kpi',         'Late collection events', 3, 4),
  ((SELECT id FROM dashboard_modules WHERE key='attendance'), 'att.trend',         'Attendance Trend',            'line',        'Daily attendance rate', 8, 5),
  ((SELECT id FROM dashboard_modules WHERE key='attendance'), 'att.absence_mix',   'Absence Reasons',             'pie',         'Reason breakdown', 4, 6),
  ((SELECT id FROM dashboard_modules WHERE key='attendance'), 'att.heatmap',       'Attendance Heatmap',          'heatmap',     'Day-of-week × room', 12, 7),

  -- Parent communication
  ((SELECT id FROM dashboard_modules WHERE key='parent_comms'), 'pc.messages',       'Messages (30d)',              'kpi',         'Sent + received', 3, 1),
  ((SELECT id FROM dashboard_modules WHERE key='parent_comms'), 'pc.response',       'Avg Response Time',           'kpi',         'Staff reply time (mins)', 3, 2),
  ((SELECT id FROM dashboard_modules WHERE key='parent_comms'), 'pc.read_rate',      'Read Rate',                   'gauge',       'Notifications read %', 3, 3),
  ((SELECT id FROM dashboard_modules WHERE key='parent_comms'), 'pc.reports',        'Daily Reports Sent (30d)',    'kpi',         'Meals / naps / activities', 3, 4),
  ((SELECT id FROM dashboard_modules WHERE key='parent_comms'), 'pc.volume_trend',   'Message Volume Trend',        'line',        'Inbound vs outbound', 12, 5),

  -- Nutrition
  ((SELECT id FROM dashboard_modules WHERE key='nutrition'), 'nut.intake',        'Avg Meal Intake',             'gauge',       'Average intake %', 4, 1),
  ((SELECT id FROM dashboard_modules WHERE key='nutrition'), 'nut.allergy',       'Allergy Alerts',              'kpi',         'Children with allergies', 4, 2),
  ((SELECT id FROM dashboard_modules WHERE key='nutrition'), 'nut.meals_logged',  'Meals Logged (7d)',           'kpi',         'Meal records', 4, 3),
  ((SELECT id FROM dashboard_modules WHERE key='nutrition'), 'nut.by_meal',       'Intake by Meal',              'bar',         'Breakfast / lunch / snack / tea', 12, 4),

  -- Multi-site
  ((SELECT id FROM dashboard_modules WHERE key='multisite'), 'ms.ranking',        'Site Performance Ranking',    'table',       'Composite score per site', 12, 1),
  ((SELECT id FROM dashboard_modules WHERE key='multisite'), 'ms.occupancy',      'Occupancy by Site',           'bar',         'Occupancy % per site', 6, 2),
  ((SELECT id FROM dashboard_modules WHERE key='multisite'), 'ms.revenue',        'Revenue by Site',             'bar',         'Revenue per site (MTD)', 6, 3),

  -- Analytics & BI
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.occ_trend',      'Occupancy Trend',             'line',        'Long-run occupancy', 6, 1),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.rev_growth',     'Revenue Growth',              'line',        'MoM revenue', 6, 2),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.cost_ratio',     'Staff Cost vs Revenue',       'line',        'Cost ratio trend', 6, 3),
  ((SELECT id FROM dashboard_modules WHERE key='analytics'), 'bi.funnel',         'Enquiry → Enrollment',        'funnel',      'Conversion funnel', 6, 4),

  -- Alerts
  ((SELECT id FROM dashboard_modules WHERE key='alerts'), 'alert.summary',     'Active Alerts',               'kpi',         'Total open alerts', 4, 1),
  ((SELECT id FROM dashboard_modules WHERE key='alerts'), 'alert.by_severity', 'Alerts by Severity',          'pie',         'High / medium / low', 4, 2),
  ((SELECT id FROM dashboard_modules WHERE key='alerts'), 'alert.list',        'Alert Feed',                  'table',       'Prioritised alert list', 12, 3),

  -- Operations
  ((SELECT id FROM dashboard_modules WHERE key='operations'), 'ops.today',         'Today at a Glance',           'kpi',         'Present children + staff on duty', 6, 1),
  ((SELECT id FROM dashboard_modules WHERE key='operations'), 'ops.rota',          'Staff Rota (Today)',          'table',       'Live rota view', 12, 2),

  -- Mobile
  ((SELECT id FROM dashboard_modules WHERE key='mobile'), 'mob.child_status',  'My Child Status',             'kpi',         'Attendance + last update', 6, 1),
  ((SELECT id FROM dashboard_modules WHERE key='mobile'), 'mob.updates',       'Recent Updates',              'table',       'Meals / naps / activities', 12, 2),

  -- AI
  ((SELECT id FROM dashboard_modules WHERE key='ai'), 'ai.occ_predict',    'Predicted Occupancy Gaps',    'line',        'Forecast vs capacity', 6, 1),
  ((SELECT id FROM dashboard_modules WHERE key='ai'), 'ai.staff_predict',  'Predicted Staffing Shortfall','bar',         'Projected ratio risk', 6, 2),
  ((SELECT id FROM dashboard_modules WHERE key='ai'), 'ai.churn',          'Parent Churn Risk',           'table',       'At-risk families', 12, 3)
ON CONFLICT (key) DO NOTHING;

-- ─── Grant module-view permissions to roles ──────────────────────────────────
-- admin: everything
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p WHERE r.slug='admin'
ON CONFLICT DO NOTHING;

-- management: all view.* (not admin.*)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code LIKE 'view.%'
WHERE r.slug='management'
ON CONFLICT DO NOTHING;

-- accounts
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
  ON p.code IN ('view.finance','view.occupancy','view.analytics','view.alerts','view.executive')
WHERE r.slug='accounts'
ON CONFLICT DO NOTHING;

-- teacher
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
  ON p.code IN ('view.attendance','view.eyfs','view.nutrition','view.parent_comms','view.operations')
WHERE r.slug='teacher'
ON CONFLICT DO NOTHING;

-- parent
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
  ON p.code IN ('view.mobile','view.attendance','view.eyfs','view.nutrition','view.parent_comms')
WHERE r.slug='parent'
ON CONFLICT DO NOTHING;

-- ─── Default dashboard composition (role_widget_access) ──────────────────────
-- Enable every widget belonging to a module the role is permitted to view.
-- 'view.<module_key>' permission -> all widgets of that module.
INSERT INTO role_widget_access (role_id, widget_id, is_enabled, position)
SELECT rp.role_id, w.id, TRUE, w.sort_order
FROM role_permissions rp
JOIN permissions p        ON p.id = rp.permission_id AND p.code LIKE 'view.%'
JOIN dashboard_modules m  ON m.key = substring(p.code FROM 6)
JOIN dashboard_widgets w  ON w.module_id = m.id
ON CONFLICT DO NOTHING;
