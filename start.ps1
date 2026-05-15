param([switch]$NoPause)

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host ""
Write-Host "  TallyInsights — Starting..." -ForegroundColor Cyan
Write-Host ""

# ── Launch backend silently ────────────────────────────────────────────────────
$backendArgs = "/c cd /d `"$rootDir\backend`" && .venv\Scripts\activate.bat && python desktop_entry.py"
$backend = Start-Process -FilePath "cmd.exe" -ArgumentList $backendArgs -WindowStyle Hidden -PassThru

# ── Launch Vite dev server silently ───────────────────────────────────────────
$frontendArgs = "/c cd /d `"$rootDir\frontend`" && npm run dev"
$frontend = Start-Process -FilePath "cmd.exe" -ArgumentList $frontendArgs -WindowStyle Hidden -PassThru

# ── Wait for Vite to respond (up to 30 s) ─────────────────────────────────────
Write-Host "  Waiting for services to be ready..." -ForegroundColor DarkGray
$maxWait = 30
$waited  = 0
$ready   = $false
while (-not $ready -and $waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        $ready = $true
    } catch {}
}

if (-not $ready) {
    Write-Host ""
    Write-Host "  ERROR: Frontend failed to start within $maxWait seconds." -ForegroundColor Red
    Write-Host "  Make sure Node.js is installed and 'npm install' has been run in the frontend folder." -ForegroundColor Yellow
    $backend  | Stop-Process -Force -ErrorAction SilentlyContinue
    $frontend | Stop-Process -Force -ErrorAction SilentlyContinue
    if (-not $NoPause) { Read-Host "`n  Press Enter to exit" }
    exit 1
}

Write-Host "  Launching app..." -ForegroundColor Green
Write-Host ""

# ── Run Electron (blocks until the window is closed) ─────────────────────────
Push-Location $rootDir
& npx electron .
Pop-Location

# ── Cleanup hidden processes when Electron exits ──────────────────────────────
$backend  | Stop-Process -Force -ErrorAction SilentlyContinue
$frontend | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill any child Python/Node processes spawned by the above
Get-WmiObject Win32_Process | Where-Object {
    $_.ParentProcessId -eq $backend.Id -or $_.ParentProcessId -eq $frontend.Id
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
