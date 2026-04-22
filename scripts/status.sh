#!/usr/bin/env bash
# =============================================================================
# WorkStation — status.sh
# Print a full status summary: Docker Compose service state + health checks.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose/docker-compose.yml"

# ── Load .env ─────────────────────────────────────────────────────────────────
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

echo "=== WorkStation: status ==="
echo "Timestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

echo "── Docker Compose service state ──────────────────────────────────────────"
docker compose --file "${COMPOSE_FILE}" ps 2>/dev/null || \
  echo "  (could not reach Docker daemon or no containers running)"

echo ""
echo "── HTTP health checks ────────────────────────────────────────────────────"
"${SCRIPT_DIR}/health.sh" || true

echo ""
echo "── Resource usage ────────────────────────────────────────────────────────"
docker stats --no-stream \
  workstation-switchboard 2>/dev/null || \
  echo "  (containers not running)"
