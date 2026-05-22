# PlatformDeployment

PlatformDeployment is the local developer platform that deploys and operates the shared AI
coding stack. It owns the lifecycle of **SwitchBoard**, the **Plane** task board, and
the **tiny local models** consumed by the `aider_local` coding lane.

**Ownership boundary:** PlatformDeployment owns everything that makes services *run*. If you
are asking "where does this service run?", the answer lives here. If you are asking
"what does this service do?", the answer lives in the service repo. See
[`docs/architecture/system/ownership.md`](docs/architecture/system/ownership.md) for the full model.

**System architecture:** The full platform design and component roles are documented in
[`docs/architecture/system/system_overview.md`](docs/architecture/system/system_overview.md).

---

## What this repo is

- Service Dockerfiles and compose manifests for SwitchBoard, Plane, and aider_local tiny models
- Lifecycle scripts and worker shims (backing the CLI)
- Port assignments, environment injection, health checks
- A unified CLI under `tools/platform_deployment_cli/` covering the full operator surface
- Deployment and operator docs under `docs/`

## What this repo is not

- A request-path participant — PlatformDeployment is invoked by operators and bootstrap scripts only
- OperationsCenter / SwitchBoard / OperatorConsole — service code lives in those repos
- A package — installs nothing on `pip install platformdeployment`; it is a deployment harness
- A scheduler or queue system

---

## Services

| Service          | Port | Purpose |
|------------------|------|---------|
| SwitchBoard      | 20401 | Execution-lane selector — classifies tasks, applies routing policy, selects lane |
| Plane            | 8080  | Task board — work state, comments, labels (separate script-managed stack) |
| tiny local models | local | Serves models for the `aider_local` coding lane (PlatformDeployment-deployed) |

SwitchBoard is required for coding lane dispatch. Plane is required for OperationsCenter
operation. Tiny model deployment is required for the `aider_local` lane.

## What PlatformDeployment Is Not

- **Not the task-prioritization engine.** PlatformDeployment does not decide what work
  matters next. That is OperationsCenter's job.

- **Not the lane selector.** PlatformDeployment deploys SwitchBoard; it does not make lane
  selection decisions. SwitchBoard owns the policy and the selection logic.

- **Not the coding execution layer.** PlatformDeployment does not run agents, edit files, or
  invoke CLIs. OperationsCenter's execution boundary and its backend processes do that.

- **Not the workflow harness.** PlatformDeployment does not define or execute multi-step
  coding workflows. That is Archon's job.

- **Not a provider proxy.** PlatformDeployment does not forward LLM API requests to external
  providers.

---

## Quick Start

```bash
# 1. Copy and edit environment config
cp .env.example .env

# 2. Copy service configs
cp config/switchboard/policy.example.yaml      config/switchboard/policy.yaml
cp config/platformdeployment/endpoints.example.yaml   config/platformdeployment/endpoints.yaml
cp config/platformdeployment/services.example.yaml    config/platformdeployment/services.yaml
cp config/platformdeployment/ports.example.yaml       config/platformdeployment/ports.yaml

# 3. Start the stack
python -m platform_deployment_cli up

# 4. Verify health
python -m platform_deployment_cli health
```

On Windows (PowerShell):

```powershell
./scripts/bootstrap.ps1   # first-time setup
./scripts/up.ps1
./scripts/health.ps1
```

---

## Architecture

```
PlatformDeployment deploys and manages:

  SwitchBoard (:20401)    — execution-lane selector
  Plane (:8080)           — task board (OperationsCenter dependency)
  tiny local models       — served locally for aider_local lane

System flow (see docs/architecture/system/system_overview.md for the full picture):

  OperationsCenter planning → SwitchBoard routing → OperationsCenter execution boundary
                                                     ├── claude_cli   (Claude CLI, OAuth)
                                                     ├── codex_cli    (Codex CLI, subscription)
                                                     └── aider_local  (Aider + PlatformDeployment models)
```

See [`docs/architecture/system/system_overview.md`](docs/architecture/system/system_overview.md) for
the full layered view, component roles, and conceptual flow.

---

## Local Lane: aider_local

PlatformDeployment hosts the `aider_local` execution lane — local Aider execution backed
by tiny local models. This lane runs at zero marginal API cost and is suitable for
lint fixes, simple edits, and documentation tasks.

```bash
# Configure (copy example, set enabled: true, configure model endpoints)
cp config/platformdeployment/local_lane.example.yaml config/platformdeployment/local_lane.yaml
```

