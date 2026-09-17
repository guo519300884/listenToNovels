/*
 * 听小说绿色版启动器
 * 首次解压 runtime_pack.zip → runtime\，再用内置 Python 运行 app\app.py
 *
 * 编译:
 *   x86_64-w64-mingw32-gcc -O2 -municode -mwindows -o 听小说.exe listen_launcher.c
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

static void trim_exe_dir(wchar_t *path) {
    wchar_t *slash = wcsrchr(path, L'\\');
    if (slash) {
        *slash = L'\0';
    }
}

static int path_exists(const wchar_t *path) {
    return GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES;
}

static void path_join(wchar_t *out, size_t n, const wchar_t *a, const wchar_t *b) {
    _snwprintf(out, n, L"%s\\%s", a, b);
    out[n - 1] = L'\0';
}

static int run_process(wchar_t *cmdline, const wchar_t *cwd, int wait) {
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD exit_code = 1;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    if (wait) {
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_HIDE;
    }
    ZeroMemory(&pi, sizeof(pi));

    if (!CreateProcessW(NULL, cmdline, NULL, NULL, FALSE,
                        wait ? CREATE_NO_WINDOW : 0, NULL, cwd, &si, &pi)) {
        return 0;
    }
    if (wait) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        GetExitCodeProcess(pi.hProcess, &exit_code);
    }
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return wait ? (exit_code == 0) : 1;
}

static int prepare_runtime(const wchar_t *base) {
    wchar_t pythonw[MAX_PATH];
    wchar_t zip_path[MAX_PATH];
    wchar_t cmd[8192];

    path_join(pythonw, MAX_PATH, base, L"runtime\\pythonw.exe");
    if (path_exists(pythonw)) {
        return 1;
    }

    path_join(zip_path, MAX_PATH, base, L"runtime_pack.zip");
    if (!path_exists(zip_path)) {
        MessageBoxW(NULL,
            L"缺少 runtime_pack.zip，无法准备运行环境。\n请保留绿色版目录完整文件后再试。",
            L"听小说", MB_OK | MB_ICONERROR);
        return 0;
    }

    MessageBoxW(NULL,
        L"首次启动需解压运行环境，大约半分钟。\n点击确定后开始准备。",
        L"听小说", MB_OK | MB_ICONINFORMATION);

    /* PowerShell Expand-Archive；优先保留已有的 app\app.py（仓库内最新源码） */
    _snwprintf(cmd, 8192,
        L"powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \""
        L"$ErrorActionPreference='Stop';"
        L"$base=r'%s'; $zip=r'%s';"
        L"$dest=Join-Path $base '_extract_tmp';"
        L"if (Test-Path $dest) { Remove-Item $dest -Recurse -Force };"
        L"Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force;"
        L"$root=Join-Path $dest '听小说便携版';"
        L"if (-not (Test-Path (Join-Path $root 'runtime\\pythonw.exe'))) {"
        L"  $cand=Get-ChildItem $dest -Directory | Select-Object -First 1;"
        L"  if ($cand) { $root=$cand.FullName }"
        L"};"
        L"$rt=Join-Path $base 'runtime';"
        L"if (Test-Path $rt) { Remove-Item $rt -Recurse -Force };"
        L"Move-Item (Join-Path $root 'runtime') $rt;"
        L"$app=Join-Path $base 'app';"
        L"New-Item -ItemType Directory -Force -Path $app | Out-Null;"
        L"$src=Join-Path $root 'app\\app.py';"
        L"$dst=Join-Path $app 'app.py';"
        L"if ((Test-Path $src) -and (-not (Test-Path $dst))) { Copy-Item $src $dst -Force };"
        L"Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue;"
        L"if (-not (Test-Path (Join-Path $rt 'pythonw.exe'))) { exit 1 }"
        L"\"",
        base, zip_path);
    cmd[8191] = L'\0';

    if (!run_process(cmd, base, 1) || !path_exists(pythonw)) {
        MessageBoxW(NULL,
            L"解压运行环境失败。请确认已安装 PowerShell，并完整保留绿色版文件。",
            L"听小说", MB_OK | MB_ICONERROR);
        return 0;
    }
    return 1;
}

static int launch_app(const wchar_t *base) {
    wchar_t pythonw[MAX_PATH];
    wchar_t script[MAX_PATH];
    wchar_t home[MAX_PATH];
    wchar_t pypath[MAX_PATH];
    wchar_t new_path[4096];
    wchar_t cmd[2048];
    const wchar_t *old_path;

    path_join(pythonw, MAX_PATH, base, L"runtime\\pythonw.exe");
    path_join(script, MAX_PATH, base, L"app\\app.py");
    if (!path_exists(script)) {
        MessageBoxW(NULL, L"缺少 app\\app.py，无法启动。", L"听小说", MB_OK | MB_ICONERROR);
        return 0;
    }

    path_join(home, MAX_PATH, base, L"runtime");
    path_join(pypath, MAX_PATH, base, L"app");
    old_path = _wgetenv(L"PATH");
    _snwprintf(new_path, 4096, L"%s;%s\\DLLs;%s\\Scripts;%s",
               home, home, home, old_path ? old_path : L"");
    new_path[4095] = L'\0';

    SetEnvironmentVariableW(L"PYTHONHOME", home);
    SetEnvironmentVariableW(L"PYTHONPATH", pypath);
    SetEnvironmentVariableW(L"PYTHONUTF8", L"1");
    SetEnvironmentVariableW(L"PATH", new_path);

    _snwprintf(cmd, 2048, L"\"%s\" \"%s\"", pythonw, script);
    cmd[2047] = L'\0';

    if (!run_process(cmd, base, 0)) {
        MessageBoxW(NULL, L"启动失败：无法运行内置 Python。", L"听小说", MB_OK | MB_ICONERROR);
        return 0;
    }
    return 1;
}

int WINAPI wWinMain(HINSTANCE hi, HINSTANCE hp, PWSTR cmd, int show) {
    wchar_t base[MAX_PATH];
    (void)hi; (void)hp; (void)cmd; (void)show;

    if (!GetModuleFileNameW(NULL, base, MAX_PATH)) {
        MessageBoxW(NULL, L"无法定位程序目录。", L"听小说", MB_OK | MB_ICONERROR);
        return 1;
    }
    trim_exe_dir(base);

    if (!prepare_runtime(base)) return 1;
    if (!launch_app(base)) return 1;
    return 0;
}
