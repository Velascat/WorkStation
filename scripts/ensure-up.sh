#!/usr/bin/env bash
# =============================================================================
# WorkStation — ensure-up.sh
# Ensure the stack is running. If services are already healthy, do nothing.
# If they are not, start the stack with docker compose up.
#
# Exit code: 0 if stack is healthy after this script, 1 otherwise.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose/docker-compose.yml"

if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

PORT_SWITCHBOARD="${PORT_SWITCHBOARD:-20401}"
CURL_TIMEOUT=3
MAX_WAIT=60

_healthy() {
  curl --silent --fail --max-time "${CURL_TIMEOUT}" "http://localhost:$1/health" > /dev/null 2>&1
}

echo "=== WorkStation: ensure-up ==="
echo ""

if _healthy "${PORT_SWITCHBOARD}"; then
  echo "  ✓ Stack already running and healthy."
  echo "    SwitchBoard : http://localhost:${PORT_SWITCHBOARD}"
  exit 0
fi

if [[ ! -f "${REPO_ROOT}/.env" ]]; then
  echo "  ✗ .env not found. Copy and configure:"
  echo "      cp .env.example .env"
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "  ✗ Docker not found. Install Docker Desktop or Docker Engine."
  exit 1
fi

echo "  Stack not running — starting..."
docker compose \
  --file "${COMPOSE_FILE}" \
  --env-file "${REPO_ROOT}/.env" \
  up --detach --remove-orphans --build 2>&1 | sed 's/^/    /'

echo ""
echo "  Waiting for services (up to ${MAX_WAIT}s)..."
ELAPSED=0
while [[ ${ELAPSED} -lt ${MAX_WAIT} ]]; do
  if _healthy "${PORT_SWITCHBOARD}"; then
    echo "  ✓ Stack healthy after ${ELAPSED}s."
    echo "    SwitchBoard : http://localhost:${PORT_SWITCHBOARD}"
    exit 0
  fi
  sleep 2
  ELAPSED=$(( ELAPSED + 2 ))
  printf "."
done

echo ""
echo "  ✗ Stack did not become healthy within ${MAX_WAIT}s."
echo "    Run:  bash scripts/health.sh  to diagnose."
exit 1
