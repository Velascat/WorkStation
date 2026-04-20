# Health Model

This document describes how WorkStation determines and reports the health of the stack.

---

## Status Values

| Status      | Meaning                                                                 |
|-------------|-------------------------------------------------------------------------|
| `healthy`   | All **required** services are reachable and returning HTTP 200.         |
| `degraded`  | All required services are healthy, but one or more optional services are not. |
| `unhealthy` | At least one **required** service is unreachable or returning a non-200 response. |

### Key rules

- A service is **required** when `required: true` is set in `config/workstation/services.yaml`.
- A service is **optional** when `required: false` (or the field is absent).
- If there are no services at all, the platform status is `unhealthy`.

---

## Required vs Optional Services

The current stack defines two required services:

| Service     | Required | Port  |
|-------------|----------|-------|
| SwitchBoard | yes      | 20401 |
| 9router     | yes      | 20128 |

Optional services (e.g. observability stack, metrics exporters) can fail without degrading the overall status to `unhealthy`. They will cause a `degraded` status instead, which signals that something is wrong without blocking normal operation.

---

## Health Check Mechanics

Each service is probed by sending a `GET` request to its `/health` endpoint. A result is considered healthy when:

- The TCP connection succeeds (no connection refused / timeout).
- The HTTP response status code is `200`.

Timeouts default to 3 s (connect) and 10 s (read). These can be overridden per-service in `config/workstation/endpoints.yaml`.

---

## Example JSON Output

The `workstation_cli status --json` command returns a JSON object with this shape:

```json
{
  "platform": "workstation",
  "status": "healthy",
  "timestamp": "2026-04-20T12:00:00Z",
  "services": {
    "switchboard": {
      "status": "healthy",
      "base_url": "http://localhost:20401",
      "health_url": "http://localhost:20401/health"
    },
    "9router": {
      "status": "healthy",
      "base_url": "http://localhost:20128",
      "health_url": "http://localhost:20128/health"
    }
  }
}
```

### Degraded example

```json
{
  "platform": "workstation",
  "status": "degraded",
  "timestamp": "2026-04-20T12:00:00Z",
  "services": {
    "switchboard": {
      "status": "healthy",
      "base_url": "http://localhost:20401",
      "health_url": "http://localhost:20401/health"
    },
    "9router": {
      "status": "healthy",
      "base_url": "http://localhost:20128",
      "health_url": "http://localhost:20128/health"
    },
    "metrics": {
      "status": "unhealthy",
      "base_url": "http://localhost:9090",
      "health_url": "http://localhost:9090/health"
    }
  }
}
```

In this example `metrics` is an optional service, so the platform reports `degraded` rather than `unhealthy`.

### Unhealthy example

```json
{
  "platform": "workstation",
  "status": "unhealthy",
  "timestamp": "2026-04-20T12:00:00Z",
  "services": {
    "switchboard": {
      "status": "unhealthy",
      "base_url": "http://localhost:20401",
      "health_url": "http://localhost:20401/health"
    },
    "9router": {
      "status": "healthy",
      "base_url": "http://localhost:20128",
      "health_url": "http://localhost:20128/health"
    }
  }
}
```

`switchboard` is required, so any failure there immediately makes the platform `unhealthy`.

---

## CLI Commands

```bash
# Human-readable summary
python -m workstation_cli status

# Machine-readable JSON
python -m workstation_cli status --json

# Raw health check output
python -m workstation_cli health

# Health as JSON
python -m workstation_cli health --json
```

See also: `scripts/health.sh` and `scripts/status.sh` for shell-based equivalents.
