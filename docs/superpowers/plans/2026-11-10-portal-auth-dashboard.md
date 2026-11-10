# Portal Auth + Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Vite React + FastAPI portal with session auth, seeded admin, dashboard stats from users, and an admin-only users table with role promotion, runnable via `make dev`.

**Architecture:** Monorepo with Postgres in Docker (`sample1-net`); FastAPI + Alembic on the host; Vite SPA proxies `/api` to `:8000`; signed httpOnly session cookie (no session table).

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, passlib/bcrypt, psycopg; Vite, React, TypeScript, Tailwind, shadcn/ui, Catppuccin via tweakcn; Docker Compose; Makefile.

**Spec:** `docs/superpowers/specs/2026-11-10-portal-auth-dashboard-design.md`

## Global Constraints

- Admin seed: email `admin@example.com`, password `Test@1234`, role `admin`
- New registrations always role `user`
- Users list + role PATCH: `admin` only
- Session: signed cookie only (SessionMiddleware); no Redis / sessions table
- Theme: `npx shadcn@latest add https://tweakcn.com/r/themes/catppuccin.json`
- Docker network name: `sample1-net`
- API under `/api`; Vite proxies `/api` → `http://127.0.0.1:8000`

---

## File Map

```
sample1/
  Makefile
  docker-compose.yml
  .gitignore
  README.md
  backend/
    pyproject.toml or requirements.txt
    .env.example
    alembic.ini
    alembic/
      env.py
      versions/0001_create_users.py
    app/
      __init__.py
      main.py
      config.py
      db.py
      models/user.py
      schemas/auth.py
      schemas/user.py
      schemas/dashboard.py
      deps.py
      routers/auth.py
      routers/users.py
      routers/dashboard.py
      seed.py
    tests/
      conftest.py
      test_auth.py
      test_users.py
      test_dashboard.py
  frontend/
    package.json
    vite.config.ts
    tsconfig.json
    index.html
    src/
      main.tsx
      App.tsx
      index.css
      lib/api.ts
      lib/auth.tsx
      components/... (shadcn)
      pages/LoginPage.tsx
      pages/RegisterPage.tsx
      pages/DashboardPage.tsx
      pages/UsersPage.tsx
      components/layout/AppShell.tsx
      components/layout/UserMenu.tsx
  scripts/
    wait-for-postgres.sh
    dev.sh
```

---

### Task 1: Repo root + Postgres Compose

**Files:**
- Create: `.gitignore`, `docker-compose.yml`, `scripts/wait-for-postgres.sh`, `Makefile` (stubs), `README.md`
- Test: manual `docker compose` health

**Interfaces:**
- Produces: Postgres at `localhost:5432`, user/db/password `portal`/`portal`/`portal`, network `sample1-net`, DB name `portal`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
node_modules/
dist/
.env
backend/.env
frontend/.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: sample1-postgres
    environment:
      POSTGRES_USER: portal
      POSTGRES_PASSWORD: portal
      POSTGRES_DB: portal
    ports:
      - "5432:5432"
    volumes:
      - sample1_pgdata:/var/lib/postgresql/data
    networks:
      - sample1-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U portal -d portal"]
      interval: 2s
      timeout: 5s
      retries: 15

networks:
  sample1-net:
    name: sample1-net

volumes:
  sample1_pgdata:
```

- [ ] **Step 3: Create `scripts/wait-for-postgres.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
for i in {1..60}; do
  if docker exec sample1-postgres pg_isready -U portal -d portal >/dev/null 2>&1; then
    echo "Postgres ready"
    exit 0
  fi
  sleep 1
done
echo "Postgres not ready" >&2
exit 1
```

- [ ] **Step 4: Verify Postgres**

Run:
```bash
chmod +x scripts/wait-for-postgres.sh
docker compose up -d
./scripts/wait-for-postgres.sh
```
Expected: `Postgres ready`

- [ ] **Step 5: Commit**

```bash
git add .gitignore docker-compose.yml scripts/wait-for-postgres.sh
git commit -m "Add Postgres compose and wait script."
```

---

### Task 2: Backend skeleton + User model + Alembic

**Files:**
- Create: `backend/requirements.txt`, `backend/.env.example`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/models/user.py`, `backend/app/main.py`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_create_users.py`
- Test: `backend/tests/test_health.py` (optional) + alembic upgrade

**Interfaces:**
- Produces: `User` model with fields `id, email, password_hash, full_name, role, created_at, updated_at`
- Produces: `get_db()` dependency; `settings.database_url`, `settings.session_secret`

- [ ] **Step 1: Create `backend/requirements.txt`**

```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.0
psycopg[binary]>=3.2.0
alembic>=1.13.0
pydantic-settings>=2.0.0
passlib[bcrypt]>=1.7.4
bcrypt<4.1.0
email-validator>=2.0.0
httpx>=0.27.0
pytest>=8.0.0
```

- [ ] **Step 2: Create config + db + User model**

`backend/app/config.py`: load `DATABASE_URL` default `postgresql+psycopg://portal:portal@127.0.0.1:5432/portal`, `SESSION_SECRET` default `dev-secret-change-me`, `CORS_ORIGINS` default `http://localhost:5173`.

