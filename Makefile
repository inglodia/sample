.PHONY: up down wait dev migrate seed backend frontend

up:
	docker compose up -d

down:
	docker compose down

wait:
	./scripts/wait-for-postgres.sh

dev:
	@echo "Stub: full dev workflow lands in a later task."

migrate:
	@echo "Stub: run Alembic migrations (backend task)."

seed:
	@echo "Stub: seed admin user (backend task)."

backend:
	@echo "Stub: uvicorn backend (backend task)."

frontend:
	@echo "Stub: Vite dev server (frontend task)."
