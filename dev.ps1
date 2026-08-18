<#
.SYNOPSIS
  Rosetta 本地开发启动脚本：并发启动 FastAPI 后端 (:8000) 与 Nuxt 4 前端 (:3000)
.DESCRIPTION
  用法（在项目根目录执行）:
    .\dev.ps1                         # 同时启动前后端
    .\dev.ps1 -NoFrontend             # 只启后端
    .\dev.ps1 -NoBackend              # 只启前端
    .\dev.ps1 -BackendPort 8080       # 换后端端口 (还需要同步修改 frontend 对应 env)

  特性:
    · 日志前缀区分颜色 [backend] Cyan / [frontend] Magenta
    · 每条子进程的 stdout/stderr 都在原控制台用前缀合并输出
    · Ctrl+C / 任意子进程退出 → finally 级联 taskkill /T /F 清理整棵子进程树
    · 启动前探测端口占用，避免因残留进程导致启动失败
#>
[CmdletBinding()]
param(
    [string]$BackendHost = '127.0.0.1',
    [int]$BackendPort  = 8000,
    [switch]$NoFrontend,
    [switch]$NoBackend,
    [int]$TestAutoStopAfter = 0  # 调试用：进入守护循环 N 秒后自动退出（触发 finally 清理）
)
$ErrorActionPreference = 'Stop'

# ── 路径 / 环境 ──────────────────────────────────────────────────────────────
$RepoRoot    = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $RepoRoot 'frontend'
$BackendDir  = $RepoRoot

$TmpPrefix = "rosetta_dev_$([DateTime]::Now.ToString('yyyyMMdd_HHmmss'))_$PID"

# ── 工具函数 ─────────────────────────────────────────────────────────────────
function Test-PortListening {
    param(
        [string]$HostIp = '127.0.0.1',
        [int]$Port,
        [int]$TimeoutMs = 400
    )
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostIp, $Port, $null, $null)
        if ($async.AsyncWaitHandle.WaitOne($TimeoutMs, $false) -and $client.Connected) { return $true }
    } finally {
        try { $client.Close() } catch {}
    }
    return $false
}

function Write-TaggedLine {
    param(
        [Parameter(Mandatory)][string]$Tag,
        [Parameter(Mandatory)][ConsoleColor]$Color,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text,
        [ConsoleColor]$TextColor = 'Gray'
    )
    if ([string]::IsNullOrWhiteSpace($Text)) { return }
    Write-Host '[' -NoNewline
    Write-Host $Tag -ForegroundColor $Color -NoNewline
    Write-Host '] ' -NoNewline
    Write-Host $Text -ForegroundColor $TextColor
}