`backend/app/models/user.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 3: Alembic init + migration `0001_create_users`**

Create table matching the model. `alembic/env.py` must import `Base` and `User` and use `settings.database_url`.

- [ ] **Step 4: Run migration**

Run:
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
```
Expected: `users` table exists

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "Add FastAPI skeleton, User model, and Alembic migration."
```

---

### Task 3: Auth routes + seed admin + session cookie

**Files:**
- Create: `backend/app/schemas/auth.py`, `backend/app/deps.py`, `backend/app/routers/auth.py`, `backend/app/seed.py`
- Modify: `backend/app/main.py` — SessionMiddleware, CORS, include router
- Test: `backend/tests/conftest.py`, `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `User`, `get_db`, settings
- Produces:
  - `POST /api/auth/register` → UserOut
  - `POST /api/auth/login` → UserOut + session
  - `POST /api/auth/logout` → `{ "ok": true }`
  - `GET /api/auth/me` → UserOut
  - `seed_admin()` idempotent
  - `get_current_user`, `require_admin` deps

- [ ] **Step 1: Write failing auth tests**

```python
def test_register_login_me_logout(client):
    r = client.post("/api/auth/register", json={"email": "a@example.com", "password": "Test@1234", "full_name": "A"})
    assert r.status_code == 201
    assert r.json()["role"] == "user"
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "Test@1234"})
    assert r.status_code == 200
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    r = client.get("/api/auth/me")
    assert r.status_code == 401
```

Use TestClient with cookie jar; use a test DB or the docker Postgres with transaction rollback.

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_auth.py -v`  
Expected: FAIL (routes missing)

- [ ] **Step 3: Implement hashing, deps, auth router, SessionMiddleware**

- Hash with `passlib.context.CryptContext(schemes=["bcrypt"])`
- On login: `request.session["user_id"] = str(user.id)`
- On logout: `request.session.clear()`
- Register forces `role="user"`
- Seed: if no user with `admin@example.com`, create with password `Test@1234`, role `admin`

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_auth.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "Add session auth, register/login, and admin seed."
```

---

### Task 4: Users admin API + dashboard stats API

**Files:**
- Create: `backend/app/schemas/user.py`, `backend/app/schemas/dashboard.py`, `backend/app/routers/users.py`, `backend/app/routers/dashboard.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_users.py`, `backend/tests/test_dashboard.py`

**Interfaces:**
- Produces:
  - `GET /api/users` → `{ "items": UserOut[] }` (admin)
  - `PATCH /api/users/{id}/role` body `{ "role" }` → UserOut (admin)
  - `GET /api/dashboard/stats` → `{ total_users, new_users_30d, admin_count, user_count, signups_by_day: [{date, count}] }`

- [ ] **Step 1: Write failing tests**

```python
def test_users_admin_only(client, admin_client, user_client):
    assert user_client.get("/api/users").status_code == 403
    assert admin_client.get("/api/users").status_code == 200

def test_promote_user(admin_client, registered_user_id):
    r = admin_client.patch(f"/api/users/{registered_user_id}/role", json={"role": "admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"

def test_dashboard_stats(admin_client):
    r = admin_client.get("/api/dashboard/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_users" in body and "signups_by_day" in body
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/test_users.py tests/test_dashboard.py -v`

- [ ] **Step 3: Implement routers**

- `require_admin` raises 403 if `user.role != "admin"`
- Stats: COUNT users; COUNT where `created_at >= now()-30d`; COUNT by role; daily counts for last 30 days via SQL `date_trunc('day', created_at)`

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_users.py tests/test_dashboard.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "Add admin users API and dashboard stats."
```

---

### Task 5: Frontend scaffold + Catppuccin shadcn theme

**Files:**
- Create: Vite React-TS app under `frontend/`
- Modify: `frontend/vite.config.ts` proxy; theme CSS variables
- Test: `npm run dev` loads

**Interfaces:**
- Produces: working Vite app on `:5173` with `/api` → `http://127.0.0.1:8000`
- Produces: shadcn components + Catppuccin theme applied

