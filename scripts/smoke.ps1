$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    docker compose up -d
    alembic upgrade head
    $api = Start-Process -FilePath python -ArgumentList "-m", "uvicorn", "apps.api.src.main:app", "--host", "127.0.0.1", "--port", "8000" -PassThru -WindowStyle Hidden
    try {
        $deadline = (Get-Date).AddSeconds(30)
        do {
            Start-Sleep -Milliseconds 500
            try { $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 } catch { $health = $null }
        } until ($health -or (Get-Date) -gt $deadline)
        if (-not $health -or -not $health.body.ok) { throw "Health smoke test failed" }
        Write-Host "Backend smoke test: PASS"
    } finally {
        if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
    }
} finally {
    Pop-Location
}
