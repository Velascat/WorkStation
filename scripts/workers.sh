#!/usr/bin/env bash
# =============================================================================
# WorkStation — workers.sh
# Shim for OperationsCenter watcher lifecycle.
#
# WorkStation owns the startup/shutdown sequence; OperationsCenter owns the
# logic inside its own script. This shim bridges the two.
#
# Usage:
#   ./scripts/workers.sh start    — start all watcher roles (including intake)
#   ./scripts/workers.sh stop     — stop all watcher roles
#   ./scripts/workers.sh status   — print role status
#   ./scripts/workers.sh restart  — stop then start
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OC_ROOT="${OPERATIONS_CENTER_ROOT:-${HOME}/Documents/GitHub/OperationsCenter}"
OC_SCRIPT="${OC_ROOT}/scripts/operations-center.sh"

_log()  { printf '[WorkStation/workers] %s\n' "$*"; }
_ok()   { printf '[WorkStation/workers] %-40s [OK]\n'   "$1"; }
_warn() { printf '[WorkStation/workers] %-40s [WARN] %s\n' "$1" "$2"; }
_fail() { printf '[WorkStation/workers] %-40s [FAIL] %s\n' "$1" "$2" >&2; exit 1; }

if [[ ! -f "${OC_SCRIPT}" ]]; then
  _warn "OperationsCenter" "not found at ${OC_ROOT} — set OPERATIONS_CENTER_ROOT to override"
  exit 0
fi

CMD="${1:-status}"
shift || true

case "${CMD}" in
  start)
    _log "Starting OperationsCenter watchers..."
    bash "${OC_SCRIPT}" watch-all "$@"
    _ok "watchers started"
    ;;
  stop)
    _log "Stopping OperationsCenter watchers..."
    bash "${OC_SCRIPT}" watch-all-stop "$@"
    _ok "watchers stopped"
    ;;
  status)
    bash "${OC_SCRIPT}" watch-all-status "$@"
    ;;
  restart)
    _log "Restarting OperationsCenter watchers..."
    bash "${OC_SCRIPT}" watch-all-stop "$@" || true
    bash "${OC_SCRIPT}" watch-all "$@"
    _ok "watchers restarted"
    ;;
  *)
    echo "Usage: workers.sh start | stop | status | restart" >&2
    exit 1
    ;;
esac
