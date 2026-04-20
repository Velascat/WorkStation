# Service Map

This document lists every service in the WorkStation stack, their roles, ports, container names, and health endpoints.

---

## Services

| Service       | Container Name              | Image              | Host Port | Container Port | Health Endpoint                        | Role                              |
|---------------|-----------------------------|--------------------|-----------|----------------|----------------------------------------|-----------------------------------|
| SwitchBoard   | `workstation-switchboard`   | `switchboard:latest` | 20401   | 20401          | `http://localhost:20401/health`        | API gateway, policy, auth, rate-limiting |
| 9router       | `workstation-ninerouter`    | `9router:latest`   | 20128     | 20128          | `http://localhost:20128/health`        | Model dispatcher, provider routing |
| Status API    | (future)                    | —                  | 20400     | 20400          | `http://localhost:20400/health`        | Stack-level health aggregation    |

---

## Compose Profile Services

These services are only started when specific compose profiles are used.

### Dev Profile (`compose/profiles/dev.yml`)

| Service   | Container Name         | Host Port(s)        | Purpose                    |
|-----------|------------------------|---------------------|----------------------------|
| Mailpit   | `workstation-mailpit`  | 1025 (SMTP), 8025 (UI) | Local email capture     |

### Observability Profile (`compose/profiles/observability.yml`)

| Service    | Container Name             | Host Port | Purpose                        |
|------------|----------------------------|-----------|--------------------------------|
| Prometheus | `workstation-prometheus`   | 9090      | Metrics scraping and storage   |
| Grafana    | `workstation-grafana`      | 3000      | Metrics dashboards             |

---

## Internal Network

All services share the `workstation-platform` Docker bridge network. Internal DNS resolution uses Docker service names:

| Service     | Internal DNS Name | Internal Address     |
|-------------|-------------------|----------------------|
| SwitchBoard | `switchboard`     | `switchboard:20401`  |
| 9router     | `ninerouter`      | `ninerouter:20128`   |

SwitchBoard uses `http://ninerouter:20128` to reach 9router. This never traverses the host network.

---

## Startup Dependencies

```
9router   (starts first, no dependencies)
    └──> SwitchBoard   (waits for 9router health check to pass)
```

---

## Key API Paths

| Path                      | Service     | Description                         |
|---------------------------|-------------|-------------------------------------|
| `/health`                 | SwitchBoard | Service liveness check              |
| `/v1/chat/completions`    | SwitchBoard | OpenAI-compatible chat endpoint     |
| `/v1/completions`         | SwitchBoard | OpenAI-compatible completions       |
| `/v1/embeddings`          | SwitchBoard | Embedding requests                  |
| `/health`                 | 9router     | Service liveness check              |
| `/route`                  | 9router     | Internal routing (called by SwitchBoard) |
