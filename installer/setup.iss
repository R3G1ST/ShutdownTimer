#define MyAppVersion "1.0.1"
#define MyAppName "ShutdownTimer"
#define MyAppPublisher "R3G1ST"
#define MyAppExeName "ShutdownTimer.exe"

[Setup]
AppId={{8F2C6A17-4B93-4E5D-9C08-5D1E7B3A9F64}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ShutdownTimer
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=ShutdownTimer-Setup-{#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
SetupIconFile=..\resources\icon.ico
UninstallDisplayIcon={app}\ShutdownTimer.exe
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
CloseApplications=yes
UninstallDisplayName={#MyAppName}
AppCopyright=© R3G1ST
VersionInfoVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно"; Flags: unchecked
Name: "startup"; Description: "Запускать вместе с Windows"; GroupDescription: "Дополнительно"; Flags: unchecked

[Files]
Source: "..\dist\ShutdownTimer.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ShutdownTimer"; ValueData: """{app}\ShutdownTimer.exe"""; Flags: uninsdeletevalue; Tasks: startup
Root: HKCU; Subkey: "Software\Classes\shutdowntimer"; ValueType: string; ValueName: ""; ValueData: "URL:ShutdownTimer Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\shutdowntimer"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\shutdowntimer\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\ShutdownTimer.exe"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить ShutdownTimer"; Flags: nowait postinstall skipifsilent
