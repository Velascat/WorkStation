# =============================================================================
# WorkStation — health.ps1
# Check the /health endpoint of each service and report pass/fail.
# Exit code: 0 if all healthy, 1 if any service is unhealthy or unreachable.
# =============================================================================
#Requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'   # don't stop on failed web requests

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
$EnvFile   = Join-Path $RepoRoot '.env'

# ── Load .env ─────────────────────────────────────────────────────────────────
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
            $key   = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
}

$portSwitchboard = [System.Environment]::GetEnvironmentVariable('PORT_SWITCHBOARD') ?? '20401'
$port9router     = [System.Environment]::GetEnvironmentVariable('PORT_9ROUTER')     ?? '20128'
$portStatus      = [System.Environment]::GetEnvironmentVariable('PORT_STATUS')      ?? '20400'

$timeoutSec = 5
$allOk      = $true

function Check-Health {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        $resp = Invoke-WebRequest -Uri $Url -TimeoutSec $timeoutSec -UseBasicParsing -ErrorAction Stop
        $status = $resp.StatusCode
        $body   = $resp.Content.Substring(0, [Math]::Min(120, $resp.Content.Length))
        Write-Host "  [OK]   $Name  ($Url)  ->  HTTP $status" -ForegroundColor Green
        Write-Host "         $body" -ForegroundColor DarkGray
    } catch {
        Write-Host "  [FAIL] $Name  ($Url)  ->  $($_.Exception.Message)" -ForegroundColor Red
        $script:allOk = $false
    }
}

Write-Host "=== WorkStation: health check ===" -ForegroundColor Cyan
Write-Host ""
Check-Health "SwitchBoard" "http://localhost:$portSwitchboard/health"
Write-Host ""
Check-Health "9router    " "http://localhost:$port9router/health"
Write-Host ""
Check-Health "Status API " "http://localhost:$portStatus/health"
Write-Host ""

if ($allOk) {
    Write-Host "All services healthy." -ForegroundColor Green
    exit 0
} else {
    Write-Host "One or more services are unhealthy or unreachable." -ForegroundColor Red
    exit 1
}
