; =============================================================================
; HLS Downloader Pro — instalador Windows (Inno Setup 6)
;
; Build (a partir da raiz do repositório):
;   iscc /DAppVersion=1.3.0 installer\HLS-Downloader-Pro.iss
;
; Pré-requisito: dist\HLS-Downloader-Pro\ (build PyInstaller --onedir).
; Instalação POR USUÁRIO (sem admin) por padrão, com opção de "para todos".
; =============================================================================

#ifndef AppVersion
  #define AppVersion "1.3.0"
#endif

#define AppName "HLS Downloader Pro"
#define AppPublisher "Landre Codes"
#define AppExeName "HLS-Downloader-Pro.exe"
; GUID fixo: NÃO altere (é a identidade do app para upgrades/desinstalação).
#define AppId "{{C7A3E5B2-9F14-4D6A-8E21-5B0C7D93A1F4}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\installer
OutputBaseFilename=HLS-Downloader-Pro-{#AppVersion}-setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
; Detecta o mutex criado pelo app (hlsdl/app.py) e evita instalar com ele aberto.
AppMutex=HLS-Downloader-Pro-Mutex
LicenseFile=..\LICENSE

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\HLS-Downloader-Pro\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Não remove %APPDATA%\HLSDownloaderPro (settings/logs/ferramentas baixadas):
; o usuário pode querer mantê-los ao reinstalar.
Type: files; Name: "{app}\portable.flag"
