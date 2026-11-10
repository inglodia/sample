#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_VENV="${ROOT}/backend/.venv"
PIDS=()

cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

ensure_backend_venv() {
  if [[ ! -d "${BACKEND_VENV}" ]]; then
    echo "Creating backend/.venv …"
    python3 -m venv "${BACKEND_VENV}"
    "${BACKEND_VENV}/bin/pip" install -q -r "${ROOT}/backend/requirements.txt"
  fi
}

docker network inspect sample1-net >/dev/null 2>&1 || docker network create sample1-net
docker compose up -d
"${ROOT}/scripts/wait-for-postgres.sh"

ensure_backend_venv

cd "${ROOT}/backend"
"${BACKEND_VENV}/bin/alembic" upgrade head
"${BACKEND_VENV}/bin/python" -m app.seed
cd "${ROOT}"

(
  cd "${ROOT}/backend"
  exec "${BACKEND_VENV}/bin/uvicorn" app.main:app --reload --port 8000
) &
PIDS+=($!)

(
  cd "${ROOT}/frontend"
  exec npm run dev
) &
PIDS+=($!)

echo "API: http://127.0.0.1:8000/docs"
echo "UI:  http://localhost:5173"
echo "Admin: admin@example.com / Test@1234"
echo "Press Ctrl+C to stop backend and frontend."

wait
