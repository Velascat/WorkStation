# Operations

Day-to-day operational runbook for the WorkStation stack.

---

## Starting the Stack

**Linux / macOS:**
```bash
./scripts/up.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\up.ps1
```

This runs `docker compose up -d --remove-orphans` against `compose/docker-compose.yml` and prints the service table on completion.

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

Containers are stopped and removed. Volumes are preserved.

To also remove named volumes (destroys persisted data):
```bash
docker compose -f compose/docker-compose.yml down --volumes
```

---

## Restarting the Stack

**Linux / macOS:**
```bash
./scripts/restart.sh
```

**Windows:**
```powershell
.\scripts\restart.ps1
# Pull latest images first:
.\scripts\restart.ps1 -Pull
```

---

## Health Checks

**Linux / macOS:**
```bash
./scripts/health.sh
```

**Windows:**
```powershell
.\scripts\health.ps1
```

Both scripts exit with code `0` if all services return HTTP 200, or `1` if any service is unhealthy.

Manual check via curl:
```bash
curl http://localhost:20401/health   # SwitchBoard
```

---

## Full Status Summary

Combines Docker Compose service state, health checks, and resource usage:

**Linux / macOS:**
```bash
./scripts/status.sh
```

**Windows:**
```powershell
.\scripts\status.ps1
```

---

## Viewing Logs

**Linux / macOS:**
```bash
# All services
./scripts/logs.sh

# Specific service
./scripts/logs.sh switchboard

# Last 100 lines for a service
./scripts/logs.sh switchboard 100
```

**Windows:**
```powershell
.\scripts\logs.ps1
.\scripts\logs.ps1 -Service switchboard
```

Or directly via docker compose:
```bash
docker compose -f compose/docker-compose.yml logs -f
docker compose -f compose/docker-compose.yml logs -f switchboard
```

---

## Updating Images

Pull the latest images without restarting:
```bash
docker compose -f compose/docker-compose.yml pull
```

Then restart to apply:
```bash
./scripts/down.sh && ./scripts/up.sh
```

---

## Updating Configuration

1. Edit the live config file (e.g. `config/switchboard/policy.yaml`).
2. Restart the affected service:
   ```bash
   docker compose -f compose/docker-compose.yml restart switchboard
   ```
3. Verify health:
   ```bash
   ./scripts/health.sh
   ```

---

## Plane (ControlPlane dependency)

Plane is managed by a separate script, not by `docker-compose.yml`. WorkStation is the canonical owner of this infra.

```bash
# Start Plane (installs on first run)
bash scripts/plane.sh up

# Stop Plane
bash scripts/plane.sh down

# Check reachability
bash scripts/plane.sh status
```

Runtime data is stored in `runtime/plane/` (gitignored). On first run, `scripts/plane.sh up` downloads Plane's official setup script from GitHub releases, creates `runtime/plane/plane-app/` with the docker-compose manifest and environment file, and starts all Plane containers.

To configure the port or version before first startup, copy `config/plane/.env.example` to `config/plane/.env` and edit.

After Plane is running, open `http://localhost:8080` to complete workspace setup (admin account, project, API token). These credentials go in ControlPlane's config — not in WorkStation.

---

## Common Issues

### Port already in use

```
Error: bind: address already in use
```

Find the conflicting process:
```bash
lsof -i :20401
```

Either stop the conflicting process or change the host port in `.env`.

### Container exits immediately

Check logs for startup errors:
```bash
docker compose -f compose/docker-compose.yml logs switchboard
```

### Stale containers from previous sessions

```bash
docker compose -f compose/docker-compose.yml down --remove-orphans
./scripts/up.sh
```

---

## Backup

The stack is stateless by default (no persistent volumes in the core profile). Configuration files under `config/` should be kept in version control or backed up separately. If you add services with volumes (e.g. the observability profile), back up those volumes:

```bash
docker run --rm \
  -v workstation-prometheus-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz /data
```
