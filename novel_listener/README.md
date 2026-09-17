# 听小说（源码目录）

本目录为「听小说」桌面应用的 Python 源码。完整说明见仓库根目录 [README.md](../README.md)。

## 简介

用微软 Edge 神经网络真人语音朗读本地小说，支持多本书架、多格式导入、章节目录、语速调节（`0.5x`～`10.0x`，`3.0x` 以上本地加速；改速立即生效）、进度记忆与全局快捷键。

## 快速运行

```bash
pip install -r requirements.txt
python app.py
```

## 打包

```bat
build_exe.bat
```

输出：`dist\听小说.exe`。可复制到 `../听小说应用/听小说.exe` 作为绿色版使用。

## 主要依赖

见 `requirements.txt`：`customtkinter`、`edge-tts`、`pygame`，以及 `pypdf` / `python-docx` / `ebooklib` / `py7zr` 等解析库。

## 数据目录

运行后用户数据写入：`%USERPROFILE%\.novel_listener\`
