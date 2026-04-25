# Contributing to WorkStation

WorkStation is the startup and runtime authority for the platform. It owns the Docker Compose stack, environment configuration, service health definitions, and the local-lane execution environment.

## Before You Start

- Check open issues to avoid duplicate work
- For significant changes, open an issue first to discuss the approach
- WorkStation changes often have downstream effects — test the full stack locally before submitting

## Development Setup

```bash
git clone https://github.com/Velascat/WorkStation.git
cd WorkStation
```

WorkStation is primarily shell scripts and Docker Compose files. A Python virtualenv is used for tooling and tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest pyyaml httpx
```

Requires Docker, Docker Compose, and Python 3.11+.

## Running Tests

```bash
.venv/bin/python -m pytest
```

Unit tests run without a live stack. Smoke tests that require Docker are marked and skipped by default.

## Starting the Stack

```bash
bash up.sh
```

WorkStation is the **only** startup authority — do not start platform services by other means.

## Project Structure

```
up.sh                    # canonical startup entry point
docker-compose.yml       # base compose definition
docker-compose.local.yml # local overrides (gitignored)
services/                # per-service compose fragments and config
tools/                   # local lane setup, health checks, scripts
docs/
  architecture/          # system overview, contracts, adapter docs, glossary
  operations/            # setup and operational guides
  history/               # archival records (not current guidance)
```

## Architectural Constraints

WorkStation is the **startup authority only**. Contributions must not:

- Add planning or proposal logic (belongs in OperationsCenter)
- Add routing logic (belongs in SwitchBoard)
- Add adapter or execution logic (belongs in OperationsCenter backends)
- Self-bootstrap platform services outside of `up.sh`

## Pull Requests

- Keep PRs focused — one concern per PR
- Changes to `docker-compose.yml` or `up.sh` require a clear explanation in the PR description
- Environment variable changes must be reflected in `.env.example`
- Update `docs/` if the change affects operator-visible startup or configuration behavior

## Commit Style

| Prefix | Use for |
|--------|---------|
| `feat:` | new user-facing feature |
| `fix:` | bug fix |
| `refactor:` | internal restructure, no behavior change |
| `docs:` | documentation only |
| `test:` | test additions or fixes |
| `chore:` | tooling, CI, dependency updates |

## Code of Conduct

This project follows the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md). By participating you agree to uphold its standards.
