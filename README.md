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
9router are documented in
[`docs/architecture/system_overview.md`](docs/architecture/system_overview.md).

---

## Services

| Service          | Port | Purpose |
|------------------|------|---------|
| SwitchBoard      | 20401 | Execution-lane selector — classifies tasks, applies routing policy, selects lane |
| Plane            | 8080  | Task board — work state, comments, labels (separate script-managed stack) |
| tiny local models | local | Serves models for the `aider_local` coding lane (WorkStation-deployed) |

SwitchBoard is required for coding lane dispatch. Plane is required for ControlPlane
operation. Tiny model deployment is required for the `aider_local` lane.

## What WorkStation Is Not

- **Not the task-prioritization engine.** WorkStation does not decide what work
  matters next. That is ControlPlane's job.

- **Not the lane selector.** WorkStation deploys SwitchBoard; it does not make lane
  selection decisions. SwitchBoard owns the policy and the selection logic.

- **Not the coding execution layer.** WorkStation does not run agents, edit files, or
  invoke CLIs. kodo and the lane runners do that.

- **Not the workflow harness.** WorkStation does not define or execute multi-step
  coding workflows. That is Archon's job.

- **Not a provider proxy.** WorkStation does not forward LLM API requests to external
  providers. 9router, which served that role, has been removed from the architecture.
  See [`docs/architecture/adr/0001-remove-9router.md`](docs/architecture/adr/0001-remove-9router.md).

---

## Architecture

```
WorkStation deploys and manages:

  SwitchBoard (:20401)    — execution-lane selector
  Plane (:8080)           — task board (ControlPlane dependency)
  tiny local models       — served locally for aider_local lane

System flow (see docs/architecture/system_overview.md for the full picture):

  ControlPlane → SwitchBoard → lane runner
                                 ├── claude_cli   (Claude CLI, OAuth)
                                 ├── codex_cli    (Codex CLI, subscription)
                                 └── aider_local  (Aider + WorkStation models)
```

See [`docs/architecture/system_overview.md`](docs/architecture/system_overview.md) for
the full layered view, component roles, and conceptual flow.

---

## Quick Start

```bash
# 1. Copy and edit environment config
cp .env.example .env

# 2. Copy service configs
cp config/switchboard/policy.example.yaml   config/switchboard/policy.yaml
cp config/switchboard/profiles.example.yaml config/switchboard/profiles.yaml
cp config/9router/.env.example              config/9router/.env
cp config/workstation/endpoints.example.yaml config/workstation/endpoints.yaml
cp config/workstation/services.example.yaml  config/workstation/services.yaml
cp config/workstation/ports.example.yaml     config/workstation/ports.yaml

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

| Endpoint                              | Service     | Description                  |
|---------------------------------------|-------------|------------------------------|
| `http://localhost:20401/health`       | SwitchBoard | Health check                 |
| `http://localhost:20401/v1/chat/completions` | SwitchBoard | Chat completions (OpenAI-compatible) |
| `http://localhost:20401/v1/completions`     | SwitchBoard | Text completions             |
| `http://localhost:20401/v1/embeddings`      | SwitchBoard | Embeddings                   |
| `http://localhost:20128/health`       | 9router     | Health check                 |

All client traffic should target SwitchBoard (`:20401`). Direct access to 9router (`:20128`) is for internal use and debugging only.

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
./scripts/logs.sh ninerouter 100   # last 100 lines
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
│   ├── 9router/              environment config
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
cp config/switchboard/policy.example.yaml   config/switchboard/policy.yaml
cp config/switchboard/profiles.example.yaml config/switchboard/profiles.yaml
cp config/switchboard/capabilities.example.yaml config/switchboard/capabilities.yaml
cp config/9router/.env.example              config/9router/.env
cp config/workstation/endpoints.example.yaml config/workstation/endpoints.yaml
cp config/workstation/services.example.yaml  config/workstation/services.yaml
cp config/workstation/ports.example.yaml     config/workstation/ports.yaml
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

| Document                                      | What it covers                               |
|-----------------------------------------------|----------------------------------------------|
| [docs/architecture.md](docs/architecture.md)  | Full layer diagram and responsibilities      |
| [docs/operations.md](docs/operations.md)      | Day-to-day runbook (start, stop, logs, etc.) |
| [docs/health-model.md](docs/health-model.md)  | Health semantics, required vs optional, JSON |
| [docs/roadmap.md](docs/roadmap.md)            | Phase 1 goals and future directions          |
| [docs/service-map.md](docs/service-map.md)    | Service inventory                            |
| [docs/port-map.md](docs/port-map.md)          | Port assignments                             |

---

## License

MIT — see [LICENSE](LICENSE).
