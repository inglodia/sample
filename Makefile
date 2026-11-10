.PHONY: up down wait dev migrate seed backend frontend

up:
	docker compose up -d

down:
	docker compose down

wait:
	./scripts/wait-for-postgres.sh

dev:
	./scripts/dev.sh

migrate:
	cd backend && .venv/bin/alembic upgrade head

seed:
	cd backend && .venv/bin/python -m app.seed

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev
