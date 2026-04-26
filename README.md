# WorkStation

WorkStation is the local developer platform that deploys and operates the shared AI
coding stack. It owns the lifecycle of **SwitchBoard**, the **Plane** task board, and
the **tiny local models** consumed by the `aider_local` coding lane.

WorkStation does not participate in the request path at runtime. It is a pure
infrastructure and operational concern — Dockerfiles, compose manifests, lifecycle
scripts, health checks, port assignments, environment injection.

**Ownership boundary:** WorkStation owns everything that makes services *run*. If you
are asking "where does this service run?", the answer lives here. If you are asking
"what does this service do?", the answer lives in the service repo. See
[`docs/architecture/ownership.md`](docs/architecture/ownership.md) for the full model.

**System architecture:** The full platform design, component roles, and the removal of
the architecture are documented in
[`docs/architecture/system_overview.md`](docs/architecture/system_overview.md).

---

## Services

| Service          | Port | Purpose |
|------------------|------|---------|
| SwitchBoard      | 20401 | Execution-lane selector — classifies tasks, applies routing policy, selects lane |
| Plane            | 8080  | Task board — work state, comments, labels (separate script-managed stack) |
| tiny local models | local | Serves models for the `aider_local` coding lane (WorkStation-deployed) |

SwitchBoard is required for coding lane dispatch. Plane is required for OperationsCenter
operation. Tiny model deployment is required for the `aider_local` lane.

## What WorkStation Is Not

- **Not the task-prioritization engine.** WorkStation does not decide what work
  matters next. That is OperationsCenter's job.

- **Not the lane selector.** WorkStation deploys SwitchBoard; it does not make lane
  selection decisions. SwitchBoard owns the policy and the selection logic.

- **Not the coding execution layer.** WorkStation does not run agents, edit files, or
  invoke CLIs. OperationsCenter's execution boundary and its backend processes do that.

- **Not the workflow harness.** WorkStation does not define or execute multi-step
  coding workflows. That is Archon's job.

- **Not a provider proxy.** WorkStation does not forward LLM API requests to external
  providers.

---

## Architecture

```
WorkStation deploys and manages:

  SwitchBoard (:20401)    — execution-lane selector
  Plane (:8080)           — task board (OperationsCenter dependency)
  tiny local models       — served locally for aider_local lane

System flow (see docs/architecture/system_overview.md for the full picture):

  OperationsCenter planning → SwitchBoard routing → OperationsCenter execution boundary
                                                     ├── claude_cli   (Claude CLI, OAuth)
                                                     ├── codex_cli    (Codex CLI, subscription)
                                                     └── aider_local  (Aider + WorkStation models)
```

See [`docs/architecture/system_overview.md`](docs/architecture/system_overview.md) for
the full layered view, component roles, and conceptual flow.

---

## Local Lane: aider_local

WorkStation hosts the `aider_local` execution lane — local Aider execution backed
by tiny local models. This lane runs at zero marginal API cost and is suitable for
lint fixes, simple edits, and documentation tasks.

```bash
# Configure (copy example, set enabled: true, configure model endpoints)
cp config/workstation/local_lane.example.yaml config/workstation/local_lane.yaml

# Check lane status
python -m workstation_cli lane status aider_local

# Start managed model services (if start_command is configured)
python -m workstation_cli lane start aider_local

# Stop managed services
python -m workstation_cli lane stop aider_local
```

Lane states: `disabled` → `configured` → `starting` → `ready` | `unhealthy` | `failed`

For full setup and troubleshooting, see
[`docs/operations/local-lane-setup.md`](docs/operations/local-lane-setup.md).
For the architectural rationale, see
[`docs/architecture/local-lane.md`](docs/architecture/local-lane.md).

---

## Cross-Repo Architecture Docs

WorkStation carries the canonical architecture docs for the multi-repo platform.
Recent additions include:

- [docs/architecture/routing-tuning.md](docs/architecture/routing-tuning.md)
- [docs/architecture/routing-tuning-examples.md](docs/architecture/routing-tuning-examples.md)
- [docs/architecture/upstream-patch-evaluation.md](docs/architecture/upstream-patch-evaluation.md)
- [docs/architecture/upstream-patch-evaluation-examples.md](docs/architecture/upstream-patch-evaluation-examples.md)

These documents keep routing tuning, adapter-first integration, and any later
upstream patch proposals clearly separated from active runtime behavior.

---

## Quick Start

```bash
# 1. Copy and edit environment config
cp .env.example .env

# 2. Copy service configs
cp config/switchboard/policy.example.yaml      config/switchboard/policy.yaml
cp config/workstation/endpoints.example.yaml   config/workstation/endpoints.yaml
cp config/workstation/services.example.yaml    config/workstation/services.yaml
cp config/workstation/ports.example.yaml       config/workstation/ports.yaml

# 3. Start the stack
./scripts/up.sh

# 4. Verify health
./scripts/health.sh
```

On Windows (PowerShell):

```powershell
./scripts/bootstrap.ps1   # first-time setup
./scripts/up.ps1
./scripts/health.ps1
```

---

## Health and Status

```bash
# Shell health check (exits 0 = healthy, 1 = unhealthy)
./scripts/health.sh

# Full status summary (compose state + health + resource usage)
./scripts/status.sh

# Python CLI — human-readable
python -m workstation_cli status

# Python CLI — machine-readable JSON
python -m workstation_cli status --json

# Raw health JSON
python -m workstation_cli health --json
```

### Health model

