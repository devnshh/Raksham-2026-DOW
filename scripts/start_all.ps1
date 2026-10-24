# Satark Backend Launcher: Model Service + Risk API
# Starts Model Service (port 8001), waits for health, then launches Risk API (port 8000).

$ErrorActionPreference = "Continue"

# Shared secret between the two services, and the analyst key for /v1/cases, /v1/payees, /internal.
# Never hard-coded: use the env value if set, otherwise generate one for this run.
$MODEL_SERVICE_KEY = if ($env:MODEL_SERVICE_KEY) { $env:MODEL_SERVICE_KEY } else { [guid]::NewGuid().ToString("N") }
$env:MODEL_SERVICE_KEY = $MODEL_SERVICE_KEY
if (-not $env:SATARK_ANALYST_KEY) { $env:SATARK_ANALYST_KEY = [guid]::NewGuid().ToString("N") }
Write-Host "Analyst API key (X-API-Key): $env:SATARK_ANALYST_KEY" -ForegroundColor Magenta

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   SATARK Multi-Service Launcher (RAKSHAM Hackathon)      " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

# 1. Start Model Service (Port 8001) if not already active
$port8001 = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if (-not $port8001) {
    Write-Host "[1/3] Starting Satark Model Service on port 8001..." -ForegroundColor Cyan
    Start-Process python -ArgumentList "-m uvicorn model_service.main:app --host 127.0.0.1 --port 8001"
} else {
    Write-Host "[1/3] Port 8001 is already listening. Skipping Model Service launch." -ForegroundColor Yellow
}

# 2. Poll GET /health until 200 OK
Write-Host "[2/3] Waiting for Model Service health on http://127.0.0.1:8001/health..." -ForegroundColor Cyan
$healthy = $false
$maxAttempts = 30
$attempt = 0

while (-not $healthy -and $attempt -lt $maxAttempts) {
    $attempt++
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($resp.status -eq "ok" -or $resp.model_loaded -eq $true) {
            $healthy = $true
            Write-Host "      Model Service is ready and verified (Attempt $attempt)!" -ForegroundColor Green
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $healthy) {
    Write-Host "      Warning: Model Service did not respond with 200 within 15s. Continuing..." -ForegroundColor Yellow
}

# 3. Start Risk API (Port 8000) if not already active
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $port8000) {
    Write-Host "[3/3] Starting Satark Risk API on port 8000..." -ForegroundColor Cyan
    $env:MODEL_SERVICE_URL = "http://127.0.0.1:8001"
    $env:MODEL_SERVICE_KEY = $MODEL_SERVICE_KEY
    python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
} else {
    Write-Host "[3/3] Port 8000 is already listening. Skipping Risk API launch." -ForegroundColor Yellow
}
