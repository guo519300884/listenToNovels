@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "APP_DIR=%~dp0..\novel_listener"
if not exist "%APP_DIR%\app.py" set "APP_DIR=%~dp0src"
if not exist "%APP_DIR%\app.py" (
  echo [错误] 找不到程序源码：novel_listener\app.py
  pause
  exit /b 1
)

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo [错误] 未检测到 Python。请先安装 Python 3.11+，或双击「重新打包exe.bat」生成听小说.exe 后使用。
  pause
  exit /b 1
)

echo 正在检查依赖…
%PY% -m pip install -r "%APP_DIR%\requirements.txt" -q
if errorlevel 1 (
  echo [错误] 依赖安装失败
  pause
  exit /b 1
)

echo 启动听小说（支持最高 10 倍速）…
%PY% "%APP_DIR%\app.py"
if errorlevel 1 pause
