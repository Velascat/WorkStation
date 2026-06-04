#!/usr/bin/env bash
# =============================================================================
# PlatformDeployment — run_with_boundary.sh
# Convenience wrapper that materializes a RepoGraph boundary artifact through
# the approved private-manifest export flow, exports REPOGRAPH_BOUNDARY_ARTIFACT_FILE,
# and then invokes Custodian.
#
# This script does not define graph semantics, projection logic, or boundary
# policy. It only prepares runtime inputs for Custodian.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DEPLOYMENT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python}"

# Resolve the private-manifest repo root by ROLE: $PRIVATE_MANIFEST_ROOT (or
# $PRIVATE_MANIFEST_DIR) wins, else scan the workspace for a repo hosting a
# private_manifest*.yaml (the manifest *type* filename — never a hardcoded
# repo-instance name).
_discover_private_manifest_root() {
  local workspace_root
  workspace_root="$(cd "${PLATFORM_DEPLOYMENT_ROOT}/.." && pwd)"
  local d
  for d in "$workspace_root"/*/; do
    if compgen -G "${d}private_manifest*.yaml" >/dev/null 2>&1 \
       || compgen -G "${d}src/*/data/private_manifest*.yaml" >/dev/null 2>&1 \
       || compgen -G "${d}manifests/private_manifest*.yaml" >/dev/null 2>&1 \
       || compgen -G "${d}manifests/*/private_manifest*.yaml" >/dev/null 2>&1; then
      echo "${d%/}"
      return 0
    fi
  done
  return 1
}

DEFAULT_PRIVATE_MANIFEST_ROOT="${PRIVATE_MANIFEST_ROOT:-${PRIVATE_MANIFEST_DIR:-$(_discover_private_manifest_root || true)}}"
DEFAULT_REPOGRAPH_ROOT="${REPOGRAPH_ROOT:-${PLATFORM_DEPLOYMENT_ROOT}/../RepoGraph}"

repo_root="${PLATFORM_DEPLOYMENT_ROOT}"
private_manifest_root="${DEFAULT_PRIVATE_MANIFEST_ROOT}"
repograph_root="${DEFAULT_REPOGRAPH_ROOT}"
profile="PUBLIC_SAFE"
boundary_artifact=""
keep_artifacts="false"
debug="false"
custodian_command=""
tmp_dir=""
generated_artifact="false"
artifact_summary=""

usage() {
  cat <<'EOF'
Usage:
  scripts/custodian/run_with_boundary.sh --repo-root PATH [options]

Required/primary options:
  --repo-root PATH             Repo root to audit with Custodian

Boundary input:
  --boundary-artifact PATH      Use an existing boundary artifact file
  --private-manifest-root PATH  private-manifest checkout root (default: discovered in workspace)
  --repograph-root PATH         RepoGraph checkout root for PYTHONPATH during export
  --profile NAME                Operator hint for the export run (default: PUBLIC_SAFE)

Custodian invocation:
  --custodian-command STRING    Shell command to run after env assembly
                               (default: custodian-multi --repos "<repo-root>" --fail-on-findings --no-color)

Runtime controls:
  --keep-artifacts              Preserve the temporary artifact directory
  --debug                       Print safe provenance/debug info
  -h, --help                    Show this help

Examples:
  scripts/custodian/run_with_boundary.sh --repo-root /path/to/repo
  scripts/custodian/run_with_boundary.sh --repo-root /path/to/repo --boundary-artifact /tmp/boundary.json
  scripts/custodian/run_with_boundary.sh --repo-root /path/to/repo --debug --keep-artifacts
EOF
}

die() {
  echo "run_with_boundary.sh: $*" >&2
  exit 2
}

abspath() {
  "$PYTHON_BIN" - "$1" <<'PY'
import os
import sys
print(os.path.abspath(sys.argv[1]))
PY
}

cleanup() {
  if [[ "${keep_artifacts}" != "true" && -n "${tmp_dir}" && -d "${tmp_dir}" ]]; then
    rm -rf "${tmp_dir}"
  fi
}
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      [[ $# -ge 2 ]] || die "--repo-root requires a value"
      repo_root="$2"
      shift 2
      ;;
    --private-manifest-root)
      [[ $# -ge 2 ]] || die "--private-manifest-root requires a value"
      private_manifest_root="$2"
      shift 2
      ;;
    --repograph-root)
      [[ $# -ge 2 ]] || die "--repograph-root requires a value"
      repograph_root="$2"
      shift 2
      ;;
    --profile)
      [[ $# -ge 2 ]] || die "--profile requires a value"
      profile="$2"
      shift 2
      ;;
    --boundary-artifact)
      [[ $# -ge 2 ]] || die "--boundary-artifact requires a value"
      boundary_artifact="$2"
      shift 2
      ;;
    --keep-artifacts)
      keep_artifacts="true"
      shift
      ;;
    --debug)
      debug="true"
      shift
      ;;
    --custodian-command)
      [[ $# -ge 2 ]] || die "--custodian-command requires a value"
      custodian_command="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "${private_manifest_root}" ]] || die "no private-manifest repo found: pass --private-manifest-root or set PRIVATE_MANIFEST_DIR"
repo_root="$(abspath "${repo_root}")"
private_manifest_root="$(abspath "${private_manifest_root}")"
repograph_root="$(abspath "${repograph_root}")"

[[ -d "${repo_root}" ]] || die "repo root not found: ${repo_root}"
[[ -d "${private_manifest_root}" ]] || die "private-manifest root not found: ${private_manifest_root}"
[[ -d "${repograph_root}" ]] || die "RepoGraph root not found: ${repograph_root}"

if [[ -z "${custodian_command}" ]]; then
  custodian_command="custodian-multi --repos \"${repo_root}\" --fail-on-findings --no-color"
fi

if [[ -z "${boundary_artifact}" ]]; then
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/platformdeployment-custodian-XXXXXX")"
  profile_token="${profile//[^A-Za-z0-9._-]/_}"
  boundary_artifact="${tmp_dir}/repograph-boundary-${profile_token}.json"

  if [[ "${debug}" == "true" ]]; then
    echo "[custodian-runner] materializing boundary artifact via the private manifest" >&2
    echo "[custodian-runner] private_manifest_root=${private_manifest_root}" >&2
    echo "[custodian-runner] repograph_root=${repograph_root}" >&2
    echo "[custodian-runner] profile=${profile}" >&2
  fi

  export PYTHONPATH="${private_manifest_root}/src:${repograph_root}/src${PYTHONPATH:+:${PYTHONPATH}}"
  "${PYTHON_BIN}" -m private_manifest.export_boundary_artifact \
    --graph-root "${private_manifest_root}/graph" \
    --out "${boundary_artifact}"
  generated_artifact="true"
fi

[[ -s "${boundary_artifact}" ]] || die "Boundary artifact missing or empty: ${boundary_artifact}"

artifact_summary="$("${PYTHON_BIN}" - "${boundary_artifact}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
print(f"{data.get('source_graph_id')}@{data.get('source_ref_or_commit')}")
PY
)"

export REPOGRAPH_BOUNDARY_ARTIFACT_FILE="${boundary_artifact}"

if [[ "${debug}" == "true" ]]; then
  echo "[custodian-runner] boundary_artifact=${REPOGRAPH_BOUNDARY_ARTIFACT_FILE}" >&2
  echo "[custodian-runner] boundary_provenance=${artifact_summary}" >&2
  echo "[custodian-runner] generated_artifact=${generated_artifact}" >&2
  echo "[custodian-runner] custodian_command=${custodian_command}" >&2
fi

cd "${repo_root}"
set +e
eval "${custodian_command}"
status=$?
set -e
exit "${status}"
