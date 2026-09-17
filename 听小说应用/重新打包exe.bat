@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "APP_DIR=%~dp0..\novel_listener"
if not exist "%APP_DIR%\build_exe.bat" (
  echo [错误] 找不到 novel_listener\build_exe.bat
  pause
  exit /b 1
)

echo 将用最新源码重新打包听小说.exe（含 10 倍速）…
call "%APP_DIR%\build_exe.bat"
if errorlevel 1 (
  echo 打包失败
  pause
  exit /b 1
)

if not exist "%APP_DIR%\dist\听小说.exe" (
  echo [错误] 未生成 dist\听小说.exe
  pause
  exit /b 1
)

copy /Y "%APP_DIR%\dist\听小说.exe" "%~dp0听小说.exe" >nul
echo.
echo 已更新本目录的听小说.exe，可直接双击使用。
pause
