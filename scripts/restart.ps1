# =============================================================================
# WorkStation — restart.ps1
# Tear down the stack, then bring it back up.
# =============================================================================
#Requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Pull   # Pass -Pull to docker-pull images before restarting.
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== WorkStation: restarting stack ===" -ForegroundColor Cyan
Write-Host ""

# ── Down ──────────────────────────────────────────────────────────────────────
Write-Host "Step 1/2  Stopping..." -ForegroundColor DarkGray
& "$ScriptDir\down.ps1"

# ── Optional pull ─────────────────────────────────────────────────────────────
if ($Pull) {
    Write-Host ""
    Write-Host "Pulling latest images..." -ForegroundColor DarkGray
    $RepoRoot    = Split-Path -Parent $ScriptDir
    $ComposeFile = Join-Path $RepoRoot 'compose\docker-compose.yml'
    docker compose --file $ComposeFile pull
}

Write-Host ""

# ── Up ────────────────────────────────────────────────────────────────────────
Write-Host "Step 2/2  Starting..." -ForegroundColor DarkGray
& "$ScriptDir\up.ps1"
