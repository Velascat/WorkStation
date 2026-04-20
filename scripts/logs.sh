#!/usr/bin/env bash
# =============================================================================
# WorkStation — logs.sh
# Tail Docker Compose logs for all services, or a specific one.
#
# Usage:
#   ./scripts/logs.sh                  # all services
#   ./scripts/logs.sh switchboard      # only SwitchBoard
#   ./scripts/logs.sh ninerouter       # only 9router
#   ./scripts/logs.sh switchboard 100  # SwitchBoard, last 100 lines
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose/docker-compose.yml"

SERVICE="${1:-}"
TAIL="${2:-50}"

echo "=== WorkStation: streaming logs (Ctrl+C to stop) ==="
if [[ -n "${SERVICE}" ]]; then
  echo "Service: ${SERVICE}"
fi
echo ""

if [[ -n "${SERVICE}" ]]; then
  docker compose \
    --file "${COMPOSE_FILE}" \
    logs --follow --tail="${TAIL}" "${SERVICE}"
else
  docker compose \
    --file "${COMPOSE_FILE}" \
    logs --follow --tail="${TAIL}"
fi
