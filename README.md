# Nursery Analytics Platform

> Stripe-level interactive analytics dashboards for UK day-nursery operators.
> **Scope: dashboards + analytics + RBAC only** — this is *not* a nursery management system.

A production-style enterprise BI platform covering the 15 decision dashboards a
London nursery chain needs (Executive, Occupancy, Finance, Staff, Compliance,
EYFS, Attendance, Parent Comms, Nutrition, Multi-Site, BI, Alerts, Operations,
Mobile, AI), all driven by a configurable, role-based widget system.

---

## Tech stack

| Layer      | Tech |
|------------|------|
| Backend    | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Analytics  | pandas + numpy (KPI engine) |
| Database   | PostgreSQL 16 + a numbered SQL migration runner |
| Frontend   | React 18, Vite, Tailwind CSS, **Apache ECharts** (all charts) |
| Infra      | Docker Compose |

## Quick start (Docker)

```bash
cp .env.example .env          # adjust secrets if you like
docker compose up --build
```

Then open:

- **Frontend** → http://localhost:5173
- **API docs** → http://localhost:8000/docs
- **Health**   → http://localhost:8000/health

On first boot the backend automatically:
1. waits for Postgres,
2. runs SQL migrations (`backend/app/migrations/sql/*.sql`),
3. seeds realistic demo data (3 London sites, rooms, ~150 children, staff, and
   12 months of facts) + the demo users below.

## Demo accounts

| Role        | Email                      | Password      | Sees |
|-------------|----------------------------|---------------|------|
| Admin       | admin@lait.org.uk          | `Admin123!`   | Everything + **Dashboard Settings** |
| Management  | management@lait.org.uk     | `Manager123!` | All analytics dashboards |
| Accounts    | accounts@lait.org.uk       | `Accounts123!`| Finance, Occupancy, BI, Alerts, Executive |
| Teacher     | teacher@lait.org.uk        | `Teacher123!` | Attendance, EYFS, Nutrition, Parent Comms, Operations (their site) |
| Parent      | parent@lait.org.uk         | `Parent123!`  | Mobile + their own child only |

## RBAC & configurable dashboards

- **Roles → permissions** (`view.<module>`, `admin.*`) gate which modules a role can open.
- **`role_widget_access`** stores which *widgets* each role sees. Every role gets
  sensible defaults at seed time; an **admin** can add/remove any widget per role
  from the **Dashboard Settings** screen (`/admin`), or via
  `POST /api/v1/admin/dashboard-config/toggle`.
- Row-level scoping: management/accounts/admin see all sites; teachers are scoped
  to their site; parents to their linked child.

## Key API endpoints

```
POST /api/v1/auth/login-json          {email, password} -> tokens
GET  /api/v1/auth/me                   current user
GET  /api/v1/dashboards/me             modules + widgets the user may see
GET  /api/v1/dashboards/{key}/data     computed analytics payload for a module
GET  /api/v1/admin/roles
GET  /api/v1/admin/dashboard-config?role_id=
POST /api/v1/admin/dashboard-config/toggle
GET/POST /api/v1/admin/users
```

## Project layout

```
backend/
  app/
    api/v1/        auth, dashboards, admin routers
    analytics/     pandas/numpy KPI engine, one module per dashboard
    core/          config, async db, security (JWT), RBAC deps
    models/        SQLAlchemy 2.0 models (auth, dimensions, facts)
    migrations/    SQL files + idempotent runner
    seed/          realistic demo-data generator
    cli.py         `python -m app.cli migrate|seed`
frontend/
  src/
    charts/        ECharts option builders (line/bar/pie/gauge/heatmap/funnel)
    components/    Layout, EChart wrapper, WidgetRenderer, Icon
    context/       Auth + Theme (dark mode)
    pages/         Login, Dashboard, AdminConfig
```

## Data model (star-schema style)

- **Dimensions**: `dim_site`, `dim_room`, `dim_child`, `dim_parent`, `dim_staff`, `dim_date`
- **Facts**: `fact_attendance`, `fact_enrollment_event`, `fact_invoice`,
  `fact_payment`, `fact_staff_shift`, `fact_incident`, `fact_eyfs_observation`,
  `fact_meal`, `fact_message`
- **RBAC/config**: `roles`, `permissions`, `role_permissions`, `users`,
  `dashboard_modules`, `dashboard_widgets`, `role_widget_access`

## Local (without Docker)

Backend:
```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
# point POSTGRES_HOST at your local Postgres in .env
python -m app.cli migrate && python -m app.cli seed
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Adding a new widget / dashboard

1. Insert a row in `dashboard_widgets` (and a module if new) in a new migration.
2. Return its `key` from the relevant function in `backend/app/analytics/`.
3. Grant it to roles (seed default or via the admin screen).
The frontend renders it automatically from its `viz_type`.
