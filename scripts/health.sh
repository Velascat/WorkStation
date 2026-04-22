#!/usr/bin/env bash
# =============================================================================
# WorkStation — health.sh
# Curl the /health endpoint of each service and report pass/fail.
# Exit code: 0 if all healthy, 1 if any service is unhealthy/unreachable.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Load .env ─────────────────────────────────────────────────────────────────
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

PORT_SWITCHBOARD="${PORT_SWITCHBOARD:-20401}"
CURL_TIMEOUT=5
ALL_OK=true

check_health() {
  local name="$1"
  local url="$2"

  local http_code
  local body

  body=$(curl --silent --show-error --max-time "${CURL_TIMEOUT}" \
    --write-out "\n%{http_code}" \
    "${url}" 2>&1) || true

  http_code=$(echo "${body}" | tail -n1)
  response=$(echo "${body}" | head -n -1)

  if [[ "${http_code}" == "200" ]]; then
    echo "  [OK]   ${name}  (${url})  →  HTTP ${http_code}"
    echo "         ${response}"
  else
    echo "  [FAIL] ${name}  (${url})  →  HTTP ${http_code:-no response}"
    if [[ -n "${response}" ]]; then
      echo "         ${response}"
    fi
    ALL_OK=false
  fi
}

echo "=== WorkStation: health check ==="
echo ""
check_health "SwitchBoard" "http://localhost:${PORT_SWITCHBOARD}/health"
echo ""

if ${ALL_OK}; then
  echo "All services healthy."
  exit 0
else
  echo "One or more services are unhealthy or unreachable."
  exit 1
fi
