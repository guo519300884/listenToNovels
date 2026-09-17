@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   听小说 · 更新到 10 倍速绿色版
echo ========================================
echo.
echo 请先完全退出正在运行的「听小说」窗口！
echo.
pause

where git >nul 2>&1
if errorlevel 1 (
  echo [错误] 本目录不是用 Git 管理，或未安装 Git。
  echo 请到 GitHub 拉取本分支后，用「听小说应用」文件夹整夹覆盖。
  echo.
  echo https://github.com/guo519300884/listenToNovels/tree/cursor/raise-speed-apply-2903
  pause
  exit /b 1
)

echo 正在拉取最新绿色版…
git fetch origin cursor/raise-speed-apply-2903
if errorlevel 1 (
  echo [错误] git fetch 失败，请检查网络
  pause
  exit /b 1
)
git checkout cursor/raise-speed-apply-2903
if errorlevel 1 (
  echo [错误] 切换分支失败。若有未提交修改，请先自行处理后再试。
  pause
  exit /b 1
)
git pull origin cursor/raise-speed-apply-2903

echo.
echo 已更新。请确认：
echo   1. 关闭旧的听小说窗口
echo   2. 双击  听小说应用\听小说.exe
echo   3. 左上角应显示「v1.1.0 · 最高10x」
echo   4. 速度预设应为 1x / 2x / 3x / 5x / 8x / 10x（没有 1.5x）
echo.
echo 若仍看到 1.0x 1.5x … 5.0x，说明打开的还是旧程序
echo （开始菜单 / 桌面快捷方式 / 安装目录），请改用本目录下的绿色版。
echo.
start "" "%~dp0听小说应用"
pause
