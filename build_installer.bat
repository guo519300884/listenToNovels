@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_DIR=%~dp0..\听小说应用"
set "DIST_DIR=%~dp0novel_listener\dist"
set "ISS=%~dp0novel_listener\installer\听小说.iss"
set "OUT_DIR=%~dp0发布"

echo ========================================
echo   听小说 — 生成 Windows 安装包
echo ========================================
echo.

REM 若交付目录没有 exe，尝试从 dist 复制
if not exist "%APP_DIR%\听小说.exe" (
  if exist "%DIST_DIR%\听小说.exe" (
    echo [信息] 从 dist 复制听小说.exe ...
    if not exist "%APP_DIR%" mkdir "%APP_DIR%"
    copy /Y "%DIST_DIR%\听小说.exe" "%APP_DIR%\听小说.exe" >nul
  )
)

if not exist "%APP_DIR%\听小说.exe" (
  echo [错误] 找不到听小说.exe
  echo 请先运行 novel_listener\build_exe.bat 打包主程序。
  exit /b 1
)

set "ISCC="
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
  echo [错误] 未找到 Inno Setup 6（ISCC.exe）
  echo 请安装: winget install JRSoftware.InnoSetup
  exit /b 1
)

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo [信息] 编译安装包...
echo        脚本: %ISS%
echo        输出: %OUT_DIR%
echo.
"%ISCC%" "%ISS%"
if errorlevel 1 (
  echo.
  echo [失败] 安装包编译失败
  exit /b 1
)

echo.
echo [完成] 安装包已生成到「发布」文件夹
dir /b "%OUT_DIR%\*.exe"
explorer "%OUT_DIR%"
endlocal
