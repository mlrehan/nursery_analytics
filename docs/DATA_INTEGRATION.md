# Connecting Your Real Nursery Data

This is a step-by-step, non-technical-friendly guide to replacing the demo data with
your nursery’s real data. There are **three ways** to feed the platform — pick the one
that matches what your current system offers:

| You have… | Use method |
|---|---|
| Spreadsheets / exports | **A — Excel/CSV import** (easiest) |
| Direct access to your management-system database | **B — Database-to-database** |
| An API from your nursery software (e.g. Famly, Blossom, iConnect) | **C — API sync** |

All three load into the **same tables** described in [DATABASE.md](DATABASE.md). Once
data is in those tables, **every dashboard works automatically** — no code changes.

---

## Step 0 — Turn off the demo data (once)

The demo seed only fills an **empty** database, so it won’t overwrite your data. To be
safe on a real deployment, set in `.env` (or `.env.prod`):

```
SEED_ON_STARTUP=false
```

To clear the demo data and start clean:

```bash
docker compose exec backend python -m app.integration.import_csv --truncate
```
…or simply `docker compose down -v` before your first real load (this also wipes
the database volume).

---

## Method A — Excel / CSV import (recommended start)

### 1. Export one CSV per table

Create a folder (e.g. `my_data/`) with any of these files. **Skip what you don’t have.**
Column headers must match exactly; provide your own **consistent integer IDs** so the
files link together (a child’s `site_id` must equal a real `dim_site.id` you supplied).

| File | Required columns | Optional |
|---|---|---|
| `sites.csv` | `id, name, borough, postcode, capacity` | `opened_on, monthly_overhead` |
| `rooms.csv` | `id, site_id, name, room_type, capacity, required_ratio` | |
| `parents.csv` | `id, site_id, first_name, last_name, email` | `phone` |
| `children.csv` | `id, site_id, first_name, last_name, dob, status` | `room_id, parent_id, gender, enrollment_date, funding_type, monthly_fee, allergies` |
| `staff.csv` | `id, site_id, first_name, last_name, role_title, qualification_level, dbs_status` | `dbs_expiry, contract_hours, hourly_rate, is_agency, employment_status` |
| `attendance.csv` | `child_id, site_id, date, status` | `room_id, check_in, check_out, late_pickup` |
| `enrollment_events.csv` | `child_id, site_id, event_type, event_date` | |
| `invoices.csv` | `id, child_id, site_id, issue_date, due_date, period_month, amount, status` | `funding_amount, discount_amount, paid_date` |
| `payments.csv` | `invoice_id, child_id, site_id, payment_date, amount, method` | `success, is_refund` |
| `shifts.csv` | `staff_id, site_id, date, hours_scheduled, hours_worked` | `room_id, overtime_hours, absent, absence_reason` |
| `incidents.csv` | `site_id, incident_type, severity, reported_date, status` | `child_id, closed_date` |
| `eyfs.csv` | `child_id, site_id, observation_date, area, status, on_track` | |
| `meals.csv` | `child_id, site_id, date, meal_type, intake_pct` | `allergy_flag` |
| `messages.csv` | `site_id, sent_at, direction, message_type` | `parent_id, staff_id, is_read, response_minutes` |

**Allowed values** (must match exactly):
- `room_type`: `baby` / `toddler` / `preschool`
- child `status`: `active` / `waitlist` / `withdrawn`
- `funding_type`: `private` / `funded_15` / `funded_30`
- invoice `status`: `paid` / `unpaid` / `overdue` / `partial`
- `dbs_status`: `valid` / `expiring` / `expired`
- attendance `status`: `present` / `absent_illness` / `absent_holiday` / `unexplained`
- dates as `YYYY-MM-DD`; timestamps as `YYYY-MM-DD HH:MM:SS`; true/false as `true`/`false`

### 2. Run the importer

The backend container can only see files inside the `backend/` folder (it's the part
mounted into the container), so put your folder there:

```bash
# 1) place your folder at:  backend/my_data/   (sites.csv, children.csv, …)
# 2) run it (Docker):
docker compose exec backend python -m app.integration.import_csv my_data

# Local, without Docker (from the backend/ folder):
python -m app.integration.import_csv ./my_data
```
Add `--truncate` to wipe existing data first, e.g.
`... import_csv my_data --truncate`. The importer loads in the correct (foreign-key
safe) order, ignores unknown columns, and reports how many rows each file loaded.

