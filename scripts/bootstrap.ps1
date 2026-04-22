# =============================================================================
# WorkStation — bootstrap.ps1
# First-time setup: copy example config files and pull Docker images.
# Safe to run multiple times — existing files are never overwritten.
# =============================================================================
#Requires -Version 5.1
[CmdletBinding()]
param(
    # Pass -Pull to pull/refresh images even if they already exist locally.
    [switch]$Pull
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $RepoRoot 'compose\docker-compose.yml'

Write-Host "=== WorkStation: bootstrap ===" -ForegroundColor Cyan
Write-Host ""

# ── Helper: copy example file if destination does not exist ───────────────────
function Copy-IfMissing {
    param([string]$Source, [string]$Destination)
    if (Test-Path $Destination) {
        Write-Host "  [skip]  $Destination  (already exists)" -ForegroundColor DarkGray
    } else {
        Copy-Item -Path $Source -Destination $Destination
        Write-Host "  [copy]  $Destination" -ForegroundColor Green
    }
}

# ── Step 1: copy example env / config files ───────────────────────────────────
Write-Host "Step 1  Copying example configuration files..." -ForegroundColor DarkGray
Write-Host ""

Copy-IfMissing `
    (Join-Path $RepoRoot '.env.example') `
    (Join-Path $RepoRoot '.env')

Copy-IfMissing `
    (Join-Path $RepoRoot 'config\switchboard\policy.example.yaml') `
    (Join-Path $RepoRoot 'config\switchboard\policy.yaml')

Copy-IfMissing `
    (Join-Path $RepoRoot 'config\workstation\endpoints.example.yaml') `
    (Join-Path $RepoRoot 'config\workstation\endpoints.yaml')

# ── Step 2: docker compose pull ───────────────────────────────────────────────
Write-Host ""
Write-Host "Step 2  Pulling Docker images..." -ForegroundColor DarkGray
Write-Host ""

$pullArgs = @('compose', '--file', $ComposeFile, 'pull')
if (-not $Pull) {
    $pullArgs += '--quiet'
}

& docker @pullArgs

if ($LASTEXITCODE -ne 0) {
    Write-Warning "docker compose pull exited with code $LASTEXITCODE. Images may not be available yet."
} else {
    Write-Host ""
    Write-Host "Images pulled successfully." -ForegroundColor Green
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Bootstrap complete." -ForegroundColor Cyan
Write-Host "Next step: review .env, then run .\scripts\up.ps1" -ForegroundColor DarkGray
