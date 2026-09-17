@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0_prepare.bat"
if errorlevel 1 (
  echo [错误] 缺少运行环境压缩包
  pause
  exit /b 1
)
set "PYTHONHOME=%~dp0runtime"
set "PATH=%~dp0runtime;%~dp0runtime\DLLs;%~dp0runtime\Scripts;%PATH%"
set "PYTHONPATH=%~dp0app"
set "PYTHONUTF8=1"
"%~dp0runtime\python.exe" "%~dp0app\app.py"
echo.
pause