### 3. Check it
Log in → the dashboards now reflect your data. If a number looks off, see “Validating”.

---

## Method B — Database-to-database

If you can read your current system’s database, map its tables into ours with plain
SQL. Example (PostgreSQL, your data in schema `legacy`):

```sql
-- sites
INSERT INTO dim_site (id, name, borough, postcode, capacity, monthly_overhead)
SELECT branch_id, branch_name, borough, postcode, licensed_places, monthly_costs
FROM legacy.branches;

-- children
INSERT INTO dim_child (id, site_id, room_id, first_name, last_name, dob, status,
                       funding_type, monthly_fee)
SELECT c.child_id, c.branch_id, c.room_id, c.forename, c.surname, c.date_of_birth,
       CASE WHEN c.left_date IS NULL THEN 'active' ELSE 'withdrawn' END,
       CASE c.funding WHEN '30h' THEN 'funded_30' WHEN '15h' THEN 'funded_15' ELSE 'private' END,
       c.monthly_fee
FROM legacy.children c;
```

Run these once for a migration, or put them in a scheduled job for a nightly refresh
(`TRUNCATE` the fact tables first, then re-`INSERT`). The columns to target are listed
in [DATABASE.md](DATABASE.md).

> If your data lives in MySQL/SQL Server, export to CSV (Method A) or use a tool like
> `pgloader` / Airbyte to copy across.

---

## Method C — API sync (Famly, Blossom, iConnect, etc.)

Write a small scheduled script that pulls from your software’s API and inserts into our
tables. Skeleton:

```python
import requests, psycopg
data = requests.get("https://api.yourvendor.com/children",
                    headers={"Authorization": "Bearer <KEY>"}).json()
with psycopg.connect("postgresql://nursery:...@localhost:5498/nursery_analytics") as conn:
    for c in data:
        conn.execute(
            "INSERT INTO dim_child (id, site_id, first_name, last_name, dob, status, monthly_fee) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET "
            "status=EXCLUDED.status, monthly_fee=EXCLUDED.monthly_fee",
            (c["id"], c["siteId"], c["firstName"], c["lastName"], c["dob"], c["status"], c["fee"]))
    conn.commit()
```

Run it on a schedule (cron / Task Scheduler / a small worker). The `ON CONFLICT … DO
UPDATE` pattern makes re-runs safe (upsert). Map each API endpoint to the matching
table from [DATABASE.md](DATABASE.md).

> Want a built-in `/ingest` API instead of direct DB writes? That’s a small addition —
> the same column contracts apply.

---

## How often to refresh

- **Dimensions** (sites, rooms, children, staff): when they change (daily is plenty).
- **Facts** (attendance, payments, etc.): nightly is typical; near-real-time if your
  source supports it. The dashboards cache for ~20 seconds, so fresh loads appear within
  a minute.

## Validating your load

```bash
# counts per table (runs inside the db container, using its own credentials)
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
  SELECT '\''children'\'' t, count(*) FROM dim_child
  UNION ALL SELECT '\''active'\'', count(*) FROM dim_child WHERE status='\''active'\''
  UNION ALL SELECT '\''invoices'\'', count(*) FROM fact_invoice
  UNION ALL SELECT '\''attendance'\'', count(*) FROM fact_attendance;"'
```
Then open the **Executive** dashboard: *Enrolled vs Capacity* should match your roll,
and *Occupancy* should look right. Use the **site filter** to sanity-check each branch.

## Common pitfalls

- **Foreign keys**: load `sites` before `rooms`/`children`; a `child.site_id` with no
  matching site will be rejected. Keep IDs consistent across files.
- **Enum values**: use the exact allowed strings above (e.g. `funded_30`, not “30 hours”).
- **Empty cells**: leave blank for NULL — don’t write the word “null”.
- **Re-running**: Method A appends; use `--truncate` (or upsert in Method C) to avoid
  duplicates.

Everything here maps to the tables in [DATABASE.md](DATABASE.md) and surfaces in the
reports described in [REPORTS_GUIDE.md](REPORTS_GUIDE.md).
