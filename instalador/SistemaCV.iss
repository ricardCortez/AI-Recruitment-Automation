; ===========================================================================
;  SistemaCV.iss — Script Inno Setup 6.x
;  Genera: SistemaCV_Instalador.exe
;
;  Para compilar: doble clic en compilar.bat
;  O desde Inno Setup IDE: File > Open > este archivo > Build > Compile
;
;  Estructura esperada al compilar:
;    instalador\
;      SistemaCV.iss         <- este archivo
;    (raiz del proyecto)\
;      instalar.bat
;      iniciar.bat
;      iniciar_gpu.bat
;      detener.bat
;      verificar.bat
;      README_INSTALACION.txt
;      backend\
;      frontend\
; ===========================================================================


; ---------------------------------------------------------------------------
;  Constantes globales (editar antes de compilar si es necesario)
; ---------------------------------------------------------------------------
#define AppName      "Sistema CV RRHH"
#define AppVersion   "1.0"
#define AppPublisher "Tu Empresa"
#define AppURL       "http://127.0.0.1:8000"
; Ruta relativa desde este .iss hasta la raiz del proyecto
#define SrcRoot      ".."


; ===========================================================================
;  [Setup] — Configuración global del instalador
; ===========================================================================
[Setup]

; Identificacion de la aplicacion
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Identificador unico para "Agregar o quitar programas" (no cambiar entre versiones)
AppId={{8B4F2C3A-1E9D-4F7B-A2C8-3D6E5F8A9B0C}

; Directorio fuente: raiz del proyecto (un nivel arriba de instalador\)
SourceDir={#SrcRoot}

; Destino de instalacion por defecto
DefaultDirName=C:\SistemaCV
DefaultGroupName={#AppName}

; Carpeta de salida del .exe compilado (relativa a SourceDir)
OutputDir=dist_instalador
OutputBaseFilename=SistemaCV_Instalador

; Compresion maxima (LZMA2 solido — mas lento al compilar, .exe mas pequeno)
Compression=lzma2/ultra64
SolidCompression=yes

; Apariencia del wizard
WizardStyle=modern
WizardSizePercent=110

; Privilegios y plataforma
PrivilegesRequired=admin
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Sin icono propio (no hay .ico en el proyecto)
; SetupIconFile=ruta\al\icono.ico

; Icono en "Agregar o quitar programas" → usamos shell32.dll
UninstallDisplayIcon={sys}\shell32.dll,137

; Desinstalador
CreateUninstallRegKey=yes
UninstallDisplayName={#AppName}

; Pantalla de bienvenida
DisableWelcomePage=no

; No mostrar "Listo para instalar" (se muestra instalar.bat en su lugar)
DisableReadyPage=no

; Mostrar progreso de descompresion
ShowTasksTreeLines=yes

; Idioma
ShowLanguageDialog=auto


; ===========================================================================
;  [Languages] — Idioma del instalador
; ===========================================================================
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"


; ===========================================================================
;  [Messages] — Textos personalizados del wizard
; ===========================================================================
[Messages]
; Mensaje de bienvenida
WelcomeLabel1=Bienvenido al instalador de {#AppName}
WelcomeLabel2=Este asistente instalar%c el sistema de reclutamiento con IA local.%n%nDurante la instalaci%cn se descargar%cn e instalar%cn autom%cticamente:%n%n  %b Python 3.12%n  %b Node.js 20 LTS%n  %b Ollama (motor de IA local)%n  %b Modelo de lenguaje qwen2.5:7b (~4 GB)%n%nRequiere conexi%cn a Internet.%n%nSe recomienda cerrar todas las aplicaciones antes de continuar.
; Pagina "Seleccionar directorio"
SelectDirLabel3=El sistema se instalar%c en la siguiente carpeta.
SelectDirBrowseLabel=Para continuar, haga clic en Siguiente. Si desea elegir otra carpeta, haga clic en Examinar.
; Pagina final
FinishedHeadingLabel=Instalaci%cn de {#AppName} completada
FinishedLabel=El sistema ha sido instalado. Puede iniciarlo desde el icono del Escritorio o el Men%z Inicio.


; ===========================================================================
;  [CustomMessages] — Mensajes adicionales propios
; ===========================================================================
[CustomMessages]
spanish.RunAfterInstall=Iniciar el sistema ahora
spanish.RequirementsTitle=Requisitos m%bnimos del sistema
spanish.RequirementsText=Este software requiere:%n%n  %b Windows 10 / 11 (64-bit)%n  %b 8 GB de RAM m%bnimo (16 GB recomendado)%n  %b 10 GB de espacio libre en disco%n  %b Conexi%cn a Internet durante la instalaci%cn%n%nSi el equipo no cumple estos requisitos, el rendimiento puede verse afectado.


; ===========================================================================
;  [Types] — Tipos de instalacion
; ===========================================================================
[Types]
Name: "full";    Description: "Instalacion completa (recomendada)"
Name: "custom";  Description: "Instalacion personalizada"; Flags: iscustom

; ===========================================================================
;  [Components] — Componentes seleccionables
; ===========================================================================
[Components]
Name: "main";        Description: "Sistema CV RRHH (obligatorio)"; Types: full custom; Flags: fixed
Name: "shortcuts";   Description: "Accesos directos en el Escritorio"; Types: full custom
Name: "startmenu";   Description: "Accesos directos en el Menu Inicio"; Types: full custom

Name: "deps";        Description: "Instalar dependencias automaticamente"; Types: full custom

Name: "deps\python"; Description: "Instalar Python 3.12 (requerido para backend)"; Types: full custom; Flags: checkablealone
Name: "deps\node"; Description: "Instalar Node.js LTS (requerido para frontend)"; Types: full custom; Flags: checkablealone
Name: "deps\ollama"; Description: "Instalar Ollama (motor local de IA)"; Types: full custom; Flags: checkablealone

; ===========================================================================
;  [Tasks] — Tareas opcionales durante la instalacion
; ===========================================================================
[Tasks]
Name: "desktopicon";    Description: "Crear acceso directo en el Escritorio"; \
      GroupDescription: "Accesos directos:"; \
      Components: shortcuts
Name: "startmenuicon";  Description: "Crear grupo en el Menu Inicio"; \
      GroupDescription: "Accesos directos:"; \
      Components: startmenu


; ===========================================================================
;  [Dirs] — Directorios a crear en el destino
; ===========================================================================
[Dirs]
; Carpeta raiz de la aplicacion (Inno Setup la crea automaticamente)
Name: "{app}"
; Subdirectorios necesarios en tiempo de ejecucion (instalar.bat los crea,
; pero los predefinimos para que el desinstalador los pueda limpiar)
Name: "{app}\logs"
Name: "{app}\backend\database"
Name: "{app}\backend\storage\cvs"
Name: "{app}\backend\storage\exports"
Name: "{app}\dist_instalador"; Flags: uninsneveruninstall


; ===========================================================================
;  [Files] — Archivos a copiar
;  SourceDir ya apunta a la raiz del proyecto (definido en [Setup])
;
;  Criterio de exclusion:
;    - node_modules\       (se regenera con npm install)
;    - frontend\dist\      (se genera con npm run build durante instalar.bat)
;    - backend\venv\       (prohibido por diseno — se usa Python global)
;    - __pycache__\        (bytecode generado automaticamente)
;    - *.pyc               (bytecode Python compilado)
;    - .git\               (historial de Git — innecesario en produccion)
;    - backend\database\*  (BD vacia — se genera en el primer inicio)
;    - backend\logs\*      (logs de ejecucion anteriores)
;    - backend\config.json (configuracion de usuario — no sobreescribir)
;    - build\ / dist\      (artefactos PyInstaller/Vite de desarrollo)
;    - SistemaCV.spec      (configuracion PyInstaller)
;    - instalador\         (este propio directorio, innecesario en destino)
; ===========================================================================
[Files]

; --- Archivos raiz -----------------------------------------------------------
Source: "instalar.bat";          DestDir: "{app}"; Flags: ignoreversion
Source: "iniciar.bat";           DestDir: "{app}"; Flags: ignoreversion
Source: "iniciar_gpu.bat";       DestDir: "{app}"; Flags: ignoreversion
Source: "detener.bat";           DestDir: "{app}"; Flags: ignoreversion
Source: "verificar.bat";         DestDir: "{app}"; Flags: ignoreversion
Source: "README_INSTALACION.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md";             DestDir: "{app}"; Flags: ignoreversion isreadme
; run_system.py — launcher Python alternativo
Source: "run_system.py";         DestDir: "{app}"; Flags: ignoreversion

; --- Backend -----------------------------------------------------------------
; Copiar todo el backend recursivamente, excluyendo directorios generados
Source: "backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "venv,venv\*,__pycache__,__pycache__\*,*.pyc,*.pyo,database\*.db,database\*.sqlite,database\*.sqlite3,logs,logs\*,config.json,tests,tests\*,.env"
; .env.example → siempre copiar (instalar.bat lo usa como plantilla)
Source: "backend\.env.example";  DestDir: "{app}\backend"; Flags: ignoreversion

; --- Frontend ----------------------------------------------------------------
; Solo copiar los fuentes; dist\ se construye durante instalar.bat
Source: "frontend\*"; DestDir: "{app}\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "node_modules,node_modules\*,dist,dist\*,.next,.next\*,.cache,.cache\*,*.local"

; --- Documentacion (si existe) -----------------------------------------------
Source: "docs\*"; \
    DestDir: "{app}\docs"; \
    Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; --- Instaladores de dependencias (modo offline / bundle) --------------------
; Estos archivos deben descargarse manualmente a instalador\deps\ antes de
; compilar el .iss para generar un instalador autocontenido offline.
; Si no existen, se ignoran en compilacion (skipifsourcedoesntexist).
; En ese caso instalar.bat los descarga de Internet en tiempo de instalacion.
; Para descargar:
;   python-3.12.0-amd64.exe -> https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
;   node-v20.11.0-x64.msi   -> https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi
;   OllamaSetup.exe          -> https://ollama.com/download/OllamaSetup.exe
Source: "instalador\deps\python-3.12.0-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist; Check: WizardIsComponentSelected('deps\python')
Source: "instalador\deps\node-v20.11.0-x64.msi";   DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist; Check: WizardIsComponentSelected('deps\node')
Source: "instalador\deps\OllamaSetup.exe";          DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist; Check: WizardIsComponentSelected('deps\ollama')


; ===========================================================================
;  [Icons] — Accesos directos
; ===========================================================================
[Icons]

; --- Escritorio --------------------------------------------------------------
; "Sistema CV - Iniciar"
Name: "{userdesktop}\Sistema CV - Iniciar"; \
    Filename: "{app}\iniciar.bat"; \
    WorkingDir: "{app}"; \
    IconFilename: "{sys}\shell32.dll"; IconIndex: 137; \
    Comment: "Iniciar Sistema CV RRHH"; \
    Tasks: desktopicon

; "Sistema CV - Detener"
Name: "{userdesktop}\Sistema CV - Detener"; \
    Filename: "{app}\detener.bat"; \
    WorkingDir: "{app}"; \
    IconFilename: "{sys}\shell32.dll"; IconIndex: 131; \
    Comment: "Detener Sistema CV RRHH"; \
    Tasks: desktopicon

; --- Menu Inicio → carpeta "Sistema CV RRHH" ---------------------------------
Name: "{group}\Iniciar Sistema";         \
    Filename: "{app}\iniciar.bat";        \
    WorkingDir: "{app}";                  \
    IconFilename: "{sys}\shell32.dll"; IconIndex: 137; \
    Tasks: startmenuicon

Name: "{group}\Iniciar con GPU (NVIDIA)"; \
    Filename: "{app}\iniciar_gpu.bat";    \
    WorkingDir: "{app}";                  \
    IconFilename: "{sys}\shell32.dll"; IconIndex: 137; \
    Tasks: startmenuicon

Name: "{group}\Detener Sistema";          \
    Filename: "{app}\detener.bat";        \
    WorkingDir: "{app}";                  \
    IconFilename: "{sys}\shell32.dll"; IconIndex: 131; \
    Tasks: startmenuicon

Name: "{group}\Verificar instalacion";   \
    Filename: "{app}\verificar.bat";      \
    WorkingDir: "{app}";                  \
    IconFilename: "{sys}\shell32.dll"; IconIndex: 21; \
    Tasks: startmenuicon

Name: "{group}\README - Instrucciones";  \
    Filename: "{app}\README_INSTALACION.txt"; \
    Tasks: startmenuicon

Name: "{group}\Desinstalar {#AppName}";  \
    Filename: "{uninstallexe}";           \
    IconFilename: "{sys}\shell32.dll"; IconIndex: 131; \
    Tasks: startmenuicon


; ===========================================================================
;  [Registry] — Entradas en el Registro de Windows
;  "Agregar o quitar programas" → HKLM\Software\...\Uninstall\<AppId>
;  Inno Setup las crea automaticamente; aqui añadimos metadatos extra.
; ===========================================================================
[Registry]
; Tamano estimado de la instalacion en KB (ajustar si cambia el proyecto)
Root: HKLM; \
    Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting('AppId')}_is1"; \
    ValueType: dword; ValueName: "EstimatedSize"; ValueData: "1572864"; \
    Flags: uninsdeletevalue

; URL de soporte visible en "Agregar o quitar programas"
Root: HKLM; \
    Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting('AppId')}_is1"; \
    ValueType: string; ValueName: "URLInfoAbout"; ValueData: "{#AppURL}"; \
    Flags: uninsdeletevalue

; Asociar la carpeta de instalacion para facilitar soporte
Root: HKLM; \
    Subkey: "Software\{#AppPublisher}\{#AppName}"; \
    ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; \
    Flags: uninsdeletekey


; ===========================================================================
;  [Run] — Acciones POST-instalacion
;
;  instalar.bat es ejecutado por [Code] CurStepChanged(ssInstall) con
;  una pagina de progreso que lee instalacion.log en tiempo real.
;  Aqui solo se incluye el refresco de PATH y el checkbox de inicio.
; ===========================================================================
[Run]

; Refrescar variables de entorno del sistema (Python/Node recien instalados)
; Nota: setx tiene limite de 1024 chars; si falla, no es critico.
Filename: "cmd.exe"; Parameters: "/c setx PATH ""%PATH%"" /M"; WorkingDir: "{app}"; StatusMsg: "Configurando variables de entorno..."; Flags: runhidden waituntilterminated skipifsilent

; Iniciar el sistema al terminar (checkbox desmarcado por defecto)
Filename: "{app}\iniciar.bat"; Description: "{cm:RunAfterInstall}"; StatusMsg: "Iniciando el sistema..."; Flags: postinstall shellexec nowait unchecked; WorkingDir: "{app}"


; ===========================================================================
;  [UninstallRun] — Acciones al desinstalar
; ===========================================================================
[UninstallRun]

; Detener el sistema antes de desinstalar
Filename: "{app}\detener.bat"; \
    Flags: shellexec waituntilterminated skipifdoesntexist; \
    WorkingDir: "{app}"


; ===========================================================================
;  [UninstallDelete] — Archivos/carpetas a borrar al desinstalar
;  (Inno Setup solo borra lo que el instalo; lo generado en runtime
;   debe listarse explicitamente aqui)
; ===========================================================================
[UninstallDelete]
; Logs generados en ejecucion
Type: filesandordirs; Name: "{app}\logs"
; Base de datos SQLite (confirmar con el usuario antes — ver [Code] abajo)
Type: filesandordirs; Name: "{app}\backend\database"
; Archivos de configuracion generados
Type: files; Name: "{app}\backend\.env"
Type: files; Name: "{app}\backend\config.json"
; Frontend compilado
Type: filesandordirs; Name: "{app}\frontend\dist"
Type: filesandordirs; Name: "{app}\frontend\node_modules"
; Log de instalacion
Type: files; Name: "{app}\instalacion.log"
Type: files; Name: "{app}\verificacion.log"


; ===========================================================================
;  [Code] — Pascal Script para logica personalizada
; ===========================================================================
[Code]

// ---------------------------------------------------------------------------
// InitializeSetup:
//   Muestra los requisitos minimos ANTES de mostrar el wizard.
//   Si el usuario cancela aqui, no se instala nada.
// ---------------------------------------------------------------------------
function InitializeSetup(): Boolean;
var
  Msg: String;
begin
  Msg := 'Requisitos minimos del sistema:' + #13#10 + #13#10 +
         '  • Windows 10 / 11 (64-bit)' + #13#10 +
         '  • 8 GB de RAM minimo (16 GB recomendado)' + #13#10 +
         '  • 10 GB de espacio libre en disco' + #13#10 +
         '  • Conexion a Internet durante la instalacion' + #13#10 + #13#10 +
         'El instalador descargara automaticamente:' + #13#10 +
         '  • Python 3.12' + #13#10 +
         '  • Node.js 20 LTS' + #13#10 +
         '  • Ollama (motor de IA local)' + #13#10 +
         '  • Modelo de IA qwen2.5:7b (~4 GB)' + #13#10 + #13#10 +
         'La instalacion puede tardar 10-30 minutos.' + #13#10 +
         'Desea continuar?';

  Result := (MsgBox(Msg, mbConfirmation, MB_YESNO) = IDYES);
end;

// ---------------------------------------------------------------------------
// InitializeUninstall:
//   Pregunta al usuario si quiere borrar tambien los datos (BD + CVs).
//   Si responde No, los datos se conservan aunque se desinstale el programa.
// ---------------------------------------------------------------------------
var
  DeleteUserData: Boolean;

function InitializeUninstall(): Boolean;
begin
  DeleteUserData := False;
  if MsgBox(
    'Desea eliminar tambien los datos del sistema?' + #13#10 + #13#10 +
    '  • Base de datos (candidatos, procesos, analisis)' + #13#10 +
    '  • CVs almacenados' + #13#10 +
    '  • Reportes exportados' + #13#10 + #13#10 +
    'Si elige No, los datos se conservaran en la carpeta de instalacion.',
    mbConfirmation, MB_YESNO) = IDYES then
  begin
    DeleteUserData := True;
  end;
  Result := True;
end;

// ---------------------------------------------------------------------------
// CurUninstallStepChanged:
//   Borra los datos de usuario solo si el usuario lo confirmo arriba.
// ---------------------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    if DeleteUserData then
    begin
      // Borrar CVs almacenados
      DelTree(AppDir + '\backend\storage', True, True, True);
      // Borrar exportaciones
      DelTree(AppDir + '\backend\storage\exports', True, True, True);
    end;
  end;
end;

// ---------------------------------------------------------------------------
// NextButtonClick:
//   Valida que el directorio de instalacion no tenga espacios en la ruta
//   (algunos scripts batch fallan con rutas con espacios sin comillas).
//   Advertencia, no bloqueo — el usuario puede ignorarla.
// ---------------------------------------------------------------------------
function NextButtonClick(CurPageID: Integer): Boolean;
var
  InstDir: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    InstDir := WizardDirValue;
    if Pos(' ', InstDir) > 0 then
    begin
      if MsgBox(
        'La ruta elegida contiene espacios:' + #13#10 +
        '  ' + InstDir + #13#10 + #13#10 +
        'Esto puede causar problemas en algunos scripts.' + #13#10 +
        'Se recomienda usar una ruta sin espacios (ej: C:\SistemaCV).' + #13#10 + #13#10 +
        'Desea continuar de todas formas?',
        mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end;
  end;
end;


// ---------------------------------------------------------------------------
// Variables globales
// ---------------------------------------------------------------------------
var
  ProgressPage: TOutputProgressWizardPage;
  // Deteccion pre-wizard de dependencias ya instaladas
  PythonYaInstalado:      Boolean;
  NodeYaInstalado:        Boolean;
  OllamaYaInstalado:      Boolean;
  //ComponentPageInitialized: Boolean;


// ---------------------------------------------------------------------------
// PythonInstalado / NodeInstalado / OllamaInstalado:
//   Detectan si cada dependencia ya esta presente en el sistema
//   consultando rutas conocidas y claves de Registro.
// ---------------------------------------------------------------------------
function PythonInstalado: Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{localappdata}\Programs\Python\Python312\python.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\Python\Python311\python.exe')) or
    FileExists('C:\Python312\python.exe') or
    FileExists('C:\Python311\python.exe') or
    FileExists('C:\Program Files\Python312\python.exe') or
    RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore\3.12') or
    RegKeyExists(HKLM, 'SOFTWARE\Python\PythonCore\3.11') or
    RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore\3.12') or
    RegKeyExists(HKCU, 'SOFTWARE\Python\PythonCore\3.11');
end;

function NodeInstalado: Boolean;
begin
  Result :=
    FileExists('C:\Program Files\nodejs\node.exe') or
    FileExists('C:\Program Files (x86)\nodejs\node.exe') or
    RegKeyExists(HKLM, 'SOFTWARE\Node.js') or
    RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\Node.js');
end;

function OllamaInstalado: Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe')) or
    FileExists('C:\Program Files\Ollama\ollama.exe') or
    RegKeyExists(HKLM, 'SOFTWARE\Ollama');
end;


// ---------------------------------------------------------------------------
// InitializeWizard:
//   Se ejecuta al arrancar el wizard (antes de mostrar ninguna pantalla).
//   Detecta dependencias ya instaladas para pre-configurar los checkboxes.
// ---------------------------------------------------------------------------
procedure InitializeWizard;
begin
  PythonYaInstalado       := PythonInstalado();
  NodeYaInstalado         := NodeInstalado();
  OllamaYaInstalado       := OllamaInstalado();
  //ComponentPageInitialized := False;
end;


// ---------------------------------------------------------------------------
// CurPageChanged:
//   Cuando se muestra la pagina de seleccion de componentes, desmarca
//   automaticamente los subcomponentes de dependencias ya instaladas
//   y actualiza su descripcion para informar al usuario.
//   Solo se ejecuta una vez (ComponentPageInitialized evita re-ejecucion).
// ---------------------------------------------------------------------------
//procedure CurPageChanged(CurPageID: Integer);
//var
//  CompList: TNewCheckListBox;
//  I: Integer;
//  Desc: String;
//begin
//  if (CurPageID = wpSelectComponents) and not ComponentPageInitialized then
//  begin
//    ComponentPageInitialized := True;
//    CompList := WizardForm.ComponentsList;
//
//    // Verificar que la lista tenga items antes de iterar
//    if CompList.Items.Count = 0 then Exit;
//
//    for I := 0 to CompList.Items.Count - 1 do
//    begin
//      // Segunda linea de defensa contra index out of bounds
//      if I >= CompList.Items.Count then Break;
//
 //     try
//        Desc := CompList.Items[I];
//
//        // Desmarcar Python si ya esta instalado
//        if (Pos('Python', Desc) > 0) and PythonYaInstalado then
//        begin
//          CompList.Checked[I] := False;
//          CompList.Items[I]   := Desc + '  [ya instalado]';
//        end
//        // Desmarcar Node si ya esta instalado
//        else if (Pos('Node', Desc) > 0) and NodeYaInstalado then
//        begin
//          CompList.Checked[I] := False;
//          CompList.Items[I]   := Desc + '  [ya instalado]';
//        end
//        // Desmarcar Ollama si ya esta instalado
//        else if (Pos('Ollama', Desc) > 0) and OllamaYaInstalado then
//        begin
//          CompList.Checked[I] := False;
//          CompList.Items[I]   := Desc + '  [ya instalado]';
//        end;
//
//      except
//        // Si un item falla, continuar con el siguiente sin romper el wizard
//      end;
//    end;
//  end;
//end;


// ---------------------------------------------------------------------------
// UpdateProgressFromLog:
//   Lee la ultima linea significativa de instalacion.log y actualiza
//   el texto de la pagina de progreso.
// ---------------------------------------------------------------------------
procedure UpdateProgressFromLog(const LogFile: String);
var
  Lines: TStringList;
  i: Integer;
  Line: String;
begin
  if not FileExists(LogFile) then Exit;
  Lines := TStringList.Create;
  try
    try
      Lines.LoadFromFile(LogFile);
    except
      Exit;  // Archivo bloqueado — ignorar y reintentar en siguiente ciclo
    end;
    // Buscar hacia atras la ultima linea no vacia y con contenido util
    for i := Lines.Count - 1 downto 0 do
    begin
      Line := Trim(Lines[i]);
      // Saltar lineas vacias, centinelas y timestamps puros
      if (Length(Line) > 4) and
         (Pos('[INSTALACION_COMPLETA]', Line) = 0) then
      begin
        if Length(Line) > 90 then
          Line := Copy(Line, 1, 90) + '...';
        ProgressPage.SetText('', Line);
        Break;
      end;
    end;
  finally
    Lines.Free;
  end;
end;


// ---------------------------------------------------------------------------
// IsInstallComplete:
//   Detecta si instalar.bat termino buscando el centinela en el log.
//   instalar.bat escribe "[INSTALACION_COMPLETA]" justo antes del pause.
// ---------------------------------------------------------------------------
function IsInstallComplete(const LogFile: String): Boolean;
var
  Lines: TStringList;
begin
  Result := False;
  if not FileExists(LogFile) then Exit;
  Lines := TStringList.Create;
  try
    try
      Lines.LoadFromFile(LogFile);
      Result := (Pos('[INSTALACION_COMPLETA]', Lines.Text) > 0);
    except
    end;
  finally
    Lines.Free;
  end;
end;


// ---------------------------------------------------------------------------
// RunInstallWithProgress:
//   Ejecuta instalar.bat en una ventana CMD visible (el usuario ve el output
//   detallado) y en paralelo muestra una pagina de progreso de Inno Setup
//   que lee instalacion.log cada 1.5 segundos para mostrar la linea actual.
//
//   Llamar desde CurStepChanged(ssInstall), que se dispara justo despues
//   de que Inno Setup copia los archivos y antes de ejecutar [Run].
// ---------------------------------------------------------------------------
procedure RunInstallWithProgress(const AppDir: String);
var
  ResultCode: Integer;
  Params: String;
begin
  Log('Ejecutando instalador principal...');

  Params :=
    '/c set INSTALL_PYTHON=' + IntToStr(Ord(WizardIsComponentSelected('deps\python'))) +
    ' && set INSTALL_NODE='   + IntToStr(Ord(WizardIsComponentSelected('deps\node'))) +
    ' && set INSTALL_OLLAMA=' + IntToStr(Ord(WizardIsComponentSelected('deps\ollama'))) +
    ' && call instalar.bat';

  Exec(
    ExpandConstant('{cmd}'),
    Params,
    ExpandConstant('{app}'),
    SW_SHOW,
    ewWaitUntilTerminated,
    ResultCode
  );

  Log('Instalador terminado. Codigo: ' + IntToStr(ResultCode));
end;

  // Esperar hasta 15 segundos a que aparezca el log
  Elapsed := 0;
  while not FileExists(LogFile) and (Elapsed < 15) do
  begin
    Sleep(1000);
    Inc(Elapsed);
    WizardForm.Update;
  end;

  // Bucle de polling: leer log + actualizar UI + detectar centinela
  Elapsed := 0;
  while Elapsed < MaxWait do
  begin
    Sleep(1500);
    Inc(Elapsed);

    // Progreso estimado: satura en 95% y solo llega a 100% con el centinela
    if Elapsed < 95 then
      ProgressPage.SetProgress(Elapsed, 100)
    else
      ProgressPage.SetProgress(95, 100);

    UpdateProgressFromLog(LogFile);
    WizardForm.Update;

    if IsInstallComplete(LogFile) then
    begin
      ProgressPage.SetProgress(100, 100);
      ProgressPage.SetText('', 'Instalacion de dependencias completada exitosamente.');
      WizardForm.Update;
      Sleep(2000);
      Break;
    end;
  end;

  ProgressPage.Hide;
end;


// ---------------------------------------------------------------------------
// CurStepChanged:
//   ssInstall se dispara justo despues de copiar archivos y antes de [Run].
//   Si existen instaladores empaquetados en {tmp}, los ejecuta primero
//   (silenciosamente y esperando a que terminen) para que instalar.bat
//   encuentre Python/Node/Ollama ya disponibles y omita la descarga.
//   Luego lanza instalar.bat con la pantalla de progreso.
// ---------------------------------------------------------------------------
procedure CurStepChanged(CurStep: TSetupStep);
var
  TmpDir: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    TmpDir := ExpandConstant('{tmp}');

    // Instalar Python desde bundle (si fue empaquetado y seleccionado)
    if WizardIsComponentSelected('deps\python') and
       FileExists(TmpDir + '\python-3.12.0-amd64.exe') then
    begin
      WizardForm.StatusLabel.Caption := 'Instalando Python 3.12...';
      WizardForm.Update;
      Exec(TmpDir + '\python-3.12.0-amd64.exe',
           '/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1',
           '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
    end;

    // Instalar Node.js desde bundle (si fue empaquetado y seleccionado)
    if WizardIsComponentSelected('deps\node') and
       FileExists(TmpDir + '\node-v20.11.0-x64.msi') then
    begin
      WizardForm.StatusLabel.Caption := 'Instalando Node.js 20...';
      WizardForm.Update;
      Exec(ExpandConstant('{sys}\msiexec.exe'),
           '/i "' + TmpDir + '\node-v20.11.0-x64.msi" /quiet /norestart',
           '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
    end;

    // Instalar Ollama desde bundle (si fue empaquetado y seleccionado)
    if WizardIsComponentSelected('deps\ollama') and
       FileExists(TmpDir + '\OllamaSetup.exe') then
    begin
      WizardForm.StatusLabel.Caption := 'Instalando Ollama...';
      WizardForm.Update;
      Exec(TmpDir + '\OllamaSetup.exe', '/S', '',
           SW_SHOW, ewWaitUntilTerminated, ResultCode);
    end;

    // Ejecutar instalar.bat con pantalla de progreso
    RunInstallWithProgress(ExpandConstant('{app}'));
  end;
end;
