# =============================================================================
# WorkStation — down.ps1
# Stop and remove all stack containers.
# =============================================================================
#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $RepoRoot 'compose\docker-compose.yml'

Write-Host "=== WorkStation: stopping stack ===" -ForegroundColor Cyan

docker compose `
    --file $ComposeFile `
    down --remove-orphans

if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose down failed (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "=== Stack stopped. ===" -ForegroundColor Green
