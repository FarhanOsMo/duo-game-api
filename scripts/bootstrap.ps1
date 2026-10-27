# One-command setup for Windows PowerShell:
# checks prerequisites, creates .env from the template, starts the stack and
# smoke-tests it. Safe to run repeatedly: every step is idempotent.
# Usage (from the repo root):  powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Fail($message) {
    Write-Host "ERROR: $message" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker is not installed (https://docs.docker.com/get-docker/)"
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker Compose v2 is required ('docker compose')" }
docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker is installed but not running; start Docker Desktop" }

$python = $null
foreach ($candidate in @("python", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) { $python = $candidate; break }
}
if (-not $python) { Fail "Python 3.12+ is required for the smoke test" }

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example"
} else {
    Write-Host ".env already exists; leaving it unchanged"
}

$sha = git rev-parse --short HEAD 2>$null
if ($LASTEXITCODE -ne 0 -or -not $sha) { $sha = "unknown" }
$env:GIT_SHA = $sha

docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Fail "docker compose up failed" }

& $python scripts/smoke_test.py --timeout 90
if ($LASTEXITCODE -ne 0) { Fail "smoke test failed; see output above" }

Write-Host ""
Write-Host "Stack is up:"
Write-Host "  API         http://localhost:8000/docs"
Write-Host "  Prometheus  http://localhost:9090"
Write-Host "  Grafana     http://localhost:3000   (login from .env: GRAFANA_ADMIN_USER / GRAFANA_ADMIN_PASSWORD)"
Write-Host "Stop it with: docker compose down"
