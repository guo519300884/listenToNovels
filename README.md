# 听小说

Windows 本地听书应用：导入小说文件，用微软 Edge 神经网络真人语音朗读，支持多本书架、章节目录、进度记忆与全局快捷键。

> 朗读时需要联网（调用 `edge-tts` 生成语音）；小说文件与听书进度均保存在本机。

## 功能特性

- **真人讲书音色**：多种中文神经网络音色，听感接近导航播报
- **多本书架**：一次导入多本 / 整文件夹导入，随时切换收听
- **多格式支持**：`txt` / `md` / `pdf` / `doc` / `docx` / `epub` / `rtf` / `html`
- **自动分章**：侧栏目录跳转，支持章节筛选
- **正文搜索**：本章 / 全书搜索，定位后可从该处朗读
- **朗读跟随**：高亮当前句并自动滚动；可拖进度条、点击正文定位
- **语速调节**：约 `0.5x`～`5.0x`
- **进度记忆**：每本书分别记住章节与位置，下次自动续听
- **日间 / 夜间主题**、可自定义全局快捷键、迷你控制窗

## 快速开始（普通用户）

### 方式一：安装包（推荐）

1. 下载 [Releases](../../releases) 中的 `听小说安装包_v1.0.0.exe`  
   （或使用仓库内 `发布/听小说安装包_v1.0.0.exe`）
2. 双击安装，按向导完成
3. 从开始菜单或桌面快捷方式启动「听小说」

### 方式二：绿色版

直接运行 `听小说应用/听小说.exe`，无需安装。

## 使用说明

1. 左侧点击 **导入小说**（可多选）或 **导入文件夹**
2. 在 **书架** 中点选要听的书；在 **目录** 中跳转章节
3. 底部选择 **讲书音色**，调节速度后点播放
4. 单击正文可从该位置开始听；拖动进度条可跳转

### 注意事项

| 项目 | 说明 |
|------|------|
| PDF | 需为可选中文字的文档；纯扫描图片 PDF 读不出字 |
| 旧版 `.doc` | 建议本机已安装 Microsoft Word，或先另存为 `.docx` |
| 网络 | 首次朗读某段文字需联网合成；本地会缓存语音 |
| 卸载 | 卸载安装包不会删除听书进度（见下方数据目录） |

## 从源码运行（开发者）

### 环境要求

- Windows 10 / 11
- Python 3.11+（推荐 3.13）

### 安装依赖

```bash
cd novel_listener
pip install -r requirements.txt
```

### 启动

```bash
python app.py
```

### 打包可执行文件

```bat
novel_listener\build_exe.bat
```

生成结果：`novel_listener\dist\听小说.exe`（可复制到 `听小说应用\`）。

### 生成 Windows 安装包

需先安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)：

```bat
winget install JRSoftware.InnoSetup
```

然后在项目根目录执行（可自定义版本号）：

```bat
build_installer.bat 1.2.0
```

或不带参数双击运行，按提示输入版本号。  
安装包输出到：`发布/听小说安装包_v1.2.0.exe`（文件名随版本变化）。  
默认版本保存在根目录 `VERSION` 文件中。

## 项目结构

```text
PC_TS/
├── novel_listener/          # 主程序源码
│   ├── app.py               # 听小说 GUI 与业务逻辑
│   ├── requirements.txt     # Python 依赖
│   ├── build_exe.bat        # 打包 exe
│   └── installer/           # Inno Setup 安装脚本
├── 听小说应用/              # 绿色版交付（exe + 说明）
├── 发布/                    # 安装包输出目录
├── VERSION                  # 当前默认版本号
└── build_installer.bat      # 一键生成安装包（支持自定义版本）
```

## 技术栈

| 组件 | 用途 |
|------|------|
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | 桌面 GUI |
| [edge-tts](https://github.com/rany2/edge-tts) | 微软神经网络 TTS |
| pygame | 音频播放 |
| pypdf / python-docx / ebooklib 等 | 多格式小说解析 |
| PyInstaller | 打包单文件 exe |
| Inno Setup | 制作安装程序 |

## 数据目录

用户数据默认保存在：

```text
%USERPROFILE%\.novel_listener\
├── library.json      # 书架
├── progress.json     # 各书进度
├── settings.json     # 主题、音色、快捷键等
└── tts_cache\        # 语音缓存
```

## 许可证

本项目仅供学习与个人使用。第三方依赖遵循各自许可证；语音服务由 Microsoft Edge TTS 提供，使用时请遵守相关服务条款。
