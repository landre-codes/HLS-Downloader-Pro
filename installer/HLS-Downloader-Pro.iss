; =============================================================================
; HLS Downloader Pro — instalador Windows (Inno Setup 6.3+ / 7.x)
;
; Build (a partir da raiz do repositório):
;   iscc /DAppVersion=1.5.0 installer\HLS-Downloader-Pro.iss
;
; Pré-requisito: dist\HLS-Downloader-Pro\ (build PyInstaller --onedir).
; Instalação POR USUÁRIO (sem admin) por padrão, com opção de "para todos".
; =============================================================================

#if VER < EncodeVer(6,3,0)
  #error "Requer Inno Setup 6.3 ou superior (recomendado 7.x)."
#endif

#ifndef AppVersion
  #define AppVersion "1.5.0"
#endif

#define AppName "HLS Downloader Pro"
#define AppPublisher "Landre Codes"
#define AppExeName "HLS-Downloader-Pro.exe"
#define AppURL "https://github.com/landre-codes/HLS-Downloader-Pro"
; GUID fixo: NÃO altere (é a identidade do app para upgrades/desinstalação).
#define AppId "{{C7A3E5B2-9F14-4D6A-8E21-5B0C7D93A1F4}"
#define AppDistDir "..\dist\HLS-Downloader-Pro"
#define AppDistExe AppDistDir + "\" + AppExeName

; --- Validações em tempo de compilação --------------------------------------
; Falhas claras antes de gerar um instalador incompleto.
#if !DirExists(AppDistDir)
  #error "Build não encontrado em dist\HLS-Downloader-Pro. Gere com PyInstaller --onedir antes de compilar o instalador."
#endif
#if !FileExists(AppDistExe)
  #error "Executável não encontrado em dist\HLS-Downloader-Pro\HLS-Downloader-Pro.exe."
#endif
#if !DirExists(AppDistDir + "\_internal")
  #error "Pasta _internal ausente. O instalador espera um build PyInstaller --onedir."
#endif
#if !FileExists("..\assets\icon.ico")
  #error "Ícone não encontrado em assets\icon.ico."
#endif
#if !FileExists("..\README.md")
  #error "README.md não encontrado na raiz do repositório."
#endif
#if !FileExists("..\LICENSE")
  #error "LICENSE não encontrado na raiz do repositório."
#endif
#if !FileExists("..\THIRD_PARTY_NOTICES.md")
  #error "THIRD_PARTY_NOTICES.md não encontrado na raiz do repositório."
#endif
#if !FileExists("..\CHANGELOG.md")
  #error "CHANGELOG.md não encontrado na raiz do repositório."
#endif

; Aviso (não fatal) quando o exe empacotado foi gerado com outra versão.
#define AppExeVersion GetFileProductVersionString(AppDistExe)
#if AppExeVersion != AppVersion
  #pragma message "AVISO: exe em dist está na versão " + AppExeVersion + \
    ", mas o instalador foi configurado para " + AppVersion + ". Rebuild o app antes de publicar."
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
AppCopyright=Copyright (C) 2026 {#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoCopyright=Copyright (C) 2026 {#AppPublisher}
VersionInfoDescription={#AppName} installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=HLS-Downloader-Pro-{#AppVersion}-setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
; Inno Setup 7 gera um instalador 64-bit nativo; no 6.3+ usamos o modo antigo.
#if VER >= EncodeVer(7,0,0)
SetupArchitecture=x64
#else
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#endif
CloseApplications=yes
RestartApplications=no
; Detecta o mutex criado pelo app (hlsdl/app.py) e evita instalar com ele aberto.
AppMutex=HLS-Downloader-Pro-Mutex
LicenseFile=..\LICENSE

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "hebrew"; MessagesFile: "compiler:Languages\Hebrew.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Remove o runtime antigo antes de copiar o novo, evitando sobras de módulos
; que não existem mais. Dados do usuário ficam fora de _internal e são mantidos.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#AppDistDir}\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; \
  Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallDelete]
; Não remove %APPDATA%\HLSDownloaderPro (settings/logs/ferramentas baixadas):
; o usuário pode querer mantê-los ao reinstalar.
; Em modo portátil, remove apenas o marcador; settings/logs/tools permanecem.
Type: files; Name: "{app}\portable.flag"
