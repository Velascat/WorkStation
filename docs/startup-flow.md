# Startup Flow

This document describes the numbered steps to go from a clean checkout to a fully running, healthy WorkStation stack.

---

## Steps

### 1. Bootstrap (first time only)

Copy all example configuration files to their live locations and pull Docker images.

**Linux / macOS:**
```bash
cp .env.example .env
cp config/switchboard/policy.example.yaml   config/switchboard/policy.yaml
cp config/switchboard/profiles.example.yaml config/switchboard/profiles.yaml
cp config/9router/.env.example              config/9router/.env
cp config/workstation/endpoints.example.yaml config/workstation/endpoints.yaml
```

**Windows (PowerShell):**
```powershell
.\scripts\bootstrap.ps1
```

Review `.env` and the config files. At minimum, set any provider API keys in `config/9router/.env`.

---

### 2. Pull images

Ensure Docker has the latest images for both services.

**Linux / macOS:**
```bash
docker compose -f compose/docker-compose.yml pull
```

**Windows:**
```powershell
.\scripts\bootstrap.ps1 -Pull
```

---

### 3. Start the stack

**Linux / macOS:**
```bash
./scripts/up.sh
```

**Windows:**
```powershell
.\scripts\up.ps1
```

Docker Compose starts the services in dependency order:
1. **9router** starts first (no dependencies).
2. **SwitchBoard** starts once 9router passes its health check.

Both services start in detached mode (`-d`). Logs are available via `docker compose logs -f`.

---

### 4. Health check

Verify that both services are accepting requests on their health endpoints.

**Linux / macOS:**
```bash
./scripts/health.sh
```

**Windows:**
```powershell
.\scripts\health.ps1
```

Expected output when all services are healthy:
```
=== WorkStation: health check ===

  [OK]   SwitchBoard  (http://localhost:20401/health)  →  HTTP 200
  [OK]   9router      (http://localhost:20128/health)  →  HTTP 200

All services healthy.
```

If a service is not yet healthy, wait a few seconds and retry — services may still be initialising.

---

### 5. Ready

The stack is ready to accept requests. Send test traffic to SwitchBoard:

```bash
curl -s \
  -H "X-API-Key: sk-dev-placeholder-replace-me" \
  -H "Content-Type: application/json" \
  -d '{"model":"standard","messages":[{"role":"user","content":"Hello"}]}' \
  http://localhost:20401/v1/chat/completions
```

---

## Stopping the Stack

**Linux / macOS:**
```bash
./scripts/down.sh
```

**Windows:**
```powershell
.\scripts\down.ps1
```

---

## Restart

**Windows:**
```powershell
.\scripts\restart.ps1
# or with image pull:
.\scripts\restart.ps1 -Pull
```

**Linux / macOS:**
```bash
./scripts/down.sh && ./scripts/up.sh
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| `[FAIL]` on health check immediately after `up` | Containers still initialising | Wait 10 s and re-run `health.sh` |
| SwitchBoard fails health check, 9router is OK | SwitchBoard config error | Check `docker compose logs workstation-switchboard` |
| 9router fails health check | Missing provider key or bad `.env` | Check `config/9router/.env`, then restart |
| `docker compose` not found | Docker not installed or PATH issue | Install Docker Desktop / Docker Engine |
| Port conflict | Another service using :20401 or :20128 | Update `.env` and restart |
