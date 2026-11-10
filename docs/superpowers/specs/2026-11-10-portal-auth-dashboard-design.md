# Portal Auth + Dashboard Design

**Date:** 2026-11-10  
**Status:** Approved (Approach 1)  
**Project:** sample1 monorepo — Vite React frontend + FastAPI backend + Postgres

## Goal

Build an end-to-end portal with registration, session-based login, an admin-seeded account, a dashboard with real user stats, and an admin-only users table with role promotion. UI matches the shadcn dashboard look with the Catppuccin tweakcn theme.

## Decisions Locked

| Topic | Choice |
|-------|--------|
| Layout | Monorepo: `frontend/`, `backend/`, root `docker-compose.yml`, `Makefile` |
| Frontend | Vite + React + TypeScript + Tailwind + shadcn + Catppuccin theme |
| Backend | FastAPI + SQLAlchemy 2 + Alembic + Postgres |
| Infra | Postgres only in Docker; apps run on host via `make dev` |
| Admin seed | Email `admin@example.com`, password `Test@1234`, role `admin` |
| Registration | New users always get role `user` |
| Role changes | Admins can promote/demote from Users table |
| Dashboard | Real stats from `users` table (not placeholder-only) |
| Sessions | Signed secure httpOnly cookie only (no session table / no Redis) |
| Users visibility | Users list + role updates: `admin` role only |

## Architecture

```
Browser (Vite :5173)
  │  credentials: include; session cookie
  ▼
Vite /api proxy ──► FastAPI (:8000)
                      │
                      ▼
               Postgres (:5432)
               Docker network: sample1-net
```

- Session: Starlette `SessionMiddleware` with a signed cookie (`SESSION_SECRET`).
- Cookie flags: `httponly=True`, `samesite=lax`, `secure=False` in local dev.
- CORS: allow `http://localhost:5173` with `allow_credentials=True`.
- Auth check: middleware/deps read `request.session["user_id"]`, load user from DB.

## Data Model

### Table: `users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | `gen_random_uuid()` / Python uuid4 |
| `email` | VARCHAR(255) UNIQUE NOT NULL | lowercased on write |
| `password_hash` | VARCHAR(255) NOT NULL | bcrypt |
| `full_name` | VARCHAR(255) NULL | optional display name |
| `role` | VARCHAR(32) NOT NULL | `admin` \| `user`; default `user` |
| `created_at` | TIMESTAMPTZ NOT NULL | server default now() |
| `updated_at` | TIMESTAMPTZ NOT NULL | on update |

Seed (Alembic migration or startup seed script, idempotent):

- `admin@example.com` / `Test@1234` / role `admin`

No separate sessions table (decision B).

## API

Base path: `/api`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | public | Create user (role forced `user`) |
| POST | `/api/auth/login` | public | Verify credentials; set session |
| POST | `/api/auth/logout` | session | Clear session |
| GET | `/api/auth/me` | session | Current user profile |
| GET | `/api/dashboard/stats` | session | Aggregates from `users` |
| GET | `/api/users` | admin | List users |
| PATCH | `/api/users/{id}/role` | admin | Set role `admin` \| `user` |

### Request/response shapes

**Register** `{ "email", "password", "full_name?" }` → `{ "id", "email", "full_name", "role" }`  
**Login** `{ "email", "password" }` → same user object + Set-Cookie  
**Me / user** `{ "id", "email", "full_name", "role", "created_at" }`  
**Dashboard stats** `{ "total_users", "new_users_30d", "admin_count", "user_count", "signups_by_day": [{ "date", "count" }] }`  
**Users list** `{ "items": [user...] }`  
**Patch role** `{ "role": "admin"|"user" }` → updated user  

Errors: `401` unauthenticated, `403` non-admin, `409` email taken, `422` validation.

## Frontend UI

Theme: `npx shadcn@latest add https://tweakcn.com/r/themes/catppuccin.json` after shadcn init.

### Routes

| Path | Access | UI |
|------|--------|----|
| `/login` | public | Email + password form |
| `/register` | public | Email + password + optional name |
| `/` or `/dashboard` | authenticated | Sidebar layout + metric cards + chart from `/api/dashboard/stats` |
| `/users` | admin only | Users table; role select/promote; non-admins redirected to dashboard |

### Shell (matches screenshot intent)

- Left sidebar: brand, nav (Dashboard; Users if admin), Settings stub optional
- Top/header area as needed
- Profile menu (avatar): show email; **Logout** action
- Metric cards driven by real stats (map labels to user aggregates; e.g. Total Users, New Users 30d, Admins, Users)
- Area chart from `signups_by_day` (last 30 days)
- Users page: table with email, name, role, created_at, role changer for admins

### Auth UX

- Unauthenticated visitors hitting protected routes → `/login`
- After login/register → `/dashboard`
- Logout clears session via API then → `/login`

## Makefile / Dev

`make dev`:

1. Ensure Docker network `sample1-net` exists
2. `docker compose up -d` Postgres (attached to that network)
3. Wait until Postgres accepts connections
4. Backend: create venv if needed, install deps, `alembic upgrade head`, seed admin
5. Run backend (uvicorn) and frontend (`npm run dev`) concurrently in console (e.g. scripts or `make` with two processes)

Also useful targets: `make down`, `make migrate`, `make seed`, `make backend`, `make frontend`.

Env files:

- `backend/.env`: `DATABASE_URL`, `SESSION_SECRET`, `CORS_ORIGINS`
- `frontend/.env`: `VITE_API_BASE=/api` (proxy preferred)

## Out of Scope (v1)

- Redis / server-side session store
- Email verification, password reset
- True multi-service split (auth-api vs users-api)
- Production HTTPS / K8s deploy
- Real revenue/visitor analytics beyond user aggregates

## Success Criteria

1. `make dev` brings up Postgres + both apps
2. Login as `admin@example.com` / `Test@1234` lands on dashboard
3. Register creates `user` role; Users page hidden/forbidden for them
4. Admin sees Users table and can change roles
5. Profile menu Logout ends session
6. UI uses Catppuccin shadcn theme and dashboard-style layout
