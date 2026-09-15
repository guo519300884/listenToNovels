@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "APP_DIR=%~dp0听小说应用"
set "DIST_DIR=%~dp0novel_listener\dist"
set "ISS=%~dp0novel_listener\installer\听小说.iss"
set "OUT_DIR=%~dp0发布"
set "VERSION_FILE=%~dp0VERSION"

echo ========================================
echo   听小说 — 生成 Windows 安装包
echo ========================================
echo.
echo 用法:
echo   build_installer.bat           交互输入版本号
echo   build_installer.bat 1.2.3     指定版本号
echo.

REM ---------- 版本号：参数 ^> VERSION 文件 ^> 默认 1.0.0 ----------
set "APP_VERSION=%~1"
if not defined APP_VERSION if exist "%VERSION_FILE%" (
  set /p APP_VERSION=<"%VERSION_FILE%"
)
if not defined APP_VERSION set "APP_VERSION=1.0.0"
for /f "tokens=* delims= " %%A in ("%APP_VERSION%") do set "APP_VERSION=%%A"

if "%~1"=="" (
  echo 当前默认版本: !APP_VERSION!
  set /p "INPUT_VERSION=请输入版本号（直接回车使用默认）: "
  if defined INPUT_VERSION (
    for /f "tokens=* delims= " %%A in ("!INPUT_VERSION!") do set "APP_VERSION=%%A"
  )
)

if not defined APP_VERSION (
  echo [错误] 版本号不能为空
  exit /b 1
)

echo !APP_VERSION!| findstr /r "^[0-9][0-9.]*$" >nul
if errorlevel 1 (
  echo [错误] 版本号格式无效: !APP_VERSION!
  echo        请使用类似 1.0.0 或 1.2.3.4 的数字版本号
  exit /b 1
)

REM 统计版本段数，补齐为 4 段供 VersionInfoVersion 使用
set "PARTS=0"
for %%A in (!APP_VERSION:.= !) do set /a PARTS+=1
set "VER_INFO=!APP_VERSION!"
if !PARTS! LSS 1 (
  echo [错误] 版本号无效
  exit /b 1
)
if !PARTS! EQU 1 set "VER_INFO=!APP_VERSION!.0.0.0"
if !PARTS! EQU 2 set "VER_INFO=!APP_VERSION!.0.0"
if !PARTS! EQU 3 set "VER_INFO=!APP_VERSION!.0"
if !PARTS! GEQ 5 (
  echo [错误] 版本号最多 4 段，例如 1.2.3.4
  exit /b 1
)

> "%VERSION_FILE%" echo !APP_VERSION!

echo [信息] 安装包版本: !APP_VERSION!
echo [信息] 文件版本号: !VER_INFO!
echo.

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
echo        输出: %OUT_DIR%\听小说安装包_v!APP_VERSION!.exe
echo.
"%ISCC%" "/DMyAppVersion=!APP_VERSION!" "/DMyAppVersionInfo=!VER_INFO!" "%ISS%"
if errorlevel 1 (
  echo.
  echo [失败] 安装包编译失败
  exit /b 1
)

echo.
echo [完成] 已生成: 发布\听小说安装包_v!APP_VERSION!.exe
dir /b "%OUT_DIR%\听小说安装包_v!APP_VERSION!.exe" 2>nul
explorer "%OUT_DIR%"
endlocal
