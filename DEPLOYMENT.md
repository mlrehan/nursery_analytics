# Running the Nursery Analytics Platform

Two ways to run it:

| | Development | Production |
|---|---|---|
| Goal | code & iterate fast | stable, public-facing |
| Frontend | Vite dev server (hot reload) | compiled static files served by nginx |
| Backend | 1 process, auto-reload | 4 workers, no reload |
| Migrations / seed | run automatically + demo data | run once, **no demo data** |
| Compose file | `docker-compose.yml` | `docker-compose.prod.yml` |
| Open at | http://localhost:5173 | http://your-server (port 80) |

Prerequisites for the easy path: **Docker Desktop** (Windows/Mac) or **Docker Engine + Compose** (Ubuntu). Nothing else.

---

## A. Development

### Option 1 — Docker (recommended, one command)

```bash
cp .env.example .env          # first time only
docker compose up --build
```

Wait ~30s for `Application startup complete`, then open:
- App: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health

On first run it auto-creates the schema, seeds realistic demo data, and creates
the demo logins (admin@lait.org.uk / `Admin123!`, plus management/accounts/teacher/parent).

Everyday commands:
```bash
docker compose up -d           # start in background
docker compose logs -f backend # follow backend logs
docker compose down            # stop (keeps data)
docker compose down -v         # stop and WIPE the database
```

### Option 2 — Without Docker (local Python + Node)

You need **Python 3.12** (see warning below), **Node 20+**, and a **PostgreSQL** the
backend can reach.

> ⚠️ **Use Python 3.12 — not 3.13 or 3.14.** The pinned `numpy` / `pandas` /
> `asyncpg` versions don't yet publish prebuilt wheels for 3.13+, so `pip install`
> tries to **compile them from source** and appears to hang at
> `Preparing metadata (pyproject.toml)`. Install Python 3.12 from python.org, then
> create the venv with it explicitly.

You don't need a *separate* local Postgres — the easiest path is to run **only the
database in Docker** (it's published on host port **5498**) and run the backend
natively against it:

```bash
docker compose up -d db          # Postgres only, on localhost:5498
```

Backend:
```bash
cd backend
# create the venv with Python 3.12 specifically:
py -3.12 -m venv .venv           # Windows  (or: python3.12 -m venv .venv on macOS/Linux)
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt

# point the backend at the Docker DB on 5498:
set POSTGRES_HOST=localhost      # Windows (PowerShell: $env:POSTGRES_HOST="localhost")
set POSTGRES_PORT=5498
python -m app.cli migrate        # create tables + roles/modules/widgets
python -m app.cli seed           # demo data + demo users
uvicorn app.main:app --reload    # http://localhost:8000
```

Frontend (second terminal):
```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

### Connecting pgAdmin to the Docker database

The Docker Postgres is published on **localhost:5498** (chosen so it won't clash
with a local Postgres already using 5432). In pgAdmin → *Register → Server*:

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5498` |
| Maintenance DB | `nursery_analytics` |
| Username | `nursery` |
| Password | `nursery_dev_pw` (from `.env`) |

To change the host port, set `POSTGRES_HOST_PORT` in `.env` (e.g. `5499`).

---

## B. Production (Ubuntu server)

### 1. Install Docker (once)
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # then log out/in
```

### 2. Get the code & set secrets
```bash
git clone <your-repo> nursery && cd nursery
cp .env.prod.example .env.prod
```
Edit `.env.prod` and change **every** secret:
```bash
# generate a strong key:
openssl rand -hex 32           # paste into SECRET_KEY
```
Set `POSTGRES_PASSWORD`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

### 3. Build & start
```bash
docker compose -p nursery_prod -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
> `-p nursery_prod` gives the production stack its own project namespace so it
> never collides with a dev stack on the same machine.

This builds the React app, serves it via nginx on **port 80**, runs migrations
once, and starts the API with 4 workers. The database is **not** exposed to the host.

### 4. Create the first admin (no demo data)
```bash
docker compose -p nursery_prod -f docker-compose.prod.yml --env-file .env.prod \
  exec backend python -m app.cli bootstrap-admin
```
Now visit `http://your-server-ip/` and sign in as the admin from `.env.prod`.
Create all other users from the UI (admin → users API) — production starts with a
clean database (roles, the 15 dashboard modules, and widgets are created by
migrations; there are no demo children/staff).

> Want demo data in production too? Run `... exec backend python -m app.cli seed`
> instead of `bootstrap-admin` (creates demo sites/children/staff + the 5 demo users).

### 5. HTTPS / domain (recommended)
Put a TLS reverse proxy in front of port 80. Easiest is Caddy:
```bash
# /etc/caddy/Caddyfile
yourdomain.com {
    reverse_proxy localhost:80
}
```
Caddy auto-provisions a Let's Encrypt certificate. (Nginx + certbot or a cloud
load balancer work equally well.)

### Production operations
```bash
P="docker compose -p nursery_prod -f docker-compose.prod.yml --env-file .env.prod"
$P ps                    # status
$P logs -f backend       # logs
$P up -d --build         # deploy new code (after git pull)
$P exec backend python -m app.cli migrate   # apply new migrations
$P down                  # stop (keeps data in the pgdata_prod volume)
```

### Backups
```bash
# dump
docker exec nursery_db_prod pg_dump -U nursery nursery_analytics > backup_$(date +%F).sql
# restore
cat backup.sql | docker exec -i nursery_db_prod psql -U nursery nursery_analytics
```

---

## Updating / migrations

Schema is versioned by numbered SQL files in `backend/app/migrations/sql/`.
To change the schema: add `003_*.sql` (and update the matching ORM model), then
the runner applies it automatically on next start (dev) or via
`python -m app.cli migrate` (prod). Already-applied files are skipped.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install` hangs at `Preparing metadata (pyproject.toml)` | You're on Python 3.13/3.14. Use **Python 3.12** (`py -3.12 -m venv .venv`). Or just use Docker. |
| pgAdmin can't connect / port 5432 in use | The Docker DB is on **localhost:5498**, not 5432. |
| `password authentication failed` after editing DB creds in `.env` | Postgres only applies `POSTGRES_USER/PASSWORD` when it first creates its volume. After changing them run `docker compose down -v && docker compose up -d` to re-init. |
| `502 Bad Gateway` right after `up` | Backend workers still starting — wait ~10s and retry. |
| Login fails in production | You haven't run `bootstrap-admin` (or `seed`) yet. |
| `port is already allocated` | Another service uses 80/5173/8000 — stop it or change the published port in the compose file. |
| Dev "replaced" by prod containers | Use `-p nursery_prod` for the prod stack (separate namespace). |
| Want a clean slate (dev) | `docker compose down -v` then `up` re-seeds. |
| `error reading bcrypt version` in logs | Harmless passlib version probe; hashing works. |
