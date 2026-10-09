; Coding Tools MCP fork-only desktop distribution.
; ISCC /DDesktopVersion=0.5.0.1 /DSourceDir=... /DOutputDir=... installer.iss

#ifndef DesktopVersion
  #error "DesktopVersion must be defined by build-windows.ps1"
#endif
#ifndef SourceDir
  #error "SourceDir must be defined by build-windows.ps1"
#endif
#ifndef OutputDir
  #error "OutputDir must be defined by build-windows.ps1"
#endif

[Setup]
AppId={{7D25E39E-47F8-48B1-94BE-3B9DF045C87B}
AppName=Coding Tools MCP Desktop
AppVersion={#DesktopVersion}
AppPublisher=Yyu-ang (fork of xyTom/coding-tools-mcp)
AppPublisherURL=https://github.com/Yyu-ang/coding-tools-mcp
AppSupportURL=https://github.com/Yyu-ang/coding-tools-mcp
DefaultDirName={localappdata}\Programs\CodingToolsMCP
DefaultGroupName=Coding Tools MCP Desktop
UninstallDisplayIcon={app}\CodingToolsMCP.exe
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
MinVersion=10.0
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
OutputDir={#OutputDir}
OutputBaseFilename=CodingToolsMCP_Desktop_{#DesktopVersion}_x64_Setup

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Coding Tools MCP Desktop"; Filename: "{app}\CodingToolsMCP.exe"
Name: "{autodesktop}\Coding Tools MCP Desktop"; Filename: "{app}\CodingToolsMCP.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CodingToolsMCP.exe"; Description: "Launch Coding Tools MCP Desktop"; Flags: nowait postinstall skipifsilent
