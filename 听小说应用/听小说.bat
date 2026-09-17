@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0_prepare.bat"
if errorlevel 1 (
  echo [错误] 缺少 听小说便携版_10倍速.zip，无法准备运行环境
  pause
  exit /b 1
)
set "PYTHONHOME=%~dp0runtime"
set "PATH=%~dp0runtime;%~dp0runtime\DLLs;%~dp0runtime\Scripts;%PATH%"
set "PYTHONPATH=%~dp0app"
set "PYTHONUTF8=1"
start "" "%~dp0runtime\pythonw.exe" "%~dp0app\app.py"
