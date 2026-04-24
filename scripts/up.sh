#!/usr/bin/env bash
# =============================================================================
# WorkStation — up.sh
# Start the full stack in detached mode and print service status.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose/docker-compose.yml"

# ── Ensure .env exists ───────────────────────────────────────────────────────
if [[ ! -f "${REPO_ROOT}/.env" ]]; then
  if [[ -f "${REPO_ROOT}/.env.example" ]]; then
    cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
    echo "[info] Created .env from .env.example — edit it to override defaults."
  else
    echo "[error] .env not found and no .env.example to copy from." >&2
    exit 1
  fi
fi

set -a
# shellcheck disable=SC1091
source "${REPO_ROOT}/.env"
set +a

echo "=== WorkStation: starting stack ==="
echo "Compose file: ${COMPOSE_FILE}"
echo ""

docker compose \
  --file "${COMPOSE_FILE}" \
  --env-file "${REPO_ROOT}/.env" \
  up --detach --remove-orphans

echo ""
echo "=== Stack started. Current service status: ==="
docker compose \
  --file "${COMPOSE_FILE}" \
  ps

echo ""
echo "Tip: run ./scripts/health.sh to verify service health."
