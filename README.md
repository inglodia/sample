# Portal (auth + dashboard)

Vite/React frontend and FastAPI backend monorepo. Task 1 provides Postgres via Docker Compose.

## Local setup

1. Copy environment defaults:

   ```bash
   cp .env.example .env
   ```

2. Start Postgres and wait for readiness:

   ```bash
   make up
   make wait
   ```

   Or: `docker compose up -d` then `./scripts/wait-for-postgres.sh`.

Postgres listens on `localhost:${POSTGRES_PORT:-5432}` with credentials from `.env` (defaults: user/db/password `portal`).

## Makefile (stubs)

| Target    | Status                          |
|-----------|---------------------------------|
| `make up` | Start Postgres                  |
| `make down` | Stop Compose services         |
| `make wait` | Block until Postgres is ready |
| `make dev` | Full stack — later task        |

Network: `sample1-net`.
