@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

REM 转发到 PowerShell，版本号自定义更稳定
REM 用法:
REM   build_installer.bat
REM   build_installer.bat 1.2.0

if "%~1"=="" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_installer.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_installer.ps1" -Version "%~1"
)

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [失败] 打包未成功，退出码 %ERR%
  pause
)
exit /b %ERR%
