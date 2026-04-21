#!/usr/bin/env bash
# =============================================================================
# WorkStation — scripts/plane.sh
# Canonical Plane lifecycle manager for the local platform stack.
#
# Usage:
#   bash scripts/plane.sh up       install (if needed) and start Plane
#   bash scripts/plane.sh down     stop Plane containers
#   bash scripts/plane.sh status   check whether Plane is reachable
#
# Runtime data is stored in WorkStation/runtime/plane/ (gitignored).
# Provider and workspace credentials are NOT stored here — configure those
# in your Plane workspace after first startup.
#
# Configuration overrides (port, URL, version):
#   Copy config/plane/.env.example to config/plane/.env and edit.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSTATION_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Runtime data directory (gitignored) ──────────────────────────────────────
PLANE_RUNTIME_DIR="${WORKSTATION_ROOT}/runtime/plane"
PLANE_APP_DIR="${PLANE_RUNTIME_DIR}/plane-app"
SETUP_SH="${PLANE_RUNTIME_DIR}/setup.sh"
PLANE_ENV="${PLANE_APP_DIR}/plane.env"
LOG_DIR="${WORKSTATION_ROOT}/runtime/logs/plane"

# ── Load optional config/plane/.env overrides ────────────────────────────────
PLANE_CONFIG_ENV="${WORKSTATION_ROOT}/config/plane/.env"
if [[ -f "${PLANE_CONFIG_ENV}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${PLANE_CONFIG_ENV}"
  set +a
fi

PLANE_URL="${PLANE_URL:-http://localhost:8080}"
PLANE_VERSION="${PLANE_VERSION:-}"
PLANE_SETUP_URL="${PLANE_SETUP_URL:-}"

timestamp() {
  date +"%Y%m%dT%H%M%S"
}

download_setup() {
  mkdir -p "${PLANE_RUNTIME_DIR}"
  if [[ ! -x "${SETUP_SH}" ]]; then
    local setup_url="${PLANE_SETUP_URL}"
    if [[ -z "${setup_url}" ]]; then
      if [[ -n "${PLANE_VERSION}" ]]; then
        setup_url="https://github.com/makeplane/plane/releases/download/${PLANE_VERSION}/setup.sh"
      else
        setup_url="https://github.com/makeplane/plane/releases/latest/download/setup.sh"
      fi
    fi
    echo "Downloading Plane setup from: ${setup_url}"
    curl -fsSL -o "${SETUP_SH}" "${setup_url}"
    chmod +x "${SETUP_SH}"
  fi
}

run_setup_menu() {
  local action="$1"
  mkdir -p "${LOG_DIR}"
  local log_path="${LOG_DIR}/$(timestamp)_plane_${action}.log"
  if ! (
    cd "${PLANE_RUNTIME_DIR}"
    printf '%s\n8\n' "${action}" | ./setup.sh
  ) >"${log_path}" 2>&1; then
    echo "Plane command failed. Log: ${log_path}"
    tail -n 40 "${log_path}" || true
    return 1
  fi
  echo "Plane log: ${log_path}"
}

compose_cmd() {
  (
    cd "${PLANE_APP_DIR}"
    docker compose --env-file "${PLANE_ENV}" -f docker-compose.yaml "$@"
  )
}

set_env_value() {
  local key="$1"
  local value="$2"
  if [[ ! -f "${PLANE_ENV}" ]]; then
    return 1
  fi
  if grep -q "^${key}=" "${PLANE_ENV}"; then
    sed -i "s#^${key}=.*#${key}=${value}#" "${PLANE_ENV}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${PLANE_ENV}"
  fi
}

configure_plane_env() {
  if [[ ! -f "${PLANE_ENV}" ]]; then
    return 1
  fi

  local host_port="8080"
  if [[ "${PLANE_URL}" =~ :([0-9]+)$ ]]; then
    host_port="${BASH_REMATCH[1]}"
  fi

  set_env_value "LISTEN_HTTP_PORT" "${host_port}"
  set_env_value "WEB_URL" "${PLANE_URL}"
  set_env_value "CORS_ALLOWED_ORIGINS" "${PLANE_URL}"
}

ensure_installed() {
  download_setup
  if [[ ! -d "${PLANE_APP_DIR}" ]]; then
    run_setup_menu 1
  fi
  configure_plane_env
}

fallback_up() {
  echo "Falling back to direct docker compose startup..."
  compose_cmd down --remove-orphans >/dev/null 2>&1 || true
  compose_cmd up -d
}

fallback_down() {
  echo "Falling back to direct docker compose shutdown..."
  compose_cmd down --remove-orphans || true
}

wait_until_ready() {
  local attempts=30
  local delay_seconds=5

  for ((i=1; i<=attempts; i++)); do
    if curl -fsS --max-time 5 "${PLANE_URL}" >/dev/null 2>&1; then
      echo "Plane is reachable at ${PLANE_URL}"
      return 0
    fi
    sleep "${delay_seconds}"
  done

  echo "Plane did not become reachable at ${PLANE_URL} after $((attempts * delay_seconds))s"
  echo "Check logs with: (cd ${PLANE_RUNTIME_DIR} && ./setup.sh and choose 'View Logs')"
  return 1
}

cmd="${1:-}"
if [[ -z "${cmd}" ]]; then
  echo "Usage: bash scripts/plane.sh {up|down|status}"
  exit 1
fi

case "${cmd}" in
  up)
    echo "=== WorkStation: Plane up ==="
    echo ""
    echo "  Runtime: ${PLANE_RUNTIME_DIR}"
    echo "  URL    : ${PLANE_URL}"
    echo ""
    ensure_installed
    echo "  Starting Plane containers..."
    if ! run_setup_menu 2; then
      fallback_up
    fi
    echo "  Waiting for Plane readiness..."
    wait_until_ready
    ;;
  down)
    echo "=== WorkStation: Plane down ==="
    if [[ -x "${SETUP_SH}" ]]; then
      echo "  Stopping Plane containers..."
      if ! run_setup_menu 3; then
        fallback_down
      fi
      echo "  Plane containers stopped."
    else
      echo "  Plane runtime is not installed yet."
    fi
    ;;
  status)
    if curl -fsS --max-time 5 "${PLANE_URL}" >/dev/null 2>&1; then
      echo "  ✓ Plane is reachable at ${PLANE_URL}"
      exit 0
    fi
    echo "  ✗ Plane is not reachable at ${PLANE_URL}"
    exit 1
    ;;
  *)
    echo "Usage: bash scripts/plane.sh {up|down|status}"
    exit 1
    ;;
esac
