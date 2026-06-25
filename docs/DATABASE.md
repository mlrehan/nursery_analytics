# Database Guide

This explains **every table** in the platform — what it stores and why it exists —
so you can map your own nursery data to it and make changes confidently.

The database is a **PostgreSQL star schema**: a handful of **dimension** tables
(the “things” — sites, rooms, children, staff) and several **fact** tables (the
“events” — attendance, invoices, incidents). Dashboards are just summaries of these.

```
                         ┌─────────────┐
                         │  dim_site   │  the nurseries
                         └──────┬──────┘
              ┌─────────────────┼───────────────────┐
        ┌─────▼─────┐     ┌─────▼─────┐        ┌─────▼─────┐
        │ dim_room  │     │ dim_staff │        │ dim_parent│
        └─────┬─────┘     └─────┬─────┘        └─────┬─────┘
              │                 │                    │
        ┌─────▼─────┐           │              ┌─────▼─────┐
        │ dim_child │───────────┴──────────────│  (parent) │
        └─────┬─────┘                          └───────────┘
              │  facts reference children/staff/sites:
   fact_attendance · fact_enrollment_event · fact_invoice · fact_payment
   fact_staff_shift · fact_incident · fact_eyfs_observation · fact_meal · fact_message
```

> **Naming convention:** `dim_*` = master/reference data, `fact_*` = dated events,
> everything else = the app’s own security/config tables.

---

## A. Security & configuration tables

| Table | What it stores | Why it exists |
|---|---|---|
| `users` | Login accounts: email, hashed password, role, optional linked site/child/staff, **profile** (phone, job title, address, about, avatar) | Who can log in and what they are scoped to |
| `roles` | The 5 roles (admin, management, accounts, teacher, parent) | Groups users for permissions |
| `permissions` | Capability codes (`view.finance`, `admin.manage_users`, …) | The fine-grained “what you may do” list |
| `role_permissions` | Which permissions each role has | Decides which **dashboards** a role can open |
| `dashboard_modules` | The 15 dashboards (key, name, icon) | The catalogue of available dashboards |
| `dashboard_widgets` | Each report/card (key, title, chart type, size) and which module it belongs to | The catalogue of available reports |
| `role_widget_access` | Which widgets each role sees, on/off | Lets admins compose each role’s dashboard |
| `schema_migrations` | Which DB migrations have run | Tracks/automates schema upgrades |

**Key idea:** a role sees a dashboard only if it has the `view.<module>` permission
(`role_permissions`) **and** the individual cards switched on (`role_widget_access`).
Both are editable by an admin in the app — no code needed.

---

## B. Dimension tables (your master data)

### `dim_site` — the nurseries
Each physical nursery: `name`, `borough`, `postcode`, `capacity` (licensed places),
`opened_on`, `monthly_overhead` (rent, utilities, etc. — used for profit estimates).
**Why:** every number can be sliced by site; capacity drives occupancy %.

### `dim_room` — rooms within a site
`site_id`, `name`, `room_type` (`baby` / `toddler` / `preschool`), `capacity`,
`required_ratio` (how many children one staff member can look after: baby 3, toddler 4, preschool 8).
**Why:** room-level occupancy and **staff-ratio compliance**.

### `dim_child` — children on roll (and waitlist/withdrawn)
`site_id`, `room_id`, `parent_id`, names, `dob`, `gender`, `enrollment_date`,
`status` (`active` / `waitlist` / `withdrawn`), `funding_type`
(`private` / `funded_15` / `funded_30`), `monthly_fee`, `allergies`.
**funding_type:** Who is paying for this child’s nursery cost — and how much government support they get
private: No government funding, Parents pay full fee
funded_15: 15 hours/week paid by the government, Parents pay remaining hours
funded_30: 30 hours/week government funded childcare, Parents pay extra hours
**Why:** the heart of occupancy, revenue-per-child, funding mix and EYFS.

### `dim_parent` — parents/guardians
`site_id`, names, `email`, `phone`. **Why:** links children to families and powers
parent-communication metrics.

### `dim_staff` — employees
`site_id`, names, `role_title`, `qualification_level` (0/2/3/6 EYFS),
`dbs_status` (`valid`/`expiring`/`expired`), `dbs_expiry`, `contract_hours`,
`hourly_rate`, `is_agency`, `employment_status`.
**Why:** ratios, payroll cost, qualification mix and DBS compliance.