function Test-CommandExists([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

# 把 cmd / bat / ps1 / exe 统一包装成 Start-Process 能正确带重定向启动的形式
function Resolve-Callable([string]$Name) {
    if (Test-CommandExists $Name) {
        $cmd = Get-Command $Name -ErrorAction Stop
        $src = $cmd.Source
        if ([string]::IsNullOrEmpty($src)) { throw "无法定位命令 $Name 的磁盘路径" }
        $ext = [System.IO.Path]::GetExtension($src)
        # PowerShell 脚本 → pwsh -File (如果 pwsh 不可用则降级 Windows PowerShell)
        if ($ext -ieq '.ps1') {
            $pwsh = if (Test-CommandExists 'pwsh') { (Get-Command pwsh).Source }
                    else { (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') }
            return [pscustomobject]@{
                FileName     = $pwsh
                PrefixArgs   = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', $src)
                # 对于 ps1，传给 Start-Process 的参数列表是 -File script.ps1 后再拼接用户参数（全部以独立 arg 出现即可）
                JoinMode     = 'concat'
                DisplayHint  = "pwsh -File $src"
            }
        }
        # Batch 脚本 → cmd.exe /D /C "script.cmd arg1 arg2 ..."
        if ($ext -in @('.cmd', '.bat')) {
            return [pscustomobject]@{
                FileName     = (Join-Path $env:SystemRoot 'System32\cmd.exe')
                PrefixArgs   = @('/D', '/C', "`"$src`"")
                # cmd 的 /C 接受完整命令串：把用户 args 拼成单串再放进 ""，但 Start-Process 的 -ArgumentList 只接一个列表
                # 所以 joinMode = 'stringify' (在 caller 里把 PrefixArgs 末端合并)
                JoinMode     = 'cmd-args'
                DisplayHint  = "cmd /C $src"
            }
        }
        # 普通 .exe / .com 等可直接启动的可执行档
        return [pscustomobject]@{
            FileName     = $src
            PrefixArgs   = @()
            JoinMode     = 'concat'
            DisplayHint  = $src
        }
    }
    throw "找不到命令: $Name"
}

function Start-TaggedChild {
    param(
        [Parameter(Mandatory)][string]$Tag,
        [Parameter(Mandatory)][ConsoleColor]$Color,
        [Parameter(Mandatory)][string]$CommandName,
        [string[]]$ArgumentList = @(),
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [hashtable]$ExtraEnv = @{}
    )
    $tmp = [System.IO.Path]::GetTempPath()
    $outFile = Join-Path $tmp "$TmpPrefix`_$Tag.out"
    $errFile = Join-Path $tmp "$TmpPrefix`_$Tag.err"
    New-Item -ItemType File -Force -Path $outFile | Out-Null
    New-Item -ItemType File -Force -Path $errFile | Out-Null

    $callable = Resolve-Callable $CommandName

    # 构造传参
    $allArgs = switch ($callable.JoinMode) {
        'concat' {
            $combined = New-Object System.Collections.Generic.List[string]
            foreach ($a in $callable.PrefixArgs) { [void]$combined.Add($a) }
            foreach ($a in $ArgumentList)     { [void]$combined.Add($a) }
            $combined.ToArray()
        }
        'cmd-args' {
            # cmd /D /C "script.cmd arg1 arg2"
            $escapedArgs = ($ArgumentList | ForEach-Object {
                if ($_ -match '\s|"') {
                    $e = $_ -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1'
                    "`"$e`""
                } else { $_ }
            })
            # 拼出 "C:\path\to\pnpm.cmd" dev 之类的整体命令串，然后用 /S /C 让 cmd 自行去除外层引号
            $inner = "$($callable.PrefixArgs[2]) " + ($escapedArgs -join ' ')   # "script.cmd" arg1 arg2...
            @('/S', '/C', "`"$inner`"")
        }
        default {
            throw "未知 JoinMode: $_"
        }
    }

    $startParams = @{
        FilePath               = $callable.FileName
        WorkingDirectory       = $WorkingDirectory
        PassThru               = $true
        NoNewWindow            = $true
        Wait                   = $false
        RedirectStandardOutput = $outFile
        RedirectStandardError  = $errFile
    }
    if ($allArgs.Count -gt 0) {
        $startParams['ArgumentList'] = $allArgs
    }
    Write-TaggedLine 'rosetta' DarkGray "  · resolved callable: $($callable.DisplayHint)  →  $($callable.FileName) $($allArgs -join ' ')"

    # 环境变量注入（优先 Start-Process 6+ 自带的 -Environment；否则用 [Environment]:: 临时切换）
    $envRestorer = $null
    if ($ExtraEnv.Count -gt 0) {
        $patched = $false
        try {
            $cmdLet = Get-Command Start-Process -ErrorAction Stop
            if ($cmdLet.Parameters.ContainsKey('Environment')) {
                $startParams['Environment'] = $ExtraEnv
                $patched = $true
            }
        } catch {}
        if (-not $patched) {
            $prev = @{}
            foreach ($kv in $ExtraEnv.GetEnumerator()) {
                $prev[$kv.Key] = [Environment]::GetEnvironmentVariable($kv.Key)
                [Environment]::SetEnvironmentVariable($kv.Key, [string]$kv.Value)
            }
            $envRestorer = [pscustomobject]@{ Prev = $prev }
        }
    }

    try {
        $proc = Start-Process @startParams
    } finally {
        if ($envRestorer) {
            foreach ($kv in $envRestorer.Prev.GetEnumerator()) {
                [Environment]::SetEnvironmentVariable($kv.Key, $kv.Value)
            }
        }
    }

    return [pscustomobject]@{
        Tag      = $Tag
        Color    = $Color
        Proc     = $proc
        OutFile  = $outFile
        ErrFile  = $errFile
    }
}

# ── 启动前检查 ───────────────────────────────────────────────────────────────
if (-not $NoBackend -and (Test-PortListening -HostIp $BackendHost -Port $BackendPort)) {
    Write-TaggedLine 'rosetta' Yellow "端口 $BackendHost`:$BackendPort 已被占用，如属残留进程请先清理:  taskkill /F /IM python.exe /T ; taskkill /F /IM uv.exe /T" -TextColor Yellow
}

# 决定后端启动器：uv (锁存在时优先) → py → python
function Get-BackendLauncher {
    $hasUvLock = Test-Path (Join-Path $BackendDir 'uv.lock') -PathType Leaf
    if ($hasUvLock -and (Test-CommandExists 'uv')) {
        return [pscustomobject]@{ Cmd = 'uv';   Args = @('run', 'uvicorn', 'backend.main:app', "--host=$BackendHost", "--port=$BackendPort", '--reload') }
    }
    if (Test-CommandExists 'py') {
        return [pscustomobject]@{ Cmd = 'py';   Args = @('-m', 'uvicorn', 'backend.main:app', "--host=$BackendHost", "--port=$BackendPort", '--reload') }
    }
    if (Test-CommandExists 'python') {
        return [pscustomobject]@{ Cmd = 'python'; Args = @('-m', 'uvicorn', 'backend.main:app', "--host=$BackendHost", "--port=$BackendPort", '--reload') }
    }
    throw "找不到可用的 Python 启动器 (uv / py / python)，请先在项目根执行 uv sync"
}

# ── 主流程 ───────────────────────────────────────────────────────────────────
$Launched = New-Object System.Collections.Generic.List[object]
$TailTargets = @()
try {
    $bannerPad = 58
    $apiLine   = "后端 API   : http://$BackendHost`:$BackendPort/api"
    $docLine   = "后端文档   : http://$BackendHost`:$BackendPort/docs"
    $frontLine = '前端页面   : http://localhost:3000 (Nuxt 默认端口)'
    $stopLine  = '停止       : Ctrl+C  (会自动 taskkill 所有子进程)'
    Write-Host ''
    Write-Host ('╔' + ('═' * $bannerPad) + '╗') -ForegroundColor Cyan
    Write-Host ('║' + ('  Rosetta Dev · 前后端并发启动脚本').PadRight($bannerPad) + '║') -ForegroundColor Cyan
    Write-Host ('╠' + ('═' * $bannerPad) + '╣') -ForegroundColor Cyan
    Write-Host ('║ ' + $apiLine.PadRight($bannerPad - 2)   + ' ║') -ForegroundColor DarkCyan
    Write-Host ('║ ' + $docLine.PadRight($bannerPad - 2)   + ' ║') -ForegroundColor DarkCyan
    Write-Host ('║ ' + $frontLine.PadRight($bannerPad - 2) + ' ║') -ForegroundColor Magenta
    Write-Host ('║ ' + $stopLine.PadRight($bannerPad - 2)  + ' ║') -ForegroundColor Gray
    Write-Host ('╚' + ('═' * $bannerPad) + '╝') -ForegroundColor Cyan
    Write-Host ''

    if (-not $NoBackend) {
        $be = Get-BackendLauncher
        $pp = if ($env:PYTHONPATH) { "$BackendDir;$($env:PYTHONPATH)" } else { $BackendDir }
        Write-TaggedLine 'rosetta' DarkCyan "后端命令: $($be.Cmd) $($be.Args -join ' ')   (cwd: $BackendDir)"
        $st = Start-TaggedChild -Tag 'backend' -Color Cyan -CommandName $be.Cmd -ArgumentList $be.Args `
               -WorkingDirectory $BackendDir -ExtraEnv @{ PYTHONUNBUFFERED='1'; PYTHONPATH=$pp }
        [void]$Launched.Add($st)
        $TailTargets += [pscustomobject]@{
            Tag        = 'backend'
            Color      = [ConsoleColor]::Cyan
            OutFile    = $st.OutFile
            ErrFile    = $st.ErrFile
            OutReadLen = [ref]0
            ErrReadLen = [ref]0
        }
    }

    if (-not $NoFrontend) {
        Start-Sleep -Milliseconds 500
        Write-TaggedLine 'rosetta' Magenta "前端命令: pnpm dev   (cwd: $FrontendDir)"
        $st = Start-TaggedChild -Tag 'frontend' -Color Magenta -CommandName 'pnpm' -ArgumentList @('dev') -WorkingDirectory $FrontendDir
        [void]$Launched.Add($st)
        $TailTargets += [pscustomobject]@{
            Tag        = 'frontend'
            Color      = [ConsoleColor]::Magenta
            OutFile    = $st.OutFile
            ErrFile    = $st.ErrFile
            OutReadLen = [ref]0
            ErrReadLen = [ref]0
        }
    }

    Write-TaggedLine 'rosetta' Green "已启动 $($Launched.Count) 个子进程，进入守护等待 (按 Ctrl+C 停止)"
    if ($TestAutoStopAfter -gt 0) {
        Write-TaggedLine 'rosetta' Gray "调试模式：守护循环将在 ${TestAutoStopAfter}s 后自动退出，以验证 finally 清理逻辑"
    }
    $enteredAt = [DateTime]::Now

    # 守护：
    #   · 每 120ms 把 tail 文件追加内容按前缀转储到当前控制台（模拟 multi-tail -F）
    #   · 每 ~500ms 检查一次子进程存活状态，任一异常退出则 finally 清理全家
    $lastProcCheck = [DateTime]::MinValue
    while ($true) {
        foreach ($t in $TailTargets) {
            foreach ($streamType in 'out', 'err') {
                $file = if ($streamType -eq 'out') { $t.OutFile } else { $t.ErrFile }
                $ref  = if ($streamType -eq 'out') { $t.OutReadLen } else { $t.ErrReadLen }
                try {
                    $fi = New-Object System.IO.FileInfo($file)
                    if (-not $fi.Exists) { continue }
                    $currentLen = $fi.Length
                    if ($currentLen -gt $ref.Value) {
                        $fs = [System.IO.FileStream]::new($file, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
                        try {
                            $fs.Seek($ref.Value, [System.IO.SeekOrigin]::Begin) | Out-Null
                            $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)
                            $text = $sr.ReadToEnd()
                            if ($text.Length -gt 0) {
                                $color = if ($streamType -eq 'err') { [ConsoleColor]::DarkRed } else { $t.Color }
                                foreach ($line in $text -split "`r?`n") {
                                    if ($line.Length -gt 0) {
                                        Write-TaggedLine $t.Tag $color $line
                                    }
                                }
                            }
                            $ref.Value = $currentLen
                        } finally {
                            try { $sr.Dispose() } catch {}
                            try { $fs.Dispose() } catch {}
                        }
                    }
                } catch {
                    # 文件被独占等短暂异常，忽略进入下一循环
                }
            }
        }

        $now = [DateTime]::Now
        if ($TestAutoStopAfter -gt 0 -and ($now - $enteredAt).TotalSeconds -ge $TestAutoStopAfter) {
            Write-TaggedLine 'rosetta' Gray "到达 TestAutoStopAfter=${TestAutoStopAfter}s，主动退出主循环以触发清理"
            break
        }
        if (($now - $lastProcCheck).TotalMilliseconds -ge 500) {
            $lastProcCheck = $now
            $dead = @($Launched | Where-Object { $null -ne $_.Proc -and $_.Proc.HasExited })
            if ($dead.Count -gt 0) {
                foreach ($d in $dead) {
                    Write-TaggedLine 'rosetta' Yellow "[$($d.Tag)] PID $($d.Proc.Id) 已退出 (code=$($d.Proc.ExitCode))"
                }
                break
            }
        }
        Start-Sleep -Milliseconds 120
    }
} catch {
    Write-TaggedLine 'rosetta' DarkRed ("启动阶段异常: " + $_.Exception.Message)
    if ($_.Exception.StackTrace) { Write-Host $_.Exception.StackTrace -ForegroundColor DarkRed }
    throw
} finally {
    Write-Host ''
    Write-TaggedLine 'rosetta' Yellow '收到退出信号，开始级联清理子进程树 ...'

    foreach ($l in $Launched) {
        try {
            # 宽松检查：尽量获取有效 PID 再杀；杀不到就算了
            $pidToKill = $null
            if ($null -ne $l -and $null -ne $l.Proc) {
                try {
                    if ($l.Proc.HasExited) {
                        Write-TaggedLine 'rosetta' Gray ("  · [" + $l.Tag + "] 已自行退出 (PID " + $l.Proc.Id + ")")
                        continue
                    }
                    $pidToKill = $l.Proc.Id
                } catch {
                    $pidToKill = $null
                }
            }
            if ($null -eq $pidToKill) {
                Write-TaggedLine 'rosetta' Gray ("  · [" + $l.Tag + "] 无法获取 PID，跳过")
                continue
            }

            Write-TaggedLine 'rosetta' Yellow ("  · taskkill /T /F  [" + $l.Tag + "]  PID " + $pidToKill)

            # 用 cmd.exe /c taskkill 彻底规避 PowerShell 对外接程序 stderr / stream redir 的 EAP 干扰
            $cmdLine = 'taskkill /PID ' + $pidToKill + ' /T /F > nul 2>&1'
            $cmdPsi = New-Object System.Diagnostics.ProcessStartInfo
            $cmdPsi.FileName  = (Join-Path $env:SystemRoot 'System32\cmd.exe')
            $cmdPsi.Arguments = '/D /C ' + $cmdLine
            $cmdPsi.UseShellExecute = $false
            $cmdPsi.CreateNoWindow    = $true
            try {
                $p = [System.Diagnostics.Process]::Start($cmdPsi)
                if ($p) {
                    $p.WaitForExit(4000)
                    try { $p.Dispose() } catch {}
                }
            } catch {
                # 最后兜底：直接 Kill() 进程对象
                try {
                    if ($null -ne $l.Proc -and -not $l.Proc.HasExited) {
                        $l.Proc.Kill()
                    }
                } catch {}
            }
        } catch {
            # 单个进程的清理错误不影响其他进程
            try {
                Write-TaggedLine 'rosetta' Gray ("  · [" + $l.Tag + "] 清理阶段忽略异常")
            } catch {}
        }
    }

    # 清理临时日志文件
    foreach ($l in $Launched) {
        try { if (Test-Path $l.OutFile) { Remove-Item $l.OutFile -Force -ErrorAction SilentlyContinue } } catch {}
        try { if (Test-Path $l.ErrFile) { Remove-Item $l.ErrFile -Force -ErrorAction SilentlyContinue } } catch {}
    }
    Write-TaggedLine 'rosetta' Green '清理完毕。'
}
