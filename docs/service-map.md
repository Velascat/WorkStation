# Service Map

This document lists every service in the WorkStation stack, their roles, ports,
container names, and health endpoints.

9router has been removed from the architecture. See
[`docs/architecture/adr/0001-remove-9router.md`](architecture/adr/0001-remove-9router.md).

---

## Services

| Service | Container Name | Image | Host Port | Container Port | Health Endpoint | Role |
|---------|----------------|-------|-----------|----------------|-----------------|------|
| SwitchBoard | `workstation-switchboard` | `switchboard:latest` | 20401 | 20401 | `http://localhost:20401/health` | Execution-lane selector — classifies tasks, evaluates policy, selects lane |
| Plane | `plane-app-*` | `makeplane/plane-*` | 8080 | 80 | `http://localhost:8080` | Task board, work-state source of truth (ControlPlane dependency) |
| tiny local models | (host process) | — | varies | — | — | Serves models for the `aider_local` coding lane (WorkStation-deployed) |
| Status API | (future) | — | 20400 | 20400 | `http://localhost:20400/health` | Stack-level health aggregation |

---

## Compose Profile Services

These services are only started when specific compose profiles are used.

### Dev Profile (`compose/profiles/dev.yml`)

| Service | Container Name | Host Port(s) | Purpose |
|---------|----------------|--------------|---------|
| Mailpit | `workstation-mailpit` | 1025 (SMTP), 8025 (UI) | Local email capture |

### Observability Profile (`compose/profiles/observability.yml`)

| Service | Container Name | Host Port | Purpose |
|---------|----------------|-----------|---------|
| Prometheus | `workstation-prometheus` | 9090 | Metrics scraping and storage |
| Grafana | `workstation-grafana` | 3000 | Metrics dashboards |

---

## Internal Network

Services in the core stack share the `workstation-platform` Docker bridge network.
Internal DNS resolution uses Docker service names:

| Service | Internal DNS Name | Internal Address |
|---------|-------------------|-----------------|
| SwitchBoard | `switchboard` | `switchboard:20401` |

---

## Startup Dependencies

```
SwitchBoard   (starts independently, no required upstream service)
```

---

## Plane

Plane is a platform dependency managed by WorkStation but **not** included in the
core Docker Compose manifest. It is managed separately because it uses Makeplane's
official release distribution (not a WorkStation-built image).

**Lifecycle script:** `bash scripts/plane.sh {up|down|status}`

**Runtime data:** `runtime/plane/` (gitignored — populated on first startup)

**Config overrides:** copy `config/plane/.env.example` to `config/plane/.env`

Plane runs on a separate Docker Compose stack (downloaded by `scripts/plane.sh`) and
does not share the `workstation-platform` network. ControlPlane connects to it via
`http://localhost:8080` (configurable via `CONTROL_PLANE_PLANE_URL`).

---

## Key API Paths

| Path | Service | Description |
|------|---------|-------------|
| `/health` | SwitchBoard | Service liveness check |
| `/route` | SwitchBoard | Canonical `TaskProposal -> LaneDecision` route selection |
| `/v1/completions` | SwitchBoard | OpenAI-compatible completions |
| `/v1/embeddings` | SwitchBoard | Embedding requests |
| `/admin/decisions/recent` | SwitchBoard | Last N lane-selection decisions |
| `/admin/summary` | SwitchBoard | Aggregated decision stats |
