# PROMEOS — Bootstrap script (PowerShell)
# Creates .venv if absent, activates it, installs dependencies.
# Usage: .\scripts\bootstrap.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"

Write-Host "[1/4] Checking .venv..." -ForegroundColor Cyan
if (-Not (Test-Path (Join-Path $venvPath "Scripts\python.exe"))) {
    Write-Host "  Creating .venv with $(python --version)..." -ForegroundColor Yellow
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to create venv" }
    Write-Host "  .venv created." -ForegroundColor Green
} else {
    Write-Host "  .venv already exists." -ForegroundColor Green
}

Write-Host "[2/4] Activating .venv..." -ForegroundColor Cyan
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
try {
    & $activateScript
} catch {
    Write-Host ""
    Write-Host "ERROR: Cannot activate .venv. Run this first:" -ForegroundColor Red
    Write-Host "  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "[3/4] Upgrading pip + installing dependencies..." -ForegroundColor Cyan
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
& $pythonExe -m pip install -U pip setuptools wheel --quiet
$reqFile = Join-Path $repoRoot "backend\requirements.txt"
if (Test-Path $reqFile) {
    & $pythonExe -m pip install -r $reqFile --quiet
    Write-Host "  Installed from backend/requirements.txt" -ForegroundColor Green
} else {
    Write-Host "  WARNING: backend/requirements.txt not found" -ForegroundColor Yellow
}

Write-Host "[4/4] Verification..." -ForegroundColor Cyan
& $pythonExe -c "import sys; print(f'  Python: {sys.executable}'); print(f'  Version: {sys.version.split()[0]}'); print(f'  Venv active: {sys.prefix != sys.base_prefix}')"

Write-Host ""
Write-Host "OK — .venv is ready. Activate with:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