| Status      | Meaning                                                       |
|-------------|---------------------------------------------------------------|
| `healthy`   | All required services reachable and returning HTTP 200        |
| `degraded`  | Required services healthy; one or more optional services down |
| `unhealthy` | At least one required service is unreachable or non-200       |

See [docs/health-model.md](docs/health-model.md) for full semantics and example JSON output.

---

## Endpoint Reference

| Endpoint                                     | Service     | Description                          |
|----------------------------------------------|-------------|--------------------------------------|
| `http://localhost:20401/health`              | SwitchBoard | Health check                         |
| `http://localhost:20401/route`               | SwitchBoard | Canonical `TaskProposal -> LaneDecision` |
| `http://localhost:20401/route-plan`          | SwitchBoard | Primary, fallback, and escalation plan |

All client traffic targets SwitchBoard (`:20401`).

---

## Scripts

| Script                      | What it does                                  |
|-----------------------------|-----------------------------------------------|
| `up.sh` / `up.ps1`          | Start the stack in detached mode              |
| `down.sh` / `down.ps1`      | Stop and remove containers                    |
| `restart.sh` / `restart.ps1`| Stop then start the stack                     |
| `health.sh` / `health.ps1`  | Curl health endpoints; exit 0 if all healthy  |
| `status.sh` / `status.ps1`  | Health + compose state + resource usage       |
| `logs.sh` / `logs.ps1`      | Stream compose logs (optional: service name)  |
| `bootstrap.ps1`             | First-time setup (copy .env, pull images)     |

```bash
# Restart
./scripts/restart.sh

# Tail all logs
./scripts/logs.sh

# Tail logs for one service
./scripts/logs.sh switchboard
./scripts/logs.sh switchboard 100  # last 100 lines
```

---

## Repository Layout

```
WorkStation/
├── compose/                  Docker Compose files and profiles
│   ├── docker-compose.yml
│   ├── docker-compose.override.example.yml
│   └── profiles/
│       ├── core.yml
│       ├── dev.yml
│       └── observability.yml
├── config/
│   ├── switchboard/          policy, profiles, capabilities config
│   └── workstation/          endpoint registry, service list, port map
├── scripts/                  Bash + PowerShell helper scripts
├── docs/                     Architecture, operations, health model, roadmap
├── tools/workstation_cli/    Python CLI (up/down/health/status)
└── test/
    ├── smoke/                Live stack smoke tests (skipped if stack down)
    └── unit/                 Unit tests for config, health, status logic
```

---

## Configuration

All environment variables are documented in `.env.example`. Copy to `.env` and adjust.

Service configs live under `config/`. Copy each `.example.*` to its live name before starting:

```bash
cp config/switchboard/policy.example.yaml      config/switchboard/policy.yaml
cp config/workstation/endpoints.example.yaml   config/workstation/endpoints.yaml
cp config/workstation/services.example.yaml    config/workstation/services.yaml
cp config/workstation/ports.example.yaml       config/workstation/ports.yaml
# Optional: local lane configuration
cp config/workstation/local_lane.example.yaml  config/workstation/local_lane.yaml
```

Live config files are excluded from version control (see `.gitignore`). Only `.example.*` variants are committed.

---

## Python CLI

```bash
# Install dependencies (PyYAML + optional httpx)
pip install pyyaml httpx

# Commands
python -m workstation_cli up
python -m workstation_cli down
python -m workstation_cli health
python -m workstation_cli health --json
python -m workstation_cli status
python -m workstation_cli status --json

# Local lane commands
python -m workstation_cli lane status aider_local
python -m workstation_cli lane health aider_local
python -m workstation_cli lane start aider_local
python -m workstation_cli lane stop aider_local
python -m workstation_cli lane status --json aider_local
```

---

## Tests

```bash
# Unit tests (no stack required)
pytest test/unit/ -v

# Smoke tests (skipped if stack is not running)
pytest test/smoke/ -v
```

---

## Docs

| Document | What it covers |
|----------|----------------|
| [docs/architecture/system_overview.md](docs/architecture/system_overview.md) | Cross-repo architecture, component roles, architecture decisions |
| [docs/architecture/contracts.md](docs/architecture/contracts.md) | Canonical cross-repo contract models (Phase 3) |
| [docs/architecture/contracts-examples.md](docs/architecture/contracts-examples.md) | Example JSON payloads for all contract models |
| [docs/architecture/kodo-adapter.md](docs/architecture/kodo-adapter.md) | kodo backend adapter architecture (Phase 5) |
| [docs/architecture/kodo-adapter-examples.md](docs/architecture/kodo-adapter-examples.md) | kodo adapter usage examples |
| [docs/architecture/local-lane.md](docs/architecture/local-lane.md) | aider_local lane design and boundaries |
| [docs/architecture/repo_responsibility_matrix.md](docs/architecture/repo_responsibility_matrix.md) | Per-repo owns/does-not-own matrix |
| [docs/architecture/glossary.md](docs/architecture/glossary.md) | Canonical terminology |
| [docs/architecture/adr/](docs/architecture/adr/) | Architecture decision records |
| [docs/operations/local-lane-setup.md](docs/operations/local-lane-setup.md) | aider_local lane setup and troubleshooting |
| [docs/operations.md](docs/operations.md) | Stack runbook (start, stop, logs, etc.) |
| [docs/health-model.md](docs/health-model.md) | Health semantics, required vs optional, JSON |
| [docs/service-map.md](docs/service-map.md) | Service inventory |
| [docs/port-map.md](docs/port-map.md) | Port assignments |

---

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).

