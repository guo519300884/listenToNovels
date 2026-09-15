# 发布说明

## 发给别人

把 `发布\` 里对应版本的安装包发出去即可，例如：

**`听小说安装包_v1.2.0.exe`**

对方双击 → 选目录 → 完成安装。

## 自己重新打包

### 1. 先打主程序（有更新时）

```bat
novel_listener\build_exe.bat
```

把生成的 `dist\听小说.exe` 放到 `听小说应用\听小说.exe`。

### 2. 再打安装包（自定义版本）

在项目**根目录**：

```bat
build_installer.bat 1.2.0
```

或双击 `build_installer.bat`，按提示输入版本号。

### 3. 输出

```text
发布\听小说安装包_v1.2.0.exe
```

## 版本号

- 格式：`1.0.0` 或 `1.2.3.4`
- 成功后写入根目录 `VERSION`，下次默认用它
- 也可先改 `VERSION` 文件，再直接运行 `build_installer.bat` 回车确认

## 常见问题

| 现象 | 处理 |
|------|------|
| 找不到听小说.exe | 先运行 `novel_listener\build_exe.bat` |
| 找不到 ISCC.exe | `winget install JRSoftware.InnoSetup` |
| 版本一直是 1.0.0 | 用 `build_installer.bat 1.2.0` 显式指定 |
| 双击 bat 一闪而过 | 看报错；失败时脚本会 `pause` |

## 其他

- 可选创建桌面快捷方式
- 卸载不会删除 `%USERPROFILE%\.novel_listener` 里的听书进度
