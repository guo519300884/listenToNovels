@echo off
cd /d "%~dp0"
if exist "runtime\pythonw.exe" exit /b 0
echo 正在准备便携运行环境（首次约半分钟）...
set "ZIP="
if exist "听小说便携版_10倍速.zip" set "ZIP=听小说便携版_10倍速.zip"
if not defined ZIP if exist "..\发布\听小说便携版_10倍速.zip" set "ZIP=..\发布\听小说便携版_10倍速.zip"
if not defined ZIP exit /b 1
powershell -NoProfile -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '_extract_tmp' -Force"
if exist "_extract_tmp\听小说便携版\runtime" move /Y "_extract_tmp\听小说便携版\runtime" "runtime" >nul
if exist "_extract_tmp\听小说便携版\app\app.py" (
  if not exist "app" mkdir "app"
  copy /Y "_extract_tmp\听小说便携版\app\app.py" "app\app.py" >nul
)
rmdir /S /Q "_extract_tmp" 2>nul
if exist "runtime\pythonw.exe" exit /b 0
exit /b 1
