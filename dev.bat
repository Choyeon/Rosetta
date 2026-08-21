@echo off
REM =================================================================
REM  Rosetta 开发 · 双击入口 (Windows)
REM  说明：
REM   1. 优先使用 pwsh (PowerShell 7+)，不存在时退回 Windows PowerShell 5.1
REM   2. 执行 start.ps1：两个独立窗口分别跑 后端(:8000) + 前端(:3000)，
REM      本窗口作为"主控"显示 URL、按 Q 停止 / O 打开首页 / D 打开文档。
REM   3. 出错时自动 pause，避免一闪而过。
REM =================================================================
setlocal
setlocal EnableExtensions
cd /d "%~dp0"

REM 显式 UTF-8 输出（对中文环境友好）
chcp 65001 >nul 2>&1

REM 优先 pwsh
set "POWERSHELL="
where pwsh.exe >nul 2>nul
if %ERRORLEVEL%==0 (
  set "POWERSHELL=pwsh.exe"
  goto :launch
)
REM 回退到 Windows PowerShell 5.1
if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
  set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
  goto :launch
)

echo.
echo [Rosetta] ❌ 未检测到 PowerShell，无法启动脚本。
pause
exit /b 3

:launch
"%POWERSHELL%" -NoProfile -NoLogo -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
set "EXITCODE=%ERRORLEVEL%"

REM 退出码 0 表示正常结束（用户 Q 或窗口都关了），不需要 pause。
if "%EXITCODE%"=="0" (
  exit /b 0
)

echo.
echo [Rosetta] ⚠  启动异常，exit code = %EXITCODE%。请滚动上面的日志查看。
echo.
pause
exit /b %EXITCODE%
