# How to Run the Nursery Analytics Platform

This guide gets you running on **Windows, macOS, or Linux**. The Docker path below is
identical on every operating system — if you can install Docker, you can run this.

| | Development | Production |
|---|---|---|
| For | building / trying it out | a real, public server |
| Frontend | live dev server (auto-refresh) | compiled & served by nginx |
| Backend | 1 process, auto-reload | 4 workers |
| Demo data | seeded automatically | **none** (you load real data) |
| Command file | `docker-compose.yml` | `docker-compose.prod.yml` |
| You open | http://localhost:5173 | http://your-server |

---

## ⭐ The easy path (Docker) — works on any OS

### Step 1 — Install Docker (one time)

| OS | Install |
|---|---|
| **Windows** | Install **Docker Desktop** → https://www.docker.com/products/docker-desktop/ (enable WSL 2 when asked) |
| **macOS** | Install **Docker Desktop** (Apple-Silicon or Intel build) from the same link |
| **Linux (server)** | `curl -fsSL https://get.docker.com \| sh` then `sudo usermod -aG docker $USER` and log out/in |

Check it works — this should print versions:
```bash
docker --version
docker compose version
```
> Older Docker? Use `docker-compose` (with a hyphen) everywhere this guide says `docker compose`.

### Step 2 — Create your settings file

From the project folder, copy the example settings to `.env`:

| Shell | Command |
|---|---|
| macOS / Linux / Git-Bash / PowerShell | `cp .env.example .env` |
| Windows Command Prompt (cmd) | `copy .env.example .env` |

You can leave the defaults as-is for development.

### Step 3 — Start everything

```bash
docker compose up --build
```
First run takes a few minutes (it downloads images and installs packages). Wait until
you see **`Application startup complete`**, then open:

- **App** → http://localhost:5173
- **API docs** → http://localhost:8000/docs
- **Health check** → http://localhost:8000/health

On first run it automatically creates the database tables and fills them with realistic
demo data, including these logins:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@lait.org.uk` | `Admin123!` |
| Management | `management@lait.org.uk` | `Manager123!` |
| Accounts | `accounts@lait.org.uk` | `Accounts123!` |
| Teacher | `teacher@lait.org.uk` | `Teacher123!` |
| Parent | `parent@lait.org.uk` | `Parent123!` |

### Everyday commands

```bash
docker compose up -d            # start in the background
docker compose logs -f backend  # watch the backend logs
docker compose stop             # stop (keeps your data)
docker compose down             # stop & remove containers (keeps your data)
docker compose down -v          # stop & ERASE the database (fresh demo data next start)
```

That's the whole thing. Most people never need anything below this line.

---

## Connecting pgAdmin / DBeaver to the database

The database runs in Docker and is published on **port 5498** on your machine
(deliberately *not* 5432, so it won't clash with any Postgres you already have).

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5498` |
| Database | `nursery_analytics` |
| Username | the `POSTGRES_USER` in your `.env` (default `nursery`) |
| Password | the `POSTGRES_PASSWORD` in your `.env` (default `nursery_dev_pw`) |

Want a different port? Set `POSTGRES_HOST_PORT=5499` in `.env` and restart.

---

## Running without Docker (optional, for backend developers)

You only need this if you want to run the Python/Node code directly. Otherwise use Docker above.

> ⚠️ **Use Python 3.12 — not 3.13 or 3.14.** The pinned `numpy` / `pandas` / `asyncpg`
> don't yet ship prebuilt packages for 3.13+, so `pip install` tries to compile them and
> appears to **hang at `Preparing metadata (pyproject.toml)`**. Get Python 3.12 from
> https://www.python.org/downloads/ and create the virtual environment with it.

You still need a database. The simplest is to run **only Postgres in Docker**:
```bash
docker compose up -d db          # Postgres on localhost:5498
```

**Backend** (in a terminal):
```bash
cd backend

# create the virtual environment with Python 3.12 specifically:
py -3.12 -m venv .venv                 # Windows
# python3.12 -m venv .venv             # macOS / Linux

# activate it:
.venv\Scripts\activate                 # Windows PowerShell / cmd
# source .venv/bin/activate            # macOS / Linux / Git-Bash

pip install -r requirements.txt

# tell the backend where the database is (this terminal only):
#   Windows PowerShell:
$env:POSTGRES_HOST="localhost"; $env:POSTGRES_PORT="5498"
#   Windows cmd:           set POSTGRES_HOST=localhost && set POSTGRES_PORT=5498
#   macOS / Linux:         export POSTGRES_HOST=localhost POSTGRES_PORT=5498

python -m app.cli migrate              # create tables + roles/dashboards
python -m app.cli seed                 # demo data + demo users
uvicorn app.main:app --reload          # → http://localhost:8000
```

