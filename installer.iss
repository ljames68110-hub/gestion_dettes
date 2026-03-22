; installer.iss — Script Inno Setup pour Gestion Perso
; Génère un installateur Windows professionnel

#define AppName "Gestion Perso"
#define AppVersion "1.0"
#define AppPublisher "Yoann L."
#define AppExeName "GestionPerso.exe"
#define AppId "{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Gestion Perso
DefaultGroupName={#AppName}
AllowNoIcons=no
OutputDir=installer_output
OutputBaseFilename=Gestion Perso_Setup
SetupIconFile=app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
CloseApplications=yes
RestartApplications=no
; Créer un dossier data dans AppData pour la base de données
UsePreviousAppDir=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked
Name: "startupicon"; Description: "Lancer au démarrage de Windows"; GroupDescription: "Démarrage :"; Flags: unchecked

[Files]
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Menu Démarrer
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Désinstaller {#AppName}"; Filename: "{uninstallexe}"
; Bureau (optionnel)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Lancer au démarrage (optionnel)
Root: HKCU; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#AppName}"; \
  ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Proposer de lancer l'app après installation
Filename: "{app}\{#AppExeName}"; \
  Description: "Lancer {#AppName} maintenant"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Fermer l'app avant désinstallation
Filename: "taskkill.exe"; Parameters: "/F /IM {#AppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

[Code]
// Vérifier si l'app tourne avant de désinstaller
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // La base dettes.db est dans AppData — on ne la supprime pas
    // L'utilisateur garde ses données même après désinstallation
  end;
end;
