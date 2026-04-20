# Environments

This document describes how WorkStation is configured differently across development, staging, and production environments.

---

## Development

The default configuration is tuned for local developer machines.

### Key characteristics

- **Log level:** `debug` — verbose output to aid debugging.
- **Hot-reload:** Enable via `docker-compose.override.yml` volume mounts of source code.
- **Mock providers:** 9router can be configured with `NINE_ROUTER_MOCK_PROVIDERS=true` to return stub responses without hitting real provider APIs.
- **Relaxed auth:** The placeholder API key (`sk-dev-placeholder-replace-me`) is acceptable locally; never use it in production.
- **Resource limits:** Minimal CPU/memory constraints (see `compose/profiles/core.yml`).

### Activating the dev profile

```bash
docker compose \
  -f compose/docker-compose.yml \
  -f compose/profiles/core.yml \
  -f compose/profiles/dev.yml \
  up -d
```

### Local .env overrides

Copy `.env.example` to `.env` and set:
```
LOG_LEVEL=debug
```

### Config files

Use the example files as-is for development:
```
config/switchboard/policy.yaml    ← copied from policy.example.yaml
config/9router/.env               ← only real keys needed if hitting live providers
```

---

## Staging

Staging should mirror production as closely as possible while remaining safe to experiment with.

### Key differences from dev

| Concern        | Dev                        | Staging                        |
|----------------|----------------------------|--------------------------------|
| Log level      | debug                      | info                           |
| Auth keys      | placeholder                | Rotated staging keys           |
| Providers      | Mocks or real              | Real providers (staging quotas) |
| Rate limits    | Permissive                 | Production-like limits         |
| TLS            | None (localhost)           | TLS termination at reverse proxy |

### Recommendations

- Run staging behind a reverse proxy (nginx, Caddy, Traefik) that terminates TLS.
- Use secrets management (Docker Secrets, Vault, environment-specific CI secrets) rather than `.env` files.
- Store container logs in a centralised log aggregator.

---

## Production

### Key differences from staging

| Concern           | Staging          | Production                        |
|-------------------|------------------|-----------------------------------|
| Restart policy    | unless-stopped   | always (or managed by orchestrator) |
| Resource limits   | Moderate         | Sized to workload                 |
| Observability     | Optional         | Required (Prometheus + Grafana)   |
| Secrets           | CI secrets       | Dedicated secrets manager         |
| Image tags        | `:latest`        | Pinned digest or semver tag       |
| Backup / DR       | Not required     | Config and state backup required  |

### Production checklist

- [ ] Pin image versions (`switchboard:1.2.3@sha256:...`) — never use `:latest` in production.
- [ ] Replace placeholder API keys with real, scoped keys.
- [ ] Enable TLS termination in front of SwitchBoard.
- [ ] Deploy the observability profile (Prometheus + Grafana).
- [ ] Configure alerting on the Prometheus health metrics.
- [ ] Restrict network access: only SwitchBoard's port should be publicly reachable.
- [ ] Set `LOG_LEVEL=warn` or `error` to reduce log volume.
- [ ] Configure log rotation and retention.
- [ ] Document and test the runbook for restart, rollback, and failover.

---

## Environment Variable Reference

See `.env.example` at the repo root for the full list of variables and their defaults.

| Variable            | Dev default            | Prod recommendation          |
|---------------------|------------------------|------------------------------|
| `PORT_SWITCHBOARD`  | 20401                  | 20401 (behind reverse proxy) |
| `PORT_9ROUTER`      | 20128                  | 20128 (internal only)        |
| `PORT_STATUS`       | 20400                  | 20400 (internal only)        |
| `LOG_LEVEL`         | debug                  | warn                         |
| `NINE_ROUTER_URL`   | http://localhost:20128 | http://ninerouter:20128      |
