<#
.SYNOPSIS
  Stop Rosetta's dev backend (port 8000) and frontend (port 3000) cleanly.
.DESCRIPTION
  Shutdown order:
    1. Read .rosetta_run\backend.pid & frontend.pid -> taskkill /PID /T /F
    2. Port-based fallback: scan :8000 & :3000 listeners. If clearly a Rosetta-family
       process (uv/python/node/pnpm/cmd started from this repo) kill it by PID.
  NEVER does global "taskkill /IM python.exe / node.exe" - it would kill unrelated apps.

  Parameters:
    -BackendPort  Default 8000 (or env:BACKEND_PORT)
    -FrontendPort Default 3000 (or env:FRONTEND_PORT)
    -Force        Stop even when the process path does NOT live under the repo
#>
[CmdletBinding()]
param(
    [int]$BackendPort  = $( if ($env:BACKEND_PORT) { [int]$env:BACKEND_PORT } else { 8000 } ),
    [int]$FrontendPort = $( if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 3000 } ),
    [switch]$Force
)
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunDir   = Join-Path $RepoRoot '.rosetta_run'
$safeNames= @('uv','uvicorn','python','python3','py','pnpm','node','npm','cmd')

Write-Host ''
Write-Host ('=' * 60) -ForegroundColor DarkCyan
Write-Host '  Rosetta Dev - Stop services' -ForegroundColor Cyan
Write-Host ('=' * 60) -ForegroundColor DarkCyan
Write-Host ''

function Write-Line([string]$t, [ConsoleColor]$c = 'Gray') { Write-Host ('  ' + $t) -ForegroundColor $c }

function Get-PortOwner([int]$port) {
    $conn = $null
    try {
        $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                Where-Object { $_.LocalAddress -in '127.0.0.1','0.0.0.0','::','::1' } |
                Select-Object -First 1
    } catch {}
    if (-not $conn) {
        foreach ($ln in (netstat -ano 2>$null | Select-String -Pattern 'LISTENING')) {
            if ($ln -match '\s+(\S+):' + $port + '\s+\S+\s+LISTENING\s+(\d+)') {
                $pidNo = [int]$Matches[2]
                try { $p = Get-Process -Id $pidNo -ErrorAction Stop
                    return [pscustomobject]@{ Pid=$pidNo; Name=$p.ProcessName; Path=($p.Path -as [string]) } }
                catch { return [pscustomobject]@{ Pid=$pidNo; Name='<unknown>'; Path='' } }
            }
        }
        return $null
    }
    try {
        $p = Get-Process -Id $conn.OwningProcess -ErrorAction Stop
        return [pscustomobject]@{ Pid=$conn.OwningProcess; Name=$p.ProcessName; Path=($p.Path -as [string]) }
    } catch {
        return [pscustomobject]@{ Pid=$conn.OwningProcess; Name='<unknown>'; Path='' }
    }
}

function Stop-PidGraceful([int]$pid, [string]$who = '') {
    if ($pid -le 0) { return $false }
    try { $proc = Get-Process -Id $pid -ErrorAction Stop } catch { Write-Line ("PID $pid already gone") DarkGray; return $true }
    if (-not $proc -or $proc.HasExited) { return $true }
    $tag = if ($who) { '[' + $who + '] ' } else { '' }
    Write-Line ($tag + 'Stopping PID ' + $pid + ' (' + $proc.ProcessName + ') ...') DarkYellow
    try {
        $cmd = 'taskkill /PID ' + $pid + ' /T /F > nul 2>&1'
        & "$env:SystemRoot\System32\cmd.exe" /D /C $cmd | Out-Null
        Start-Sleep -Milliseconds 400
        try {
            $p2 = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($p2 -and -not $p2.HasExited) { $p2.Kill() ; Start-Sleep -Milliseconds 200 }
        } catch {}
    } catch {
        try { if (-not $proc.HasExited) { $proc.Kill() } } catch {}
    }
    try {
        $p2 = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($p2 -and -not $p2.HasExited) { Write-Line '  -> still alive, please kill manually' Red; return $false }
    } catch {}
    Write-Line '  -> stopped' Green
    return $true
}

function Is-RosettaFamily($owner) {
    if (-not $owner) { return $false }
    if ($Force) { return $true }
    if (-not [string]::IsNullOrEmpty($owner.Path) -and $owner.Path.StartsWith($RepoRoot, [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($owner.Name -in $safeNames) { return $true }
    return $false
}

# 1. PID-file based stop
Write-Line '(1) Stop based on .rosetta_run\*.pid files' -ForegroundColor Cyan
$anyStopped = $false
foreach ($pair in @(
    @{ File = 'backend.pid'  ; Label = 'Backend'  },
    @{ File = 'frontend.pid' ; Label = 'Frontend' }
)) {
    $f = Join-Path $RunDir $pair.File
    if (-not (Test-Path $f)) { Write-Line ('  - ' + $pair.File + ' not found, skip') DarkGray ; continue }
    $pidText = (Get-Content $f -Raw -ErrorAction SilentlyContinue).Trim()
    if (-not [int]::TryParse($pidText, [ref]([int]0))) {
        Write-Line ('  - ' + $pair.File + ' corrupted (' + $pidText + '), removed') DarkYellow
        Remove-Item $f -Force -ErrorAction SilentlyContinue
        continue
    }
    $pidNo = [int]$pidText
    $ok = Stop-PidGraceful $pidNo $pair.Label
    if ($ok) { $anyStopped = $true }
    Remove-Item $f -Force -ErrorAction SilentlyContinue
}

# 2. Port-based fallback
Write-Host ''
Write-Line ('(2) Port fallback: :' + $BackendPort + ' (Backend)  :' + $FrontendPort + ' (Frontend)') -ForegroundColor Cyan
foreach ($port in @($BackendPort, $FrontendPort)) {
    $owner = Get-PortOwner $port
    if (-not $owner) { Write-Line (':{0,-5} free' -f $port) Green ; continue }
    $label = Switch ($port) { $BackendPort { 'Backend' } $FrontendPort { 'Frontend' } default { 'Port' } }
    Write-Line (':{0,-5} PID={1,-6}  Name={2,-10}' -f $port,$owner.Pid,$owner.Name) Yellow
    if ($owner.Path) { Write-Line ('       Path: ' + $owner.Path) DarkGray }
    if (Is-RosettaFamily $owner) {
        Write-Line '       -> Rosetta-family process, stopping' DarkYellow
        Stop-PidGraceful $owner.Pid $label | Out-Null
        # Verify port released
        Start-Sleep -Milliseconds 300
        if (Get-PortOwner $port) { Write-Line ('       -> :' + $port + ' still occupied, manual check needed') Red }
        else { Write-Line ('       -> :' + $port + ' released') Green }
    } else {
        Write-Line '       -> NOT a Rosetta-family process (use -Force if you really want to kill it)' DarkGray
    }
}

Write-Host ''
Write-Line 'Done.' -ForegroundColor Green
Write-Host ''
Start-Sleep -Milliseconds 300
