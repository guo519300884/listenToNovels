; 听小说 — Inno Setup 安装脚本
; 请用项目根目录 build_installer.bat / build_installer.ps1 打包（可自定义版本号）

#define MyAppName "听小说"
; version_defines.iss 由打包脚本自动生成；若不存在则使用下面的默认值
#ifexist "version_defines.iss"
  #include "version_defines.iss"
#endif
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#ifndef MyAppVersionInfo
  #define MyAppVersionInfo "1.0.0.0"
#endif
#define MyAppPublisher "听小说"
#define MyAppExeName "听小说.exe"

[Setup]
AppId={{A7E3C2B1-9F4D-4A8E-B6C1-2D8F0E1A3B7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\..\发布
OutputBaseFilename=听小说安装包_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoProductName={#MyAppName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} 安装程序
DisableProgramGroupPage=yes
DisableWelcomePage=no
InfoBeforeFile=安装说明.txt

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: checkedonce

[Files]
Source: "..\..\听小说应用\听小说.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\听小说应用\使用说明.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\听小说应用\示例小说.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\听小说应用\测试小说.docx"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\听小说应用\示例小说.docx"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\使用说明"; Filename: "{app}\使用说明.md"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动听小说"; Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*.log"
