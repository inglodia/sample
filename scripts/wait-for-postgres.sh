#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ROOT_DIR}/.env"
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-portal}"
POSTGRES_DB="${POSTGRES_DB:-portal}"

for i in {1..60}; do
  if docker exec sample1-postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    echo "Postgres ready"
    exit 0
  fi
  sleep 1
done
echo "Postgres not ready" >&2
exit 1
