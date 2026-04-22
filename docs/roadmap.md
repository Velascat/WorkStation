# Roadmap

---

## Phase 1 — Current (Foundation)

The goals for Phase 1 are to have a reliable, reproducible local stack that any developer can spin up in a single command and operate with confidence.

**Done / in scope:**

- Docker Compose orchestration for the selector stack.
- `scripts/` — `up`, `down`, `restart`, `health`, `status`, `logs` for both Bash and PowerShell.
- `workstation_cli` Python CLI with `up`, `down`, `health`, `status`, and `status --json`.
- Endpoint registry (`config/workstation/endpoints.yaml`) as the single source of truth for service URLs.
- Service registry (`config/workstation/services.yaml`) declaring required vs optional services.
- Port map (`config/workstation/ports.yaml`) as the canonical port reference.
- Health model with `healthy` / `degraded` / `unhealthy` semantics tied to the required flag.
- Example config files for all services (copy-to-activate pattern, never committed live).
- Smoke tests that skip gracefully when the stack is not running.
- Unit tests for config parsing, health logic, and status aggregation.
- Architecture, operations, health-model, and service-map documentation.

---

## Later — Optional Improvements

These are not committed to and have no timeline. They represent directions that may become useful as the stack grows.

### Observability

- Prometheus metrics scraping for SwitchBoard and local execution-lane services.
- Grafana dashboards pre-configured in the `observability` compose profile.
- Structured JSON logging with correlation IDs across service hops.

### Developer Experience

- `workstation_cli logs` sub-command as a Python alternative to `scripts/logs.sh`.
- `workstation_cli restart` sub-command.
- Shell completion for `workstation_cli` (bash, zsh, fish).
- `--watch` / poll mode for `workstation_cli status`.

### Configuration

- Config validation on startup (schema check for YAML files before containers start).
- Secret management integration (e.g. read API keys from a secrets store rather than `.env`).
- Hot-reload of SwitchBoard policy without full restart.

### Testing

- Integration tests that run against a fully containerised stack in CI.
- Contract tests verifying `TaskProposal -> LaneDecision` and local stack health semantics.
- Load / latency benchmarks for the routing path.

### Deployment

- Kubernetes manifests (Helm chart or plain YAML) for teams that want to run the stack on a shared cluster.
- CI image build and publish pipeline for SwitchBoard and stack support images.
