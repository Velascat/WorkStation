"""
workstation_cli — command-line interface for WorkStation stack management.

Usage:
    python -m workstation_cli <command> [options]

Commands:
    up       Start the stack via docker compose.
    down     Stop the stack via docker compose.
    health   Check health endpoints and print results.
    status   Aggregate health + service info and print summary.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .health import check_all_health
from .services import load_services_from_yaml
from .status import aggregate_status

# ── Repo paths ────────────────────────────────────────────────────────────────

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]          # tools/workstation_cli -> repo root
_COMPOSE_FILE = _REPO_ROOT / "compose" / "docker-compose.yml"
_ENDPOINTS_FILE = _REPO_ROOT / "config" / "workstation" / "endpoints.yaml"
_ENV_FILE = _REPO_ROOT / ".env"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compose(*args: str) -> int:
    """Run a docker compose command and return the exit code."""
    cmd = [
        "docker", "compose",
        "--file", str(_COMPOSE_FILE),
    ]
    if _ENV_FILE.exists():
        cmd += ["--env-file", str(_ENV_FILE)]
    cmd += list(args)
    result = subprocess.run(cmd)
    return result.returncode


# ── Command handlers ──────────────────────────────────────────────────────────

def cmd_up(args: argparse.Namespace) -> int:
    """Start the stack in detached mode."""
    print("=== WorkStation: starting stack ===")
    rc = _compose("up", "--detach", "--remove-orphans")
    if rc == 0:
        print("\nStack started. Run 'workstation_cli health' to verify.")
    else:
        print(f"\ndocker compose up failed (exit code {rc})", file=sys.stderr)
    return rc


def cmd_down(args: argparse.Namespace) -> int:
    """Stop and remove stack containers."""
    print("=== WorkStation: stopping stack ===")
    rc = _compose("down", "--remove-orphans")
    if rc == 0:
        print("Stack stopped.")
    else:
        print(f"\ndocker compose down failed (exit code {rc})", file=sys.stderr)
    return rc


def cmd_health(args: argparse.Namespace) -> int:
    """Check health endpoints for all services."""
    if not _ENDPOINTS_FILE.exists():
        print(
            f"Endpoints config not found: {_ENDPOINTS_FILE}\n"
            "Copy config/workstation/endpoints.example.yaml to endpoints.yaml first.",
            file=sys.stderr,
        )
        return 1

    services = load_services_from_yaml(_ENDPOINTS_FILE)
    results = check_all_health(services)

    print("=== WorkStation: health check ===\n")
    all_ok = True
    for name, result in results.items():
        icon = "[OK]  " if result["healthy"] else "[FAIL]"
        status = result.get("status_code", "N/A")
        url = result.get("url", "")
        print(f"  {icon}  {name:<14}  {url}  →  HTTP {status}")
        if result.get("error"):
            print(f"         Error: {result['error']}")
        if result.get("body"):
            snippet = result["body"][:100].replace("\n", " ")
            print(f"         {snippet}")
        print()
        if not result["healthy"]:
            all_ok = False

    if args.json:
        print(json.dumps(results, indent=2))

    if all_ok:
        print("All services healthy.")
        return 0
    else:
        print("One or more services are unhealthy.", file=sys.stderr)
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Print aggregate status summary."""
    if not _ENDPOINTS_FILE.exists():
        print(
            f"Endpoints config not found: {_ENDPOINTS_FILE}\n"
            "Copy config/workstation/endpoints.example.yaml to endpoints.yaml first.",
            file=sys.stderr,
        )
        return 1

    services = load_services_from_yaml(_ENDPOINTS_FILE)
    summary = aggregate_status(services)

    print("=== WorkStation: status ===\n")

    overall = summary.get("overall", "unknown")
    color = "\033[32m" if overall == "healthy" else "\033[31m"
    reset = "\033[0m"
    print(f"  Overall: {color}{overall.upper()}{reset}")
    print(f"  Timestamp: {summary.get('timestamp', 'N/A')}\n")

    for name, svc in summary.get("services", {}).items():
        h = svc.get("healthy", False)
        icon = "[OK]  " if h else "[FAIL]"
        latency = svc.get("latency_ms")
        lat_str = f"  latency={latency}ms" if latency is not None else ""
        print(f"  {icon}  {name:<14}{lat_str}")

    if args.json:
        print("\n" + json.dumps(summary, indent=2))

    return 0 if summary.get("overall") == "healthy" else 1


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workstation_cli",
        description="WorkStation stack management CLI.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # up
    p_up = sub.add_parser("up", help="Start the stack in detached mode.")
    p_up.set_defaults(func=cmd_up)

    # down
    p_down = sub.add_parser("down", help="Stop and remove stack containers.")
    p_down.set_defaults(func=cmd_down)

    # health
    p_health = sub.add_parser("health", help="Check health endpoints.")
    p_health.add_argument("--json", action="store_true", help="Output results as JSON.")
    p_health.set_defaults(func=cmd_health)

    # status
    p_status = sub.add_parser("status", help="Print aggregate status summary.")
    p_status.add_argument("--json", action="store_true", help="Output results as JSON.")
    p_status.set_defaults(func=cmd_status)

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    rc = args.func(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
