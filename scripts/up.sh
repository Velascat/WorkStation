#!/usr/bin/env bash
# =============================================================================
# WorkStation — up.sh
# Single entrypoint to start the full platform stack.
#
# Usage:
#   ./scripts/up.sh
#
# Exit code: 0 if critical services are healthy, 1 on critical failure.
# Optional services (Plane, local models) emit warnings but do not block.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose/docker-compose.yml"

CURL_TIMEOUT=3
SWITCHBOARD_WAIT=60   # seconds to wait for SwitchBoard health

# ── Logging ───────────────────────────────────────────────────────────────────
_log()  { printf '[WorkStation] %s\n' "$*"; }
_ok()   { printf '[WorkStation] %-44s [OK]\n'   "$1"; }
_warn() { printf '[WorkStation] %-44s [WARN] %s\n' "$1" "$2"; }
_skip() { printf '[WorkStation] %-44s [SKIP] %s\n' "$1" "$2"; }
_fail() { printf '[WorkStation] %-44s [FAIL] %s\n' "$1" "$2" >&2; exit 1; }

echo "=== WorkStation: starting platform ==="
echo ""

# ── Step 1: Environment ───────────────────────────────────────────────────────
_log "Validating environment..."

if ! command -v docker &>/dev/null; then
  _fail "docker" "not found — install Docker Desktop or Docker Engine"
fi

if [[ ! -f "${REPO_ROOT}/.env" ]]; then
  if [[ -f "${REPO_ROOT}/.env.example" ]]; then
    cp "${REPO_ROOT}/.env.example" "${REPO_ROOT}/.env"
    _log "Created .env from .env.example — edit before production use."
  else
    _fail ".env" "not found and no .env.example to copy from"
  fi
fi

set -a
# shellcheck disable=SC1091
source "${REPO_ROOT}/.env"
set +a

PORT_SWITCHBOARD="${PORT_SWITCHBOARD:-20401}"
PLANE_ENABLED="${PLANE_ENABLED:-false}"
PLANE_URL="${PLANE_URL:-http://localhost:8080}"

_ok "Environment"
echo ""

# ── Step 1b: Config file bootstrap ───────────────────────────────────────────
_log "Checking config files..."

SB_POLICY="${REPO_ROOT}/config/switchboard/policy.yaml"
SB_POLICY_EXAMPLE="${REPO_ROOT}/config/switchboard/policy.example.yaml"

if [[ ! -f "${SB_POLICY}" ]]; then
  if [[ -f "${SB_POLICY_EXAMPLE}" ]]; then
    cp "${SB_POLICY_EXAMPLE}" "${SB_POLICY}"
    _warn "config/switchboard/policy.yaml" "created from example — review before use"
  else
    _warn "config/switchboard/policy.yaml" "missing and no example found — routing will use defaults"
  fi
else
  _ok "config/switchboard/policy.yaml"
fi

echo ""

# ── Step 2: SwitchBoard (critical) ────────────────────────────────────────────
_log "Starting SwitchBoard..."

docker compose \
  --file "${COMPOSE_FILE}" \
  --env-file "${REPO_ROOT}/.env" \
  up --detach --remove-orphans \
  2>&1 | sed 's/^/  /'

echo ""
_log "Waiting for SwitchBoard on :${PORT_SWITCHBOARD} (up to ${SWITCHBOARD_WAIT}s)..."

ELAPSED=0
HEALTHY=false
while [[ ${ELAPSED} -lt ${SWITCHBOARD_WAIT} ]]; do
  if curl --silent --fail --max-time "${CURL_TIMEOUT}" \
       "http://localhost:${PORT_SWITCHBOARD}/health" >/dev/null 2>&1; then
    HEALTHY=true
    break
  fi
  sleep 2
  ELAPSED=$(( ELAPSED + 2 ))
done

if [[ "${HEALTHY}" != "true" ]]; then
  _fail "SwitchBoard" "not healthy after ${SWITCHBOARD_WAIT}s — run: bash scripts/health.sh"
fi

_ok "SwitchBoard (http://localhost:${PORT_SWITCHBOARD})"
echo ""

# ── Step 3: Plane (optional) ──────────────────────────────────────────────────
_log "Checking Plane..."

if [[ "${PLANE_ENABLED}" == "true" ]]; then
  _log "Starting Plane (this may take a minute on first install)..."
  if bash "${SCRIPT_DIR}/plane.sh" up; then
    _ok "Plane (${PLANE_URL})"
  else
    _warn "Plane" "did not start — check: bash scripts/plane.sh status"
  fi
else
  _warn "Plane" "PLANE_ENABLED is not set to true in .env — board features disabled"
fi

echo ""

# ── Step 4: Local lane readiness (informational) ──────────────────────────────
_log "Checking local lane (aider_local)..."

if command -v aider &>/dev/null; then
  _ok "aider ($(command -v aider))"
else
  _warn "aider" "binary not found — aider_local lane unavailable"
fi

echo ""

# ── Step 5: OperationsCenter watchers ────────────────────────────────────────
_log "Starting OperationsCenter watchers..."
if bash "${SCRIPT_DIR}/workers.sh" start 2>&1 | sed 's/^/  /'; then
  _ok "OperationsCenter watchers"
else
  _warn "OperationsCenter watchers" "failed to start — run: bash scripts/workers.sh start"
fi

echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "=== WorkStation ready ==="
echo ""
printf '  %-16s http://localhost:%s\n' "SwitchBoard" "${PORT_SWITCHBOARD}"
if [[ "${PLANE_ENABLED}" == "true" ]]; then
  printf '  %-16s %s\n' "Plane" "${PLANE_URL}"
fi
echo ""
echo "  health   →  bash scripts/health.sh"
echo "  status   →  bash scripts/status.sh"
echo "  logs     →  bash scripts/logs.sh"
echo "  workers  →  bash scripts/workers.sh status"
echo "  stop     →  bash scripts/down.sh"