### `dim_date` — calendar
One row per date with year/quarter/month/day-of-week/weekend flags.
**Why:** consistent time grouping and term-time/holiday analysis.

---

## C. Fact tables (the dated events the dashboards summarise)

### `fact_attendance` — daily attendance
One row per child per day: `date`, `status` (`present` / `absent_illness` /
`absent_holiday` / `unexplained`), `check_in`, `check_out`, `late_pickup`.
**Powers:** Attendance dashboard, AM/PM utilisation, present-today on Executive/Ops.

### `fact_enrollment_event` — enquiry → admission → withdrawal
`child_id`, `event_type` (`enquiry` / `waitlist_join` / `waitlist_convert` /
`admission` / `withdrawal`), `event_date`.
**Powers:** admissions/withdrawals, the waitlist conversion funnel, occupancy forecast.

### `fact_invoice` — monthly bills
`child_id`, `issue_date`, `due_date`, `period_month`, `amount` (net charged),
`funding_amount`, `discount_amount`, `status` (`paid`/`unpaid`/`overdue`/`partial`),
`paid_date`. **Powers:** billed revenue, arrears, aged receivables, funding mix.

### `fact_payment` — money received
`invoice_id`, `payment_date`, `amount`, `method` (`direct_debit`/`card`/
`bank_transfer`), `success`, `is_refund`.
**Powers:** collected revenue, payment success rate, refunds.

### `fact_staff_shift` — rota & worked hours
`staff_id`, `room_id`, `date`, `hours_scheduled`, `hours_worked`, `overtime_hours`,
`absent`, `absence_reason`. **Powers:** on-duty count, ratios, absence/overtime,
payroll, utilisation, the live rota.

### `fact_incident` — accidents/incidents/safeguarding/medication
`child_id`, `incident_type`, `severity` (`low`/`medium`/`high`), `reported_date`,
`status` (`open`/`closed`), `closed_date`.
**Powers:** compliance, audit-readiness, alerts.

### `fact_eyfs_observation` — development tracking
### Every time a teacher observes a child (playing, talking, drawing, etc.), they record it here.
### In EYFS (Early Years Foundation Stage), children are tracked in key areas:
**EYFS areas**:   communication, physical, pse (personal, social, emotiona)
                  literacy (reading & writing), numeracy (counting, math thinking) 
`child_id`, `observation_date`, `area` (communication/physical/pse/literacy/numeracy),
`status` (`emerging`/`expected`/`exceeding`), `on_track`.
**Powers:** EYFS dashboard, at-risk children, the development heatmap.

### `fact_meal` — meals & intake
`child_id`, `date`, `meal_type` (breakfast/lunch/snack/tea), `intake_pct`,
`allergy_flag`. **Powers:** nutrition dashboard.

### `fact_message` — parent communications
`parent_id`, `staff_id`, `sent_at`, `direction` (`inbound`/`outbound`),
`message_type` (`report`/`message`/`announcement`), `is_read`, `response_minutes`.
**Powers:** parent-communication engagement metrics.

---

## D. How a number becomes a report

Example — **Occupancy %**:
`Occupancy = (Number of children enrolled ÷ Total licensed capacity) × 100`
`COUNT(dim_child WHERE status='active')  ÷  SUM(dim_site.capacity)`.
**
      If a nursery has:

      Licensed capacity: 60 children
      Currently enrolled: 48 children

      👉 Occupancy = (48 ÷ 60) × 100 = 80%
**
The backend computes these with pandas in `backend/app/analytics/<module>.py`, the
API returns them, and the React frontend draws the chart. If your real data lands in
these tables with the same columns, **every report works automatically** — see
[DATA_INTEGRATION.md](DATA_INTEGRATION.md).

## E. Changing the schema yourself

The schema is defined by numbered SQL files in
`backend/app/migrations/sql/` (`001_…`, `002_…`, `003_…`). To change it:

1. Add a new file, e.g. `004_add_column.sql`, with `ALTER TABLE … ADD COLUMN IF NOT EXISTS …`.
2. Restart the backend (or run `python -m app.cli migrate`). Applied files are tracked
   in `schema_migrations` and never re-run.

Never edit an already-applied migration — always add a new one.
