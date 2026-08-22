; Inno Setup скрипт для NurBooks Desktop
; Сборка: ISCC.exe installer-nurbooks.iss  (из корня репо, после flet pack)

#define MyAppName "NurBooks"
#define MyAppVersion "1.4.0"
#define MyAppPublisher "NurApps"
#define MyAppExeName "NurBooks.exe"

[Setup]
AppId={{838AA0C4-6EBE-4CEA-8519-41A3BB9906FC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist\installer-nurbooks
OutputBaseFilename=installer-nurbooks
SetupIconFile=assets\logo.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\NurBooks.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\downloads"
Name: "{app}\saved_books"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Пользовательские данные (скачанные книги) не удаляем — только пустые служебные папки
Name: "{app}\downloads"; Type: dirifempty
Name: "{app}\saved_books"; Type: dirifempty
