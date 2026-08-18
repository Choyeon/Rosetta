@echo off
REM ============================================================
REM  Rosetta Dev · 双击/命令行 一键启动 前后端 (Windows)
REM  等价于直接执行:  powershell -File dev.ps1
REM ============================================================
setlocal
cd /d "%~dp0"

REM 优先使用新版 pwsh (PowerShell 7+)，没有就退回到 Windows PowerShell 5.1
where pwsh.exe >nul 2>nul
if %ERRORLEVEL%==0 (
  pwsh.exe -NoProfile -NoLogo -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
  goto :eof
)

powershell.exe -NoProfile -NoLogo -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
endlocal
