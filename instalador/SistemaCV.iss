; ===========================================================================
;  SistemaCV.iss — Inno Setup 6
;  Para compilar: doble clic en compilar.bat
; ===========================================================================

#define AppName      "Sistema CV RRHH"
#define AppVersion   "1.0"
#define AppPublisher "Tu Empresa"
#define AppURL       "http://127.0.0.1:8000"
#define SrcRoot      ".."

; ===========================================================================
[Setup]
; ===========================================================================
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
AppId={{8B4F2C3A-1E9D-4F7B-A2C8-3D6E5F8A9B0C}

SourceDir={#SrcRoot}

DefaultDirName=C:\SistemaCV
DefaultGroupName={#AppName}

OutputDir=dist_instalador
OutputBaseFilename=SistemaCV_Instalador

Compression=lzma2/ultra64
SolidCompression=yes

WizardStyle=modern
WizardSizePercent=110

PrivilegesRequired=admin
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

DisableWelcomePage=no
ShowLanguageDialog=auto

UninstallDisplayIcon={sys}\shell32.dll,137
UninstallDisplayName={#AppName}
CreateUninstallRegKey=yes


; ===========================================================================
[Languages]
; ===========================================================================
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"


; ===========================================================================
[Dirs]
; ===========================================================================
Name: "{app}\logs"
Name: "{app}\backend\database"
Name: "{app}\backend\storage\cvs"
Name: "{app}\backend\storage\exports"


; ===========================================================================
[Files]
; ===========================================================================

; --- Raiz del proyecto -------------------------------------------------------
Source: "instalar.bat";           DestDir: "{app}"; Flags: ignoreversion
Source: "iniciar.bat";            DestDir: "{app}"; Flags: ignoreversion
Source: "iniciar_gpu.bat";        DestDir: "{app}"; Flags: ignoreversion
Source: "detener.bat";            DestDir: "{app}"; Flags: ignoreversion
Source: "verificar.bat";          DestDir: "{app}"; Flags: ignoreversion
Source: "README_INSTALACION.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md";              DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "run_system.py";          DestDir: "{app}"; Flags: ignoreversion

; --- Backend -----------------------------------------------------------------
Source: "backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "venv,venv\*,__pycache__,__pycache__\*,*.pyc,*.pyo,database\*.db,database\*.sqlite,database\*.sqlite3,logs,logs\*,config.json,tests,tests\*,.env"
Source: "backend\.env.example"; DestDir: "{app}\backend"; Flags: ignoreversion

; --- Frontend ----------------------------------------------------------------
Source: "frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "node_modules,node_modules\*,dist,dist\*,.cache,.cache\*,*.local"
; Si dist\ ya existe al compilar, incluirlo para instalacion offline
Source: "frontend\dist\*"; DestDir: "{app}\frontend\dist"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; --- Documentacion -----------------------------------------------------------
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist


; ===========================================================================
[Icons]
; ===========================================================================

; Escritorio
Name: "{userdesktop}\Sistema CV - Iniciar"; Filename: "{app}\iniciar.bat"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 137; Comment: "Iniciar Sistema CV RRHH"
Name: "{userdesktop}\Sistema CV - Detener"; Filename: "{app}\detener.bat"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 131; Comment: "Detener Sistema CV RRHH"

; Menu Inicio
Name: "{group}\Iniciar Sistema";          Filename: "{app}\iniciar.bat";            WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 137
Name: "{group}\Iniciar con GPU (NVIDIA)"; Filename: "{app}\iniciar_gpu.bat";        WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 137
Name: "{group}\Detener Sistema";          Filename: "{app}\detener.bat";            WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 131
Name: "{group}\Verificar instalacion";    Filename: "{app}\verificar.bat";          WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 21
Name: "{group}\README - Instrucciones";   Filename: "{app}\README_INSTALACION.txt"
Name: "{group}\Desinstalar {#AppName}";   Filename: "{uninstallexe}";               IconFilename: "{sys}\shell32.dll"; IconIndex: 131


; ===========================================================================
[Registry]
; ===========================================================================
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey


; ===========================================================================
[Run]
; ===========================================================================

; Ejecutar instalar.bat en ventana CMD visible — el usuario ve el progreso
Filename: "cmd.exe"; Parameters: "/c ""{app}\instalar.bat"""; WorkingDir: "{app}"; StatusMsg: "Instalando dependencias... esto puede tardar 10-30 minutos"; Flags: shellexec waituntilterminated

; Checkbox opcional al final para iniciar el sistema
Filename: "{app}\iniciar.bat"; Description: "Iniciar el sistema ahora"; StatusMsg: "Iniciando el sistema..."; Flags: postinstall shellexec nowait unchecked; WorkingDir: "{app}"


; ===========================================================================
[UninstallRun]
; ===========================================================================
Filename: "{app}\detener.bat"; Flags: shellexec waituntilterminated skipifdoesntexist; WorkingDir: "{app}"


; ===========================================================================
[UninstallDelete]
; ===========================================================================
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\backend\database"
Type: files;          Name: "{app}\backend\.env"
Type: files;          Name: "{app}\backend\config.json"
Type: filesandordirs; Name: "{app}\frontend\dist"
Type: filesandordirs; Name: "{app}\frontend\node_modules"
Type: files;          Name: "{app}\instalacion.log"
Type: files;          Name: "{app}\verificacion.log"


; ===========================================================================
[Code]

// Mostrar requisitos minimos al arrancar el wizard
function InitializeSetup(): Boolean;
begin
  Result := (MsgBox(
    'Requisitos minimos:' + #13#10 +
    '  Windows 10/11 64-bit' + #13#10 +
    '  8 GB RAM minimo' + #13#10 +
    '  10 GB espacio libre' + #13#10 +
    '  Conexion a Internet' + #13#10 + #13#10 +
    'La instalacion puede tardar 10-30 minutos.' + #13#10 +
    'Desea continuar?',
    mbConfirmation, MB_YESNO) = IDYES);
end;


// Advertir si la ruta de instalacion tiene espacios
function NextButtonClick(CurPageID: Integer): Boolean;
var
  InstDir: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    InstDir := WizardDirValue;
    if Pos(' ', InstDir) > 0 then
      if MsgBox(
        'La ruta tiene espacios: ' + InstDir + #13#10 +
        'Puede causar problemas. Recomendado: C:\SistemaCV' + #13#10 +
        'Continuar de todas formas?',
        mbConfirmation, MB_YESNO) = IDNO then
        Result := False;
  end;
end;


// Preguntar si borrar datos al desinstalar
var
  DeleteData: Boolean;

function InitializeUninstall(): Boolean;
begin
  DeleteData := (MsgBox(
    'Desea borrar tambien los datos?' + #13#10 +
    '  Base de datos, CVs y reportes' + #13#10 +
    'Si elige No, los datos se conservan.',
    mbConfirmation, MB_YESNO) = IDYES);
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and DeleteData then
    DelTree(ExpandConstant('{app}\backend\storage'), True, True, True);
end;
