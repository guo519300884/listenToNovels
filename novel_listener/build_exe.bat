@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在打包听小说.exe（最高 10 倍速 + 调速立即生效）...
python -m PyInstaller --noconfirm --clean "听小说.spec"
if errorlevel 1 (
  echo 打包失败
  exit /b 1
)
echo.
echo 完成: dist\听小说.exe
if exist "dist\听小说.exe" (
  if exist "..\听小说应用\" (
    copy /Y "dist\听小说.exe" "..\听小说应用\听小说.exe" >nul
    echo 已同步到 ..\听小说应用\听小说.exe
  )
)
explorer dist