- [ ] **Step 1: Scaffold**

```bash
cd /Users/ravitejamanepalli/projects/sample1
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

- [ ] **Step 2: Init shadcn + Catppuccin**

```bash
npx shadcn@latest init -y
npx shadcn@latest add https://tweakcn.com/r/themes/catppuccin.json
npx shadcn@latest add button card input label table dropdown-menu avatar separator sheet sidebar chart
```

(If sidebar/chart names differ in current shadcn, add the closest available components used by the dashboard layout.)

- [ ] **Step 3: Vite proxy**

```ts
server: {
  port: 5173,
  proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
},
```

- [ ] **Step 4: Verify blank themed app**

Run: `npm run dev` — page loads with Catppuccin colors

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "Scaffold Vite React app with shadcn Catppuccin theme."
```

---

### Task 6: Frontend auth + shell + pages

**Files:**
- Create: `frontend/src/lib/api.ts`, `frontend/src/lib/auth.tsx`, pages + `AppShell`, `UserMenu`, routes in `App.tsx`
- Test: manual login flow

**Interfaces:**
- Consumes: auth/users/dashboard APIs with `credentials: "include"`
- Produces: `/login`, `/register`, `/dashboard`, `/users` (admin); logout in profile menu

- [ ] **Step 1: API helper**

```ts
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw Object.assign(new Error(await res.text()), { status: res.status });
  return res.json();
}
```

- [ ] **Step 2: AuthProvider** — call `/api/auth/me` on load; expose `user`, `login`, `register`, `logout`, `isAdmin`

- [ ] **Step 3: Pages**

- Login/Register forms → redirect `/dashboard`
- Dashboard: 4 metric cards from stats + area chart for `signups_by_day`
- Users: table; role `<Select>` calling PATCH; route guard if `!isAdmin` → dashboard
- `UserMenu`: avatar + email + Logout

- [ ] **Step 4: Manual E2E check**

1. Register `user@example.com` / `Test@1234` → dashboard; no Users nav  
2. Login admin → see Users; promote user  
3. Logout → `/login`; `/dashboard` redirects to login  

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "Add auth pages, dashboard stats UI, and admin users table."
```

---

### Task 7: Makefile `make dev` + scripts polish

**Files:**
- Create: `scripts/dev.sh`
- Modify: `Makefile`, `README.md`

**Interfaces:**
- Produces: `make dev` starts network/postgres, migrates, seeds, runs backend+frontend

- [ ] **Step 1: `scripts/dev.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
docker network inspect sample1-net >/dev/null 2>&1 || docker network create sample1-net
docker compose up -d
"$ROOT/scripts/wait-for-postgres.sh"
cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
alembic upgrade head
python -m app.seed
cd "$ROOT"
# run both (use concurrently if installed, else background + trap)
(cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev) &
wait
```

- [ ] **Step 2: Makefile**

```makefile
.PHONY: dev down migrate seed backend frontend

dev:
	./scripts/dev.sh

down:
	docker compose down

migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

seed:
	cd backend && . .venv/bin/activate && python -m app.seed

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev
```

- [ ] **Step 3: README** — setup (venv, npm i), `make dev`, default admin credentials

- [ ] **Step 4: Run `make dev` smoke**

Expected: Postgres up; API docs at `http://127.0.0.1:8000/docs`; UI at `http://localhost:5173`; admin login works

- [ ] **Step 5: Commit**

```bash
git add Makefile scripts README.md
git commit -m "Wire make dev for Postgres, API, and Vite frontend."
```

---

## Spec Coverage Check

| Spec requirement | Task |
|------------------|------|
| Vite + FastAPI monorepo | 1, 2, 5 |
| Postgres Docker + sample1-net | 1, 7 |
| Alembic users migration | 2 |
| Session cookie auth | 3 |
| Register → user role | 3 |
| Admin seed admin@example.com / Test@1234 | 3 |
| Dashboard real user stats | 4, 6 |
| Users table admin-only + promote | 4, 6 |
| Logout under profile | 6 |
| Catppuccin tweakcn theme | 5 |
| `make dev` | 7 |
| Screenshot-like dashboard shell | 6 |

## Self-Review Notes

- No TBD placeholders left in tasks
- Role values consistently `admin` | `user`
- API paths all under `/api`
- Cookie session approach matches decision B (no sessions table)
