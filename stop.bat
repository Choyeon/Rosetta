@echo off
REM =================================================================
REM  Rosetta Dev · 停止脚本
REM  使用方法：
REM    1. 双击运行
REM    2. 或命令行： stop.bat [BACKEND_PORT=8000] [FRONTEND_PORT=3000] [-Force]
REM  策略：
REM    · 先读 .rosetta_run\backend.pid / frontend.pid，按 PID taskkill /T /F
REM    · 再按端口兜底检测 (默认 :8000 :3000)
REM    · 只停止 Rosetta 家族进程 (路径匹配仓库 或 进程名 python/node/pnpm/uv/cmd)
REM    · 绝对不会 全局 taskkill /IM python.exe  /IM node.exe 误伤
REM =================================================================
setlocal EnableExtensions
cd /d "%~dp0"

REM 解析参数：支持 BACKEND_PORT=8000 FRONTEND_PORT=3000 -Force
:parse_args
if "%~1"=="" goto args_done
set "A=%~1"
if /I "%A:~0,1%"=="-" (
  REM Switches -BackendPort 8000 形式
  if /I "%A%"=="-BackendPort"  ( set "BE_NEXT=1" & shift & goto parse_args )
  if /I "%A%"=="-FrontendPort" ( set "FE_NEXT=1" & shift & goto parse_args )
  if /I "%A%"=="-Force" ( set "FORCE_FLAG=%A%" & shift & goto parse_args )
  shift & goto parse_args
)
if defined BE_NEXT ( set "BACKEND_PORT=%A%" & set "BE_NEXT=" & shift & goto parse_args )
if defined FE_NEXT ( set "FRONTEND_PORT=%A%" & set "FE_NEXT=" & shift & goto parse_args )
REM KEY=VALUE form
echo.%A% | findstr /R /C:"^BACKEND_PORT="  >nul && set "%A%" && shift && goto parse_args
echo.%A% | findstr /R /C:"^FRONTEND_PORT=" >nul && set "%A%" && shift && goto parse_args
shift & goto parse_args
:args_done

REM 缺省值
if not defined BACKEND_PORT  set "BACKEND_PORT=8000"
if not defined FRONTEND_PORT set "FRONTEND_PORT=3000"

REM 选择 PowerShell
set "POWERSHELL="
where pwsh.exe >nul 2>nul
if %ERRORLEVEL%==0 ( set "POWERSHELL=pwsh.exe" & goto launch_stop )
if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
  set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
  goto launch_stop
)
echo [Rosetta] PowerShell missing. Please install PowerShell.
pause
exit /b 3

:launch_stop
"%POWERSHELL%" -NoProfile -NoLogo -ExecutionPolicy Bypass ^
  -File "%~dp0stop.ps1" ^
  -BackendPort %BACKEND_PORT% ^
  -FrontendPort %FRONTEND_PORT% ^
  %FORCE_FLAG% %*
set "EC=%ERRORLEVEL%"
REM 出错时 pause 让用户看日志；正常就直接退出
if not "%EC%"=="0" (
  echo.
  echo [Rosetta] stop exit code = %EC%. Please scroll up to check.
  echo.
  pause
)
exit /b %EC%
