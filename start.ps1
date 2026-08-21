<#
.SYNOPSIS
  Rosetta Dev Starter - friendly mode (double-click via dev.bat)
.DESCRIPTION
  Opens 2 separate console windows for backend and frontend.
  Keeps the current console as a CONTROLLER:
    - Shows URLs & health
    - Press [Q] to stop services selectively (by recorded PIDs + /T, never global kill)
    - Press [O] to open the home page http://localhost:3000
    - Press [D] to open the FastAPI /docs page

  Parameters:
    -BackendPort      Default 8000
    -BackendHost      Default 127.0.0.1
    -FrontendPort     Default 3000 (Nuxt may auto-shift; check the frontend window)
    -NoFrontend       Only start backend
    -NoBackend        Only start frontend
    -SkipEnvCheck     Skip uv/node/pnpm availability checks
#>
[CmdletBinding()]
param(
    [int]$BackendPort       = 8000,
    [string]$BackendHost    = '127.0.0.1',
    [int]$FrontendPort      = 3000,
    [switch]$NoFrontend,
    [switch]$NoBackend,
    [switch]$SkipEnvCheck
)
$ErrorActionPreference = 'Stop'

# --- Paths & constants -------------------------------------------------------
$RepoRoot    = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $RepoRoot 'frontend'
$RunDir      = Join-Path $RepoRoot '.rosetta_run'
$PidFileBE   = Join-Path $RunDir 'backend.pid'
$PidFileFE   = Join-Path $RunDir 'frontend.pid'

if (-not (Test-Path $RunDir)) { New-Item -ItemType Directory -Path $RunDir -Force | Out-Null }

