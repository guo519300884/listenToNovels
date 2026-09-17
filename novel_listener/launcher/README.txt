@echo off
REM Cross-compile green-package launcher on Linux/macOS with mingw-w64:
REM   x86_64-w64-mingw32-gcc -O2 -municode -mwindows -finput-charset=UTF-8 -fexec-charset=UTF-8 -o 听小说.exe listen_launcher.c
echo This directory holds the Windows green-package launcher source.
echo Build with mingw-w64 as shown in listen_launcher.c header comments.
