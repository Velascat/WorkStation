# =============================================================================
# WorkStation — up.ps1
# Start the full stack in detached mode and print service status.
# =============================================================================
#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot   = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $RepoRoot 'compose\docker-compose.yml'
$EnvFile     = Join-Path $RepoRoot '.env'

# ── Load .env if present ──────────────────────────────────────────────────────
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
            $key   = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
} else {
    Write-Warning ".env not found — using defaults. Run: Copy-Item .env.example .env"
}

Write-Host "=== WorkStation: starting stack ===" -ForegroundColor Cyan
Write-Host "Compose file: $ComposeFile"
Write-Host ""

docker compose `
    --file $ComposeFile `
    --env-file $EnvFile `
    up --detach --remove-orphans

if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up failed (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=== Stack started. Current service status: ===" -ForegroundColor Green
docker compose --file $ComposeFile ps

Write-Host ""
Write-Host "Tip: run .\scripts\health.ps1 to verify service health." -ForegroundColor DarkGray
