@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在打包听小说.exe（多格式 + 真人语音）...
python -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name "听小说" ^
  --hidden-import=edge_tts ^
  --hidden-import=aiohttp ^
  --hidden-import=pypdf ^
  --hidden-import=docx ^
  --hidden-import=ebooklib ^
  --hidden-import=bs4 ^
  --hidden-import=lxml ^
  --hidden-import=striprtf ^
  --collect-all customtkinter ^
  --collect-all edge_tts ^
  --collect-all ebooklib ^
  app.py
if errorlevel 1 (
  echo 打包失败
  exit /b 1
)
echo.
echo 完成: dist\听小说.exe
explorer dist