Lane management is via the `lane` subcommand — see [CLI Reference → Lane](#lane--aider_local-ai-execution-lane).

For full setup and troubleshooting, see
[`docs/operations/local-lane-setup.md`](docs/operations/local-lane-setup.md).
For the architectural rationale, see
[`docs/architecture/adapters/local-lane.md`](docs/architecture/adapters/local-lane.md).

---

## Cross-Repo Architecture Docs

Public charter material now lives in `ProtocolWarden.github.io`. This repo
keeps deployment-focused architecture and operator material, including:

- [docs/architecture/routing/routing-tuning.md](docs/architecture/routing/routing-tuning.md)
- [docs/architecture/routing/routing-tuning-examples.md](docs/architecture/routing/routing-tuning-examples.md)
- [docs/architecture/contracts/upstream-patch-evaluation.md](docs/architecture/contracts/upstream-patch-evaluation.md)
- [docs/architecture/contracts/upstream-patch-evaluation-examples.md](docs/architecture/contracts/upstream-patch-evaluation-examples.md)

These documents keep routing tuning, adapter-first integration, and any later
upstream patch proposals clearly separated from active runtime behavior.

---

## Health and Status

```bash
# Shell health check (exits 0 = healthy, 1 = unhealthy)
./scripts/health.sh

# Full status summary (compose state + health + resource usage)
./scripts/status.sh

# Python CLI — human-readable
python -m platform_deployment_cli status

# Python CLI — machine-readable JSON
python -m platform_deployment_cli status --json

# Raw health JSON
python -m platform_deployment_cli health --json
```

### Health model

| Status      | Meaning                                                       |
|-------------|---------------------------------------------------------------|
| `healthy`   | All required services reachable and returning HTTP 200        |
| `degraded`  | Required services healthy; one or more optional services down |
| `unhealthy` | At least one required service is unreachable or non-200       |

See [docs/operations/health-model.md](docs/operations/health-model.md) for full semantics and example JSON output.

---

## Endpoint Reference

| Endpoint                                     | Service     | Description                          |
|----------------------------------------------|-------------|--------------------------------------|
| `http://localhost:20401/health`              | SwitchBoard | Health check                         |
| `http://localhost:20401/route`               | SwitchBoard | Canonical `TaskProposal -> LaneDecision` |
| `http://localhost:20401/route-plan`          | SwitchBoard | Primary, fallback, and escalation plan |

All client traffic targets SwitchBoard (`:20401`).

---

## CLI Reference

All operator actions are available through the Python CLI. Scripts in `scripts/` back the CLI
and can still be called directly when needed (e.g. on Windows before Python is available).

```bash
python -m platform_deployment_cli <command>
```

### Stack lifecycle

| Command | What it does |
|---------|--------------|
| `up` | Start the stack in detached mode |
| `down` | Stop and remove containers |
| `restart` | Stop then start the stack |
| `ensure-up` | Start only if not already healthy; no-op if healthy |
| `logs [service]` | Stream compose logs for all services or one (`--tail N`) |
| `health [--json]` | Check health endpoints; exit 0 if all healthy |
| `status [--json]` | Aggregate status summary |

```bash
python -m platform_deployment_cli up
python -m platform_deployment_cli restart
python -m platform_deployment_cli logs
python -m platform_deployment_cli logs switchboard --tail 100
python -m platform_deployment_cli health --json
python -m platform_deployment_cli status
```

### Lane — aider_local AI execution lane

Manages the `aider_local` lane: Ollama serving a local model + aider wired to it.

| Command | What it does |
|---------|--------------|
| `lane start [lane]` | Start local model services |
| `lane stop [lane]` | Stop local model services |
| `lane status [lane]` | Show lane state and model health |
| `lane health [lane]` | Live health check |
| `lane doctor [lane]` | Full pre-flight check (config, binary, Ollama, models) |

```bash
python -m platform_deployment_cli lane status
python -m platform_deployment_cli lane doctor
python -m platform_deployment_cli lane start
```

Lane states: `disabled` → `configured` → `starting` → `ready` | `unhealthy` | `failed`

### Plane — project tracker lifecycle and backup

| Command | What it does |
|---------|--------------|
| `plane up` | Install (if needed) and start Plane |
| `plane down` | Stop Plane containers |
| `plane status` | Check whether Plane is reachable |
| `plane backup` | pg_dump Plane DB → `~/sync/platform/backups/` (timestamped, 10-dump rotation) |
| `plane restore [dump]` | Restore DB from a dump file (latest if omitted); prompts for confirmation |
| `plane list` | List available database dumps with sizes |

```bash
python -m platform_deployment_cli plane up
python -m platform_deployment_cli plane backup
python -m platform_deployment_cli plane list
python -m platform_deployment_cli plane restore
python -m platform_deployment_cli plane restore ~/sync/platform/backups/plane_20260517T143022Z.sql.gz
```

DB credentials are read from `runtime/plane/plane-app/plane.env` (overridable via
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`). Dump destination overridable
via `PLATFORM_BACKUPS_DIR`. Rotation count via `PLANE_BACKUP_KEEP` (default: 10).

### Secrets — synced config files

Manages the four gitignored config files (`plane.env`, `.env`, `policy.yaml`,
`endpoints.yaml`) via `~/sync/platform/config/` as the sync intermediary.

| Command | What it does |
|---------|--------------|
| `secrets backup` | Copy live files from repo → sync dir (flat-named) |
| `secrets setup` | Copy files from sync dir → repo positions |
| `secrets list` | Show what is present in the sync dir |

```bash
python -m platform_deployment_cli secrets backup   # before switching machines or after editing secrets
python -m platform_deployment_cli secrets setup    # on a new machine after ~/sync/ has synced
python -m platform_deployment_cli secrets list
```

Sync dir overridable via `PLATFORM_SECRETS_DIR` (default: `~/sync/platform/config/`).

### Workers — OperationsCenter watcher lifecycle

| Command | What it does |
|---------|--------------|
| `workers start` | Start all OperationsCenter watcher roles |
| `workers stop` | Stop all watcher roles |
| `workers status` | Print watcher role status |
| `workers restart` | Stop then start all watcher roles |

```bash
python -m platform_deployment_cli workers start
python -m platform_deployment_cli workers status
```

OC checkout path defaults to `~/Documents/GitHub/OperationsCenter`; override with
`OPERATIONS_CENTER_ROOT`.

---

## Repository Layout

```
PlatformDeployment/
├── compose/                  Docker Compose files and profiles
│   ├── docker-compose.yml
│   ├── docker-compose.override.example.yml
│   └── profiles/
│       ├── core.yml
│       ├── dev.yml
│       └── observability.yml
├── config/
│   ├── switchboard/          policy, profiles, capabilities config
│   └── platformdeployment/   endpoint registry, service list, port map
├── scripts/                  Bash + PowerShell helper scripts
├── docs/                     Architecture, operations, health model, roadmap
├── tools/platform_deployment_cli/    Canonical Python CLI
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
cp config/platformdeployment/endpoints.example.yaml   config/platformdeployment/endpoints.yaml
cp config/platformdeployment/services.example.yaml    config/platformdeployment/services.yaml
cp config/platformdeployment/ports.example.yaml       config/platformdeployment/ports.yaml
# Optional: local lane configuration
cp config/platformdeployment/local_lane.example.yaml  config/platformdeployment/local_lane.yaml
```

Live config files are excluded from version control (see `.gitignore`). Only `.example.*` variants are committed.

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
| [docs/architecture/system/system_overview.md](docs/architecture/system/system_overview.md) | Cross-repo architecture, component roles, architecture decisions |
| [docs/architecture/contracts/contracts.md](docs/architecture/contracts/contracts.md) | Canonical cross-repo contract models (Phase 3) |
| [docs/architecture/contracts/contracts-examples.md](docs/architecture/contracts/contracts-examples.md) | Example JSON payloads for all contract models |
| [docs/architecture/adapters/local-lane.md](docs/architecture/adapters/local-lane.md) | aider_local lane design and boundaries |
| [docs/architecture/system/repo_responsibility_matrix.md](docs/architecture/system/repo_responsibility_matrix.md) | Per-repo owns/does-not-own matrix |
| [docs/architecture/system/glossary.md](docs/architecture/system/glossary.md) | Canonical terminology |
| [docs/architecture/adr/](docs/architecture/adr/) | Architecture decision records |
| [docs/operations/local-lane-setup.md](docs/operations/local-lane-setup.md) | aider_local lane setup and troubleshooting |
| [docs/operations/runbook.md](docs/operations/runbook.md) | Stack runbook (start, stop, logs, etc.) |
| [docs/operations/health-model.md](docs/operations/health-model.md) | Health semantics, required vs optional, JSON |
| [docs/operations/service-map.md](docs/operations/service-map.md) | Service inventory |
| [docs/operations/port-map.md](docs/operations/port-map.md) | Port assignments |

---

## License

Server Side Public License, Version 1 (SSPL-1.0) — see [LICENSE](LICENSE).
