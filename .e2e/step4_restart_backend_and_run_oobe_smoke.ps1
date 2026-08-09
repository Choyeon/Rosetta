# Step 4 wrapper: kill backend, clean DBs, restart backend, run OOBE smoke
$ErrorActionPreference = "Continue"
$Root = "d:\WebProjects\Rosetta"
$Py = "$Root\.venv\Scripts\python.exe"
$BackendLog = "$Root\.e2e\logs\backend.log"
New-Item -ItemType Directory -Force -Path "$Root\.e2e\logs" | Out-Null

# 1. Kill processes listening on 8000
Write-Host "[1/6] Kill 8000 listeners..."
$ports = @(8000)
foreach ($p in $ports) {
  $xs = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($x in $xs) {
    try { Stop-Process -Id $x -Force -ErrorAction Stop; Write-Host "  killed pid=$x port=$p" }
    catch { Write-Host "  kill failed pid=$x port=$p : $_" }
  }
}
Start-Sleep -Seconds 2

# 2. Clean DB files (including rosetta_config / e2e dbs)
Write-Host "[2/6] Clean DB files..."
$dbFiles = @(
  "$Root\rosetta_config.db",
  "$Root\backend\rosetta_config.db",
  "$Root\rosetta.db",
  "$Root\backend\rosetta.db",
  "$Root\.e2e\rosetta_e2e_api.db",
  "$Root\.e2e\rosetta_e2e_test.db"
)
foreach ($f in $dbFiles) {
  if (Test-Path $f) {
    try { Remove-Item $f -Force -ErrorAction Stop; Write-Host "  deleted $f" }
    catch { Write-Host "  cannot delete $f : $_" }
  }
}
Get-ChildItem "$Root\.e2e" -Filter "*.db" -ErrorAction SilentlyContinue | ForEach-Object {
  try { Remove-Item $_.FullName -Force -ErrorAction Stop; Write-Host "  deleted e2e db: $($_.FullName)" }
  catch { Write-Host "  cannot delete $($_.FullName): $_" }
}

# 3. Restart backend: uvicorn backend.main:app on 127.0.0.1:8000
Write-Host "[3/6] Start backend (uvicorn 127.0.0.1:8000)..."
$env:PYTHONPATH = $Root
$env:HTTP_PROXY = "http://127.0.0.1:7897"
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
$backendJob = Start-Process -FilePath $Py `
  -ArgumentList "-m","uvicorn","backend.main:app","--host","127.0.0.1","--port","8000","--no-server-header","--log-level","warning" `
  -WorkingDirectory $Root `
  -RedirectStandardOutput $BackendLog `
  -RedirectStandardError "$BackendLog.err" `
  -NoNewWindow -PassThru
Write-Host "  backend pid=$($backendJob.Id) log=$BackendLog"

# 4. Wait for /health 200 (timeout 60s)
Write-Host "[4/6] Wait backend /health/ == 200..."
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$healthy = $false
while ($sw.Elapsed.TotalSeconds -lt 60 -and -not $healthy) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health/" -TimeoutSec 4 -UseBasicParsing -ErrorAction Stop
    if ($r.StatusCode -eq 200) { $healthy = $true }
  } catch { Start-Sleep -Milliseconds 600 }
}
$sw.Stop()
if (-not $healthy) { Write-Host "  FATAL: backend not healthy after 60s"; exit 6 }
Write-Host "  backend healthy after $($sw.Elapsed.TotalSeconds.ToString('F1'))s"

# 5. Run Python OOBE smoke test
Write-Host "[5/6] Run OOBE + admin smoke..."
$env:PYTHONPATH = $Root
$env:HTTP_PROXY = $null; $env:HTTPS_PROXY = $null
& $Py "$Root\.e2e\run_oobe_and_admin_smoke.py"
$smokeExit = $LASTEXITCODE
Write-Host "  smoke exit=$smokeExit"
if ($smokeExit -ne 0) {
  Write-Host "--- tail backend.log ---"
  if (Test-Path $BackendLog) { Get-Content $BackendLog -Tail 40 | ForEach-Object { Write-Host "  | $_" } }
  Write-Host "--- tail backend.log.err ---"
  if (Test-Path "$BackendLog.err") { Get-Content "$BackendLog.err" -Tail 40 | ForEach-Object { Write-Host "  | $_" } }
  exit $smokeExit
}
Write-Host "[6/6] DONE. backend pid=$($backendJob.Id). Keep running for follow-up tests."
# 注意：不 kill backend，因为后续 Todo 5/6/7 要继续用。
exit 0
