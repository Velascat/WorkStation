# Operations

Day-to-day operational runbook for the PlatformDeployment stack.

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

1. Edit the live lane policy file (`config/switchboard/policy.yaml`).
2. Restart the affected service:
   ```bash
   docker compose -f compose/docker-compose.yml restart switchboard
   ```
3. Verify health:
   ```bash
   ./scripts/health.sh
   ```

---

## Running Custodian With RepoGraph Boundary Artifacts

Custodian intentionally fails closed when `REPOGRAPH_BOUNDARY_ARTIFACT_FILE` is
missing. PlatformDeployment provides a convenience wrapper that materializes
the boundary artifact through the approved private-manifest export flow,
exports the required environment variable, and then invokes Custodian.

```bash
./scripts/custodian/run_with_boundary.sh \
  --repo-root "$(pwd)" \
  --profile PUBLIC_SAFE
```

If the boundary artifact already exists, pass it directly:

```bash
./scripts/custodian/run_with_boundary.sh \
  --repo-root "$(pwd)" \
  --boundary-artifact /path/to/boundary_disclosure_artifact.json
```

### CI usage

In CI, call the same wrapper and let it materialize a temporary artifact unless
your workflow already has a vetted artifact file:

```bash
./scripts/custodian/run_with_boundary.sh \
  --repo-root "$GITHUB_WORKSPACE" \
  --custodian-command "custodian-multi --repos \"$GITHUB_WORKSPACE\" --fail-on-findings --no-color"
```

### Debugging

Add `--debug` to print safe provenance details and `--keep-artifacts` to retain
the temporary artifact directory for inspection. The wrapper never prints
forbidden private names; if artifact generation fails, fix the
private-manifest export flow rather than Custodian.

---

## Plane (OperationsCenter dependency)

Plane is managed by a separate script, not by `docker-compose.yml`. PlatformDeployment is the canonical owner of this infra.

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

After Plane is running, open `http://localhost:8080` to complete workspace setup (admin account, project, API token). These credentials go in OperationsCenter's config — not in PlatformDeployment.

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
  -v platformdeployment-prometheus-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz /data
```