**Frontend** (a second terminal):
```bash
cd frontend
npm install
npm run dev                            # → http://localhost:5173
```

---

## 🚀 Production deployment (any server: Linux, macOS or Windows)

Same Docker idea, but with compiled assets, no demo data, and the database hidden from
the internet. A small Linux VM (1–2 vCPU, 2 GB RAM) is plenty.

### 1. Install Docker
Same as Step 1 above (on a Linux server: `curl -fsSL https://get.docker.com | sh`).

### 2. Get the code and set real secrets
```bash
git clone <your-repo> nursery
cd nursery
cp .env.prod.example .env.prod          # (Windows cmd: copy .env.prod.example .env.prod)
```
Open `.env.prod` and change **every** secret:
- `POSTGRES_PASSWORD` → a strong password
- `SECRET_KEY` → run `openssl rand -hex 32` and paste the result
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` → your first admin login

### 3. Build and start
```bash
docker compose -p nursery_prod -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
> Always include `-p nursery_prod`. It keeps the production stack separate from any dev
> stack on the same machine (otherwise they share names and overwrite each other).

This serves the app on **port 80**, runs migrations once, starts 4 backend workers, and
keeps the database internal (not reachable from outside).

### 4. Create your first admin (no demo data)
```bash
docker compose -p nursery_prod -f docker-compose.prod.yml --env-file .env.prod \
  exec backend python -m app.cli bootstrap-admin
```
Open `http://your-server-ip/`, sign in with the admin from `.env.prod`, then add other
users in **User Management**. Load your real data via [docs/DATA_INTEGRATION.md](docs/DATA_INTEGRATION.md).

> Prefer to start with demo data instead? Run `... exec backend python -m app.cli seed`.

### 5. Add HTTPS + your domain (recommended)
Point a TLS reverse proxy at port 80. The easiest is **Caddy** (auto free certificates):
```
# /etc/caddy/Caddyfile
yourdomain.com {
    reverse_proxy localhost:80
}
```
(Nginx + certbot, or a cloud load balancer, work too.)

### Production day-to-day
```bash
# tip: save this once so you don't retype it
P="docker compose -p nursery_prod -f docker-compose.prod.yml --env-file .env.prod"

$P ps                                   # status
$P logs -f backend                      # logs
git pull && $P up -d --build            # deploy new code
$P exec backend python -m app.cli migrate   # apply new DB changes
$P down                                  # stop (data is kept)
```

### Backups
```bash
# save a backup
docker exec nursery_db_prod pg_dump -U nursery nursery_analytics > backup_$(date +%F).sql
# restore one
cat backup.sql | docker exec -i nursery_db_prod psql -U nursery nursery_analytics
```
(Use the `POSTGRES_USER` from your `.env.prod` if you changed it from `nursery`.)

---

## Updating the database structure

The schema is a set of numbered SQL files in `backend/app/migrations/sql/`
(`001_…`, `002_…`, `003_…`). To change it, add the next file
(e.g. `004_add_something.sql`) using `ALTER TABLE … ADD COLUMN IF NOT EXISTS …`, then
restart (dev) or run `python -m app.cli migrate` (prod). Applied files are recorded and
never run twice. **Never edit a file that has already run — always add a new one.**

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `docker compose` "command not found" | Docker isn't installed / not started, or you have old Docker — try `docker-compose` (hyphen). |
| `.env file not found` on `up` | You skipped Step 2 — run `cp .env.example .env` (cmd: `copy …`). |
| `pip install` hangs at `Preparing metadata (pyproject.toml)` | You're on Python 3.13/3.14. Use **Python 3.12**. (Or just use Docker.) |
| pgAdmin can't connect, or "port 5432 in use" | The Docker database is on **localhost:5498**, not 5432. |
| `password authentication failed` after changing DB user/password in `.env` | Postgres only applies those on first creation. Run `docker compose down -v && docker compose up -d` to re-initialise. |
| `port is already allocated` | Something else uses 5173 / 8000 / 80. Stop it, or change the published port in the compose file. |
| `502 Bad Gateway` right after starting production | Backend workers are still booting — wait ~10 seconds and refresh. |
| Can't log in on production | You haven't created the admin yet — run the `bootstrap-admin` step. |
| Dev containers got "replaced" by production | Always use `-p nursery_prod` for the production commands. |
| `error reading bcrypt version` in logs | Harmless message from a library; logins still work. |
