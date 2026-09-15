# 听小说

Windows 本地听书应用：导入小说，用微软 Edge 神经网络真人语音朗读。支持多本书架、章节目录、进度记忆与全局快捷键。

> 朗读需要联网（`edge-tts`）；小说与进度保存在本机。

## 功能

- 真人中文讲书音色，语速约 `0.5x`～`5.0x`
- 多本书架：多选导入 / 文件夹导入，随时切换
- 格式：`txt` / `md` / `pdf` / `doc` / `docx` / `epub` / `rtf` / `html`
- 压缩包导入：`zip` / `7z` / `tar` / `gz` 等（自动解压出小说）
- 自动分章、正文搜索、朗读高亮跟随
- 日间 / 夜间主题、可自定义全局快捷键、迷你控制窗

## 普通用户：安装使用

### 安装包（推荐）

1. 打开仓库里的 `发布\` 目录
2. 双击 `听小说安装包_vX.Y.Z.exe`（版本号以文件名为准）
3. 按向导安装后，从开始菜单或桌面启动

### 绿色版

直接运行 `听小说应用\听小说.exe`，无需安装。

### 简单用法

1. 「导入小说」或「导入文件夹」
2. 「书架」选书，「目录」跳章节
3. 选音色 → 调速度 → 播放  
4. 单击正文可从该处开听；可拖进度条

| 注意 | 说明 |
|------|------|
| PDF | 需可选中文字；扫描版图片 PDF 读不出字 |
| 旧 `.doc` | 建议有 Word，或另存为 `.docx` |
| 网络 | 首次合成需联网，本地会缓存 |
| 卸载 | 不删听书进度（见下方数据目录） |

---

## 开发者：运行与打包

### 环境

- Windows 10 / 11
- Python 3.11+（推荐 3.13）
- 打安装包还需 [Inno Setup 6](https://jrsoftware.org/isinfo.php)

### 从源码运行

```bat
cd novel_listener
pip install -r requirements.txt
python app.py
```

### ① 打包主程序 exe

```bat
novel_listener\build_exe.bat
```

生成 `novel_listener\dist\听小说.exe`，再复制到 `听小说应用\听小说.exe`（脚本也会提示）。

### ② 打包安装包（可自定义版本号）

先安装 Inno Setup：

```bat
winget install JRSoftware.InnoSetup
```

再在**项目根目录**执行：

```bat
REM 方式 A：命令行指定版本（推荐）
build_installer.bat 1.2.0

REM 方式 B：双击运行，按提示输入版本号
build_installer.bat
```

成功后得到：

```text
发布\听小说安装包_v1.2.0.exe
```

版本号会写入根目录 `VERSION`，下次默认沿用。

若提示找不到 `ISCC.exe`，说明还没装好 Inno Setup 6，或未装到默认路径。

若 PowerShell 报 `Unexpected token` / 中文乱码，请确认已拉取最新脚本（`build_installer.ps1` 需为 **UTF-8 带 BOM**），然后重新执行：

```bat
build_installer.bat 1.2.0
```

---

## 目录说明

```text
PC_TS/
├── novel_listener/           # 源码
│   ├── app.py
│   ├── requirements.txt
│   ├── build_exe.bat         # 打主程序
│   └── installer/            # Inno Setup 脚本
├── 听小说应用/               # 绿色版（exe + 说明 + 示例）
├── 发布/                     # 安装包输出
├── VERSION                   # 默认版本号，例如 1.0.0
├── build_installer.bat       # 打安装包（入口）
└── build_installer.ps1       # 打安装包（实际逻辑）
```

## 数据目录

```text
%USERPROFILE%\.novel_listener\
├── library.json      # 书架
├── progress.json     # 进度
├── settings.json     # 设置
├── imports\          # 从压缩包解压出的文件
└── tts_cache\        # 语音缓存
```

## 许可证

仅供学习与个人使用。第三方依赖遵循各自许可证；语音服务来自 Microsoft Edge TTS，请遵守其服务条款。
