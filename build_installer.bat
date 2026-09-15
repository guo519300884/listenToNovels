@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

REM Forward to PowerShell (UTF-8 BOM script).
REM Usage:
REM   build_installer.bat
REM   build_installer.bat 1.2.0

set "PS1=%~dp0build_installer.ps1"
if not exist "%PS1%" (
  echo [ERR] Missing build_installer.ps1
  pause
  exit /b 1
)

where pwsh >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PSEXE=pwsh"
) else (
  set "PSEXE=powershell"
)

if "%~1"=="" (
  "%PSEXE%" -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
) else (
  "%PSEXE%" -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -Version "%~1"
)

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo [ERR] build failed, exit code %ERR%
  echo Tip: open build_installer.ps1 in Notepad and confirm it is UTF-8.
  pause
)
exit /b %ERR%
