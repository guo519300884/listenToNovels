@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Packaging listen-novel exe (Edge TTS + SAPI)...
python -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name "听小说" ^
  --hidden-import=edge_tts ^
  --hidden-import=aiohttp ^
  --hidden-import=miniaudio ^
  --hidden-import=numpy ^
  --hidden-import=pypdf ^
  --hidden-import=docx ^
  --hidden-import=ebooklib ^
  --hidden-import=bs4 ^
  --hidden-import=lxml ^
  --hidden-import=striprtf ^
  --hidden-import=py7zr ^
  --hidden-import=pythoncom ^
  --hidden-import=win32com.client ^
  --exclude-module=torch ^
  --exclude-module=torchvision ^
  --exclude-module=torchaudio ^
  --exclude-module=piper ^
  --exclude-module=onnxruntime ^
  --exclude-module=scipy ^
  --exclude-module=pandas ^
  --collect-all customtkinter ^
  --collect-all edge_tts ^
  --collect-all ebooklib ^
  --collect-all py7zr ^
  app.py
if errorlevel 1 (
  echo Build failed
  exit /b 1
)
echo.
echo Done: dist\听小说.exe
