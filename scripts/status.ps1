# =============================================================================
# WorkStation — status.ps1
# Full status summary: Docker Compose service state + health checks.
# =============================================================================
#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $RepoRoot 'compose\docker-compose.yml'

Write-Host "=== WorkStation: status ===" -ForegroundColor Cyan
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ' -AsUTC)"
Write-Host ""

Write-Host "-- Docker Compose service state --" -ForegroundColor DarkGray
try {
    docker compose --file $ComposeFile ps
} catch {
    Write-Host "  (could not reach Docker daemon or no containers running)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "-- HTTP health checks --" -ForegroundColor DarkGray
& "$ScriptDir\health.ps1"

Write-Host ""
Write-Host "-- Container resource usage --" -ForegroundColor DarkGray
try {
    docker stats --no-stream workstation-switchboard
} catch {
    Write-Host "  (containers not running)" -ForegroundColor Yellow
}
