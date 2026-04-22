# =============================================================================
# WorkStation — logs.ps1
# Stream Docker Compose logs for all (or a specific) service.
# =============================================================================
#Requires -Version 5.1
[CmdletBinding()]
param(
    # Optional: name of a specific service to tail.
    [string]$Service = "",

    # Number of tail lines to start from (default: 50).
    [int]$Tail = 50
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Split-Path -Parent $ScriptDir
$ComposeFile = Join-Path $RepoRoot 'compose\docker-compose.yml'

Write-Host "=== WorkStation: streaming logs (Ctrl+C to stop) ===" -ForegroundColor Cyan
if ($Service) {
    Write-Host "Service: $Service" -ForegroundColor DarkGray
}
Write-Host ""

$baseArgs = @('compose', '--file', $ComposeFile, 'logs', '--follow', "--tail=$Tail")

if ($Service) {
    $baseArgs += $Service
}

& docker @baseArgs
