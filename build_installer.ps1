# 听小说 — 生成 Windows 安装包（支持自定义版本号）
# 用法:
#   .\build_installer.ps1
#   .\build_installer.ps1 -Version 1.2.0
#   build_installer.bat 1.2.0

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$AppDir = Join-Path $Root "听小说应用"
$DistDir = Join-Path $Root "novel_listener\dist"
$Iss = Join-Path $Root "novel_listener\installer\听小说.iss"
$OutDir = Join-Path $Root "发布"
$VersionFile = Join-Path $Root "VERSION"
$DefineFile = Join-Path $Root "novel_listener\installer\version_defines.iss"

Write-Host "========================================"
Write-Host "  听小说 — 生成 Windows 安装包"
Write-Host "========================================"
Write-Host ""

function Read-DefaultVersion {
    if (Test-Path $VersionFile) {
        $v = (Get-Content -LiteralPath $VersionFile -Raw -Encoding UTF8).Trim()
        if ($v) { return $v }
    }
    return "1.0.0"
}

function Normalize-VersionInfo([string]$ver) {
    $parts = @($ver.Split(".") | Where-Object { $_ -ne "" })
    if ($parts.Count -lt 1 -or $parts.Count -gt 4) {
        throw "版本号最多 4 段，例如 1.2.3 或 1.2.3.4"
    }
    foreach ($p in $parts) {
        if ($p -notmatch '^\d+$') {
            throw "版本号每段必须是数字: $ver"
        }
    }
    while ($parts.Count -lt 4) { $parts += "0" }
    return ($parts -join ".")
}

# ---------- 解析版本号 ----------
if (-not $Version) {
    $default = Read-DefaultVersion
    Write-Host "当前默认版本: $default"
    $inputVer = Read-Host "请输入版本号（直接回车使用默认）"
    if ([string]::IsNullOrWhiteSpace($inputVer)) {
        $Version = $default
    } else {
        $Version = $inputVer.Trim()
    }
} else {
    $Version = $Version.Trim()
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "版本号不能为空"
}
if ($Version -notmatch '^\d+(\.\d+){0,3}$') {
    throw "版本号格式无效: $Version（请用 1.0.0 或 1.2.3.4）"
}

$VerInfo = Normalize-VersionInfo $Version
Set-Content -LiteralPath $VersionFile -Value $Version -Encoding ascii -NoNewline
# 补一个换行，方便记事本查看
Add-Content -LiteralPath $VersionFile -Value "" -Encoding ascii

Write-Host "[信息] 安装包版本: $Version"
Write-Host "[信息] 文件版本号: $VerInfo"
Write-Host ""

# ---------- 准备主程序 ----------
$AppExe = Join-Path $AppDir "听小说.exe"
$DistExe = Join-Path $DistDir "听小说.exe"
if (-not (Test-Path -LiteralPath $AppExe)) {
    if (Test-Path -LiteralPath $DistExe) {
        Write-Host "[信息] 从 dist 复制听小说.exe ..."
        New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
        Copy-Item -LiteralPath $DistExe -Destination $AppExe -Force
    }
}
if (-not (Test-Path -LiteralPath $AppExe)) {
    throw "找不到听小说.exe，请先运行 novel_listener\build_exe.bat"
}
if (-not (Test-Path -LiteralPath $Iss)) {
    throw "找不到安装脚本: $Iss"
}

# ---------- 查找 ISCC ----------
$isccCandidates = @(
    (Join-Path $env:LocalAppData "Programs\Inno Setup 6\ISCC.exe"),
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $isccCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $Iscc) {
    throw "未找到 Inno Setup 6（ISCC.exe）。请先执行: winget install JRSoftware.InnoSetup"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# 用临时 defines 文件传版本，避免 cmd /D 引号被吃掉
$defineText = @"
; 由 build_installer.ps1 自动生成，请勿手工长期修改
#define MyAppVersion "$Version"
#define MyAppVersionInfo "$VerInfo"
"@
Set-Content -LiteralPath $DefineFile -Value $defineText -Encoding UTF8

$outName = "听小说安装包_v$Version.exe"
Write-Host "[信息] 编译安装包..."
Write-Host "       脚本: $Iss"
Write-Host "       输出: $(Join-Path $OutDir $outName)"
Write-Host ""

& $Iscc $Iss
if ($LASTEXITCODE -ne 0) {
    throw "安装包编译失败（退出码 $LASTEXITCODE）"
}

$built = Join-Path $OutDir $outName
if (-not (Test-Path -LiteralPath $built)) {
    Write-Host "[警告] 未找到预期文件名，请检查 发布 目录中的 exe"
    Get-ChildItem -LiteralPath $OutDir -Filter "*.exe" | ForEach-Object { Write-Host " - $($_.Name)" }
} else {
    Write-Host ""
    Write-Host "[完成] 已生成: 发布\$outName"
    Write-Host "       大小: $([math]::Round((Get-Item -LiteralPath $built).Length / 1MB, 1)) MB"
}

try { Invoke-Item $OutDir } catch {}
