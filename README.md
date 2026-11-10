# Portal (auth + dashboard)

Vite/React frontend and FastAPI backend monorepo with Postgres via Docker Compose.

## Local setup

1. Copy environment files (keep ports in sync — see note below):

   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

2. Backend Python venv and dependencies:

   ```bash
   python3 -m venv backend/.venv
   source backend/.venv/bin/activate
   pip install -r backend/requirements.txt
   ```

   `make dev` creates `backend/.venv` automatically if it is missing.

3. Frontend dependencies:

   ```bash
   cd frontend && npm install
   ```

4. Start the full stack:

   ```bash
   make dev
   ```

   - API docs: http://127.0.0.1:8000/docs  
   - UI: http://localhost:5173  
   - Default admin (after seed): **admin@example.com** / **Test@1234**

### Postgres port vs `DATABASE_URL`

Root `.env` sets `POSTGRES_PORT` for Docker Compose (host port mapped to the container). `backend/.env` `DATABASE_URL` must use the **same host port**, e.g. if `POSTGRES_PORT=5434` in the repo `.env`, set:

`DATABASE_URL=postgresql+psycopg://portal:portal@127.0.0.1:5434/portal`

Compose reads the root `.env`; the API reads `backend/.env`.

## Makefile

| Target        | Description                                      |
|---------------|--------------------------------------------------|
| `make dev`    | Network, Postgres, migrate, seed, API + Vite     |
| `make up`     | `docker compose up -d` (Postgres only)           |
| `make down`   | `docker compose down`                            |
| `make wait`   | Block until Postgres is ready                    |
| `make migrate`| Alembic `upgrade head`                           |
| `make seed`   | Insert default admin if missing                  |
| `make backend`| Uvicorn on port 8000 (venv required)             |
| `make frontend` | Vite dev server                                |

Network: `sample1-net`. Container: `sample1-postgres`.
