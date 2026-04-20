"""
workstation_cli — command-line interface for WorkStation stack management.

Usage:
    python -m workstation_cli <command> [options]

Commands:
    up            Start the stack via docker compose.
    down          Stop the stack via docker compose.
    health        Check health endpoints and print results.
    health --json Output health results as JSON.
    status        Aggregate health + service info and print summary.
    status --json Output status summary as JSON.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .config import load_config
from .health import check_all_health
from .status import aggregate_status

# ── Repo paths ────────────────────────────────────────────────────────────────

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]          # tools/workstation_cli -> repo root
_COMPOSE_FILE = _REPO_ROOT / "compose" / "docker-compose.yml"
_CONFIG_DIR = _REPO_ROOT / "config" / "workstation"
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


def _load_or_die() -> dict:
    """Load service config from config/workstation/. Exit with message on failure."""
    endpoints_file = _CONFIG_DIR / "endpoints.yaml"
    if not endpoints_file.exists():
        print(
            f"Endpoints config not found: {endpoints_file}\n"
            "Copy config/workstation/endpoints.example.yaml to endpoints.yaml first.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        cfg = load_config(_CONFIG_DIR)
    except Exception as exc:
        print(f"Failed to load config: {exc}", file=sys.stderr)
        sys.exit(1)
    return cfg.services


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
    services = _load_or_die()
    results = check_all_health(services)

    if args.json:
        print(json.dumps(results, indent=2))
        all_ok = all(r["healthy"] for r in results.values())
        return 0 if all_ok else 1

    print("=== WorkStation: health check ===\n")
    all_ok = True
    for name, result in results.items():
        icon = "[OK]  " if result["healthy"] else "[FAIL]"
        status = result.get("status_code", "N/A")
        url = result.get("url", "")
        latency = result.get("latency_ms")
        lat_str = f"  {latency}ms" if latency is not None else ""
        print(f"  {icon}  {name:<16}  {url}  ->  HTTP {status}{lat_str}")
        if result.get("error"):
            print(f"           Error: {result['error']}")
        print()
        if not result["healthy"]:
            all_ok = False

    if all_ok:
        print("All services healthy.")
        return 0
    else:
        print("One or more services are unhealthy.", file=sys.stderr)
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Print aggregate status summary."""
    services = _load_or_die()
    summary = aggregate_status(services)

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("status") == "healthy" else 1

    print("=== WorkStation: status ===\n")

    platform_status = summary.get("status", "unknown")
    if platform_status == "healthy":
        color = "\033[32m"
    elif platform_status == "degraded":
        color = "\033[33m"
    else:
        color = "\033[31m"
    reset = "\033[0m"
    print(f"  Platform:  {color}{platform_status.upper()}{reset}")
    print(f"  Timestamp: {summary.get('timestamp', 'N/A')}\n")

    for name, svc in summary.get("services", {}).items():
        healthy = svc.get("status") == "healthy"
        icon = "[OK]  " if healthy else "[FAIL]"
        base = svc.get("base_url", "")
        required = getattr(services.get(name), "required", True)
        req_label = "" if required else "  (optional)"
        print(f"  {icon}  {name:<16}  {base}{req_label}")

    print()
    return 0 if platform_status == "healthy" else 1


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
    p_status.add_argument("--json", action="store_true", help="Output status as JSON.")
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
