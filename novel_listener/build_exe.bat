@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Packaging listen-novel exe (Piper + SAPI + Edge TTS)...
python -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name "???" ^
  --hidden-import=piper ^
  --hidden-import=piper.voice ^
  --hidden-import=piper.config ^
  --hidden-import=piper.espeakbridge ^
  --hidden-import=piper.phonemize_espeak ^
  --hidden-import=onnxruntime ^
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
  --exclude-module=piper.train ^
  --exclude-module=scipy ^
  --exclude-module=pandas ^
  --collect-data piper ^
  --collect-all customtkinter ^
  --collect-all onnxruntime ^
  --collect-all edge_tts ^
  --collect-all ebooklib ^
  --collect-all py7zr ^
  app.py
if errorlevel 1 (
  echo Build failed
  exit /b 1
)
echo.
echo Done: dist\???.exe
echo Keep voices\ folder next to the exe.
