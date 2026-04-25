#!/usr/bin/env bash
# =============================================================================
# WorkStation — down.sh
# Stop and remove all stack containers.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose/docker-compose.yml"

echo "=== WorkStation: stopping stack ==="

# Stop OperationsCenter watchers before tearing down the stack
bash "${SCRIPT_DIR}/workers.sh" stop 2>&1 | sed 's/^/  /' || true

echo ""

docker compose \
  --file "${COMPOSE_FILE}" \
  down --remove-orphans

echo ""
echo "=== Stack stopped. ==="
