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

**Windows:**
```powershell
.\scripts\restart.ps1
# Pull latest images first:
.\scripts\restart.ps1 -Pull
```

**Linux / macOS:**
```bash
./scripts/down.sh && ./scripts/up.sh
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
curl http://localhost:20128/health   # 9router
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

Stream all service logs:
```bash
docker compose -f compose/docker-compose.yml logs -f
```

Stream logs for a single service:
```bash
docker compose -f compose/docker-compose.yml logs -f switchboard
docker compose -f compose/docker-compose.yml logs -f ninerouter
```

**Windows:**
```powershell
.\scripts\logs.ps1
.\scripts\logs.ps1 -Service switchboard
.\scripts\logs.ps1 -Service ninerouter -Tail 100
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

## Scaling (Advanced)

To run multiple replicas of 9router (requires a load-balancer in front):
```bash
docker compose -f compose/docker-compose.yml up -d --scale ninerouter=3
```

Note: SwitchBoard's `NINE_ROUTER_URL` must point to the load-balancer, not directly to a single container.

---

## Common Issues

### Port already in use

```
Error: bind: address already in use
```

Find the conflicting process:
```bash
lsof -i :20401
lsof -i :20128
```

Either stop the conflicting process or change the host port in `.env`.

### Container exits immediately

Check logs for startup errors:
```bash
docker compose -f compose/docker-compose.yml logs switchboard
docker compose -f compose/docker-compose.yml logs ninerouter
```

### SwitchBoard cannot reach 9router

Verify 9router is running:
```bash
docker compose -f compose/docker-compose.yml ps
```

Check that both containers are on the `workstation-platform` network:
```bash
docker network inspect workstation-platform
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