# --- Helpers -----------------------------------------------------------------
function Write-Line([string]$text, [ConsoleColor]$c = 'Gray') {
    Write-Host ('  ' + $text) -ForegroundColor $c
}
function Write-Section([string]$t, [ConsoleColor]$c = 'Cyan') {
    $bar = '-' * [Math]::Min(72, $t.Length + 6)
    Write-Host ''
    Write-Host ('+ ' + $t) -ForegroundColor $c
    Write-Host ('+' + $bar) -ForegroundColor $c
}
function Test-Cmd([string]$name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

# Resolve a command to a path that cmd.exe can execute directly.
# For tools installed via npm/corepack, Get-Command often returns *.ps1 which cmd.exe
# can NOT run. In those cases we look for a sibling *.cmd / *.bat / *.exe shim.
function Resolve-CmdSafePath([string]$name) {
    $cmd = Get-Command $name -ErrorAction Stop
    $src = $cmd.Source
    if ([string]::IsNullOrEmpty($src)) { throw "Cannot locate command: $name" }
    $ext = [System.IO.Path]::GetExtension($src)
    if ($ext -in @('.exe','.com','.cmd','.bat')) { return $src }

    $dir = [System.IO.Path]::GetDirectoryName($src)
    $basename = [System.IO.Path]::GetFileNameWithoutExtension($src)
    foreach ($altExt in @('.cmd','.bat','.exe')) {
        $candidate = Join-Path $dir ($basename + $altExt)
        if (Test-Path $candidate) { return $candidate }
    }
    # Fallback: if even the ps1-only lives in a known npm/bin dir, try the .cmd shim
    # placed by npm in the same directory. If none, return the original and let
    # cmd try with PATHEXT (usually it fails).
    return $src
}

function Get-PortOwner([int]$port) {
    # Returns [pscustomobject]@{ Port; Pid; ProcessName; Path } or $null
    $conn = $null
    try {
        $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                Where-Object { $_.LocalAddress -in '127.0.0.1','0.0.0.0','::','::1' } |
                Select-Object -First 1
    } catch {}
    if (-not $conn) {
        $lines = netstat -ano 2>$null | Select-String -Pattern 'LISTENING'
        foreach ($ln in $lines) {
            if ($ln -match '\s+(\S+):' + $port + '\s+\S+\s+LISTENING\s+(\d+)') {
                $pidNo = [int]$Matches[2]
                try {
                    $p = Get-Process -Id $pidNo -ErrorAction Stop
                    return [pscustomobject]@{ Port=$port; Pid=$pidNo; ProcessName=$p.ProcessName; Path=($p.Path -as [string]) }
                } catch {
                    return [pscustomobject]@{ Port=$port; Pid=$pidNo; ProcessName='<unknown>'; Path='' }
                }
            }
        }
        return $null
    }
    try {
        $p = Get-Process -Id $conn.OwningProcess -ErrorAction Stop
        return [pscustomobject]@{ Port=$port; Pid=$conn.OwningProcess; ProcessName=$p.ProcessName; Path=($p.Path -as [string]) }
    } catch {
        return [pscustomobject]@{ Port=$port; Pid=$conn.OwningProcess; ProcessName='<unknown>'; Path='' }
    }
}

function Stop-PidGraceful([int]$pid, [string]$who = '') {
    if ($pid -le 0) { return }
    try { $proc = Get-Process -Id $pid -ErrorAction Stop } catch { return }
    if (-not $proc -or $proc.HasExited) { return }
    $tag = if ($who) { '[' + $who + '] ' } else { '' }
    Write-Line ($tag + 'Stopping PID ' + $pid + ' (' + $proc.ProcessName + ') ...') DarkYellow
    try {
        $cmd = 'taskkill /PID ' + $pid + ' /T /F > nul 2>&1'
        & "$env:SystemRoot\System32\cmd.exe" /D /C $cmd | Out-Null
        Start-Sleep -Milliseconds 300
        try {
            $p2 = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($p2 -and -not $p2.HasExited) { $p2.Kill() }
        } catch {}
    } catch {
        try { if (-not $proc.HasExited) { $proc.Kill() } } catch {}
    }
}

function Start-AndCapturePid(
    [string]$WindowTitle,
    [string]$WorkDir,
    [string]$FilePath,
    [string[]]$Args,
    [string]$PidFile,
    [hashtable]$ExtraEnv = @{}
) {
    # We wrap target in cmd.exe /S /K "title X & cd /d WD & command args" so the
    # console window stays open with its native log, and we can taskkill /T the
    # recorded pid to kill the whole tree cleanly.
    #
    # Build a properly quoted argument string
    $sb = New-Object System.Text.StringBuilder
    for ($i = 0; $i -lt $Args.Count; $i++) {
        $a = $Args[$i]
        if ($a -match '\s|"') {
            $esc = $a -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1'
            [void]$sb.Append('"').Append($esc).Append('"')
        } else {
            [void]$sb.Append($a)
        }
        if ($i -lt $Args.Count - 1) { [void]$sb.Append(' ') }
    }
    $argStr = $sb.ToString()

    $wdForTitle = $WorkDir -replace '"', '""'
    $fpForTitle = $FilePath  -replace '"', '""'
    $wtForTitle = $WindowTitle -replace '"', '""'
    $innerCmd = 'title ' + $wtForTitle + ' & cd /d "' + $wdForTitle + '" & "' + $fpForTitle + '" ' + $argStr

    $envRestorer = @{}
    try {
        if ($ExtraEnv -and $ExtraEnv.Count -gt 0) {
            foreach ($k in $ExtraEnv.Keys) {
                $envRestorer[$k] = [Environment]::GetEnvironmentVariable($k, 'Process')
                [Environment]::SetEnvironmentVariable($k, [string]$ExtraEnv[$k], 'Process')
            }
        }
        $proc = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\cmd.exe') `
                    -ArgumentList @('/S','/K', '"' + $innerCmd + '"') `
                    -WorkingDirectory $WorkDir `
                    -PassThru -WindowStyle Normal -ErrorAction Stop
    } finally {
        foreach ($k in $envRestorer.Keys) {
            [Environment]::SetEnvironmentVariable($k, $envRestorer[$k], 'Process')
        }
    }

    try { Set-Content -Path $PidFile -Value $proc.Id.ToString() -Force } catch {}
    Write-Line ('  * started window [' + $WindowTitle + ']  PID=' + $proc.Id + '  WD=' + $WorkDir) DarkGray
    return [pscustomobject]@{ Pid = $proc.Id; Window = $WindowTitle; PidFile = $PidFile }
}

# --- Banner ------------------------------------------------------------------
$Host.UI.RawUI.WindowTitle = 'Rosetta - Dev Controller'
Clear-Host
$pad = 70
Write-Host ('+' + ('=' * $pad) + '+') -ForegroundColor Cyan
Write-Host ('|' + ('  Rosetta Dev  |  Start Backend + Frontend in separate windows').PadRight($pad) + '|') -ForegroundColor Cyan
Write-Host ('+' + ('=' * $pad) + '+') -ForegroundColor Cyan
Write-Host ''

# --- Environment check -------------------------------------------------------
Write-Section 'Environment check'
$envOK = $true
$checks = @(
    @{ n='uv (Python launcher)'; ok=(Test-Cmd 'uv');   hint='Install uv from https://astral.sh then run: uv sync' },
    @{ n='Node.js';              ok=(Test-Cmd 'node'); hint='Install Node.js 20+ and add to PATH' },
    @{ n='pnpm';                 ok=(Test-Cmd 'pnpm'); hint='Run: corepack enable ; corepack prepare pnpm@latest --activate' }
)
foreach ($c in $checks) {
    if ($c.ok) { Write-Line ('OK  ' + $c.n) Green }
    else {
        Write-Line ('MISS ' + $c.n) Red
        Write-Line ('      -> ' + $c.hint) DarkGray
        $envOK = $false
    }
}
if (-not $SkipEnvCheck -and -not $envOK) {
    Write-Host ''
    Write-Line 'Environment incomplete. Startup cancelled.' Red
    Write-Host ''
    Read-Host 'Press ENTER to exit'
    exit 2
}
Write-Line 'Environment OK' DarkGreen

# --- Port-conflict handling: auto-kill only if clearly Rosetta family --------
Write-Section 'Port 8000 / 3000 - conflict detection and clean-up'
$portsToCheck = @()
if (-not $NoBackend)  { $portsToCheck += $BackendPort }
if (-not $NoFrontend) { $portsToCheck += $FrontendPort }
$rosettaProcessNames = @('uv','uvicorn','python','python3','py','pnpm','node','npm','cmd')

foreach ($port in $portsToCheck) {
    $owner = Get-PortOwner $port
    if (-not $owner) {
        Write-Line ('OK  :' + $port + ' is free') Green
        continue
    }
    $isRosetta = $false
    try {
        if (-not [string]::IsNullOrEmpty($owner.Path) -and $owner.Path.StartsWith($RepoRoot, [StringComparison]::OrdinalIgnoreCase)) { $isRosetta = $true }
        if ($owner.ProcessName -in $rosettaProcessNames) { $isRosetta = $true }
        if (Test-Path $PidFileBE) { $bp = (Get-Content $PidFileBE -Raw -ErrorAction SilentlyContinue).Trim(); if ([string]$owner.Pid -eq $bp) { $isRosetta = $true } }
        if (Test-Path $PidFileFE) { $fp = (Get-Content $PidFileFE -Raw -ErrorAction SilentlyContinue).Trim(); if ([string]$owner.Pid -eq $fp) { $isRosetta = $true } }
    } catch {}

    Write-Line ('WARN :' + $port + ' in use by PID=' + $owner.Pid + '  (' + $owner.ProcessName + ')') DarkYellow
    if ($owner.Path) { Write-Line ('       path: ' + $owner.Path) DarkGray }

    if ($isRosetta) {
        Write-Line ('       -> recognized as Rosetta leftover; stopping it') DarkYellow
        Stop-PidGraceful $owner.Pid
        Start-Sleep -Milliseconds 600
        if (Get-PortOwner $port) { Write-Line ('       -> port still occupied; please close the offending program and retry') Red }
        else { Write-Line ('       -> port released') Green }
    } else {
        Write-Line ('       -> NOT a Rosetta process; leaving it alone. If it blocks startup, close that app first.') DarkYellow
    }
}

# --- Clean stale pid files whose process no longer exists --------------------
foreach ($f in @($PidFileBE, $PidFileFE)) {
    if (Test-Path $f) {
        try {
            $pidNo = [int](Get-Content $f -Raw -ErrorAction SilentlyContinue).Trim()
            $exists = Get-Process -Id $pidNo -ErrorAction SilentlyContinue
            if (-not $exists) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
        } catch {}
    }
}

# --- Launch backend + frontend -----------------------------------------------
Write-Section 'Starting services'
$started = New-Object System.Collections.Generic.List[object]

if (-not $NoBackend) {
    $uvPath = Resolve-CmdSafePath 'uv'
    $pyExtraEnv = @{
        PYTHONUNBUFFERED = '1'
        PYTHONPATH       = if ($env:PYTHONPATH) { "$RepoRoot;$env:PYTHONPATH" } else { $RepoRoot }
    }
    $s = Start-AndCapturePid -WindowTitle ('Rosetta Backend :' + $BackendPort) `
            -WorkDir $RepoRoot -FilePath $uvPath `
            -Args @('run','uvicorn','backend.main:app',"--host=$BackendHost","--port=$BackendPort",'--reload') `
            -PidFile $PidFileBE -ExtraEnv $pyExtraEnv
    $s | Add-Member -NotePropertyName Kind -NotePropertyValue 'backend' -Force
    $s | Add-Member -NotePropertyName Url  -NotePropertyValue ('http://' + $BackendHost + ':' + $BackendPort) -Force
    [void]$started.Add($s)
}

Start-Sleep -Milliseconds 400

if (-not $NoFrontend) {
    $pnpmPath = Resolve-CmdSafePath 'pnpm'
    $s = Start-AndCapturePid -WindowTitle ('Rosetta Frontend :' + $FrontendPort) `
            -WorkDir $FrontendDir -FilePath $pnpmPath `
            -Args @('dev') -PidFile $PidFileFE
    $s | Add-Member -NotePropertyName Kind -NotePropertyValue 'frontend' -Force
    $s | Add-Member -NotePropertyName Url  -NotePropertyValue ('http://localhost:' + $FrontendPort) -Force
    [void]$started.Add($s)
}

# --- Friendly info -----------------------------------------------------------
Start-Sleep -Seconds 3
Write-Section 'Services started'
foreach ($s in $started) {
    if ($s.Kind -eq 'backend') {
        Write-Line 'Backend window open:' Cyan
        Write-Line ('     API    : ' + $s.Url + '/api') DarkCyan
        Write-Line ('     Docs   : ' + $s.Url + '/docs') DarkCyan
        Write-Line ('     Health : ' + $s.Url + '/health') DarkCyan
        Write-Line ('     PID    : ' + $s.Pid) DarkGray
    } elseif ($s.Kind -eq 'frontend') {
        Write-Line 'Frontend window open:' Magenta
        Write-Line ('     Home   : ' + $s.Url) DarkMagenta
        Write-Line ('     PID    : ' + $s.Pid) DarkGray
    }
}
Write-Host ''
Write-Line 'Each service prints its own logs in its window.'
Write-Line 'This controller window ONLY handles start/stop - closing it will NOT stop the child windows automatically.' DarkGray
Write-Host ''
Write-Host ('  ' + ('=-' * 28)) -ForegroundColor DarkGray
Write-Line 'Press [Q] to stop all services and exit' Yellow
Write-Line 'Press [O] to open the home page (http://localhost:' + $FrontendPort + ')' Gray
Write-Line 'Press [D] to open backend /docs page' Gray
Write-Host ('  ' + ('=-' * 28)) -ForegroundColor DarkGray

# --- Key loop ----------------------------------------------------------------
:waitLoop while ($true) {
    while ($Host.UI.RawUI.KeyAvailable) {
        $ki = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
        $ch = ([string]$ki.Character).ToLowerInvariant()
        switch ($ch) {
            'q' { break waitLoop }
            'o' { try { Start-Process ('http://localhost:' + $FrontendPort) } catch {} }
            'd' { try { Start-Process ('http://' + $BackendHost + ':' + $BackendPort + '/docs') } catch {} }
        }
    }
    $anyAlive = $false
    foreach ($s in $started) {
        try { $p = Get-Process -Id $s.Pid -ErrorAction SilentlyContinue; if ($p -and -not $p.HasExited) { $anyAlive = $true } } catch {}
    }
    if (-not $anyAlive) {
        Write-Host ''
        Write-Line 'All service windows closed. Exiting controller.' DarkGray
        break waitLoop
    }
    Start-Sleep -Milliseconds 250
}

# --- Cleanup: stop by recorded PIDs ------------------------------------------
Write-Section 'Cleanup'
foreach ($s in @($started)) {
    Stop-PidGraceful $s.Pid $s.Window
}
foreach ($f in @($PidFileBE, $PidFileFE)) {
    if (Test-Path $f) {
        try {
            $pidNo = [int](Get-Content $f -Raw -ErrorAction SilentlyContinue).Trim()
            Stop-PidGraceful $pidNo (Split-Path $f -Leaf)
        } catch {}
    }
}
foreach ($f in @($PidFileBE, $PidFileFE)) { if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue } }

Write-Line 'Cleanup done.' Green
Write-Host ''
Start-Sleep -Milliseconds 500
