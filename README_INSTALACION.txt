============================================================
  SISTEMA CV -- IA de Reclutamiento Local
  Guia de instalacion y uso
============================================================


REQUISITOS PREVIOS
------------------
- Windows 10 / 11 (64-bit)
- Conexion a Internet (solo durante la instalacion)
- Al menos 8 GB de RAM (16 GB recomendado para modelos grandes)
- Al menos 10 GB de espacio libre en disco


INSTALACION (primera vez)
--------------------------
1. Haz doble clic en  instalar.bat
2. El instalador descargara e instalara automaticamente:
     - Python 3.12
     - Node.js 20 LTS
     - Ollama (motor de IA local)
     - Dependencias de Python (fastapi, uvicorn, sqlalchemy, etc.)
3. Compilara el frontend (React) y lo dejara listo para usar
4. Creara el archivo de configuracion backend\.env
5. Descargara el modelo de IA  qwen2.5:7b  (~4 GB)

   La instalacion puede tardar 10-30 minutos segun tu conexion.
   Al terminar veras el mensaje "Instalacion completada".


INICIAR EL SISTEMA
-------------------
- CPU (cualquier PC):     doble clic en  iniciar.bat
- GPU NVIDIA (mas rapido): doble clic en  iniciar_gpu.bat

El sistema abrira automaticamente el navegador en:
    http://127.0.0.1:8000

Si el navegador no abre, escribe esa direccion manualmente.


CREDENCIALES POR DEFECTO
--------------------------
Usuario:  admin
Password: (se muestra en los logs la primera vez que inicia)

Para ver el password inicial, abre el archivo:
    logs\backend.log
y busca la linea que contiene "Contrasena admin generada".

Puedes cambiar el password desde el panel de administracion
una vez que inicies sesion.


DETENER EL SISTEMA
-------------------
Doble clic en  detener.bat
Se te preguntara si tambien quieres detener Ollama.


VERIFICAR EL SISTEMA
---------------------
Si algo no funciona, doble clic en  verificar.bat
Genera un reporte en  verificacion.log  con el estado de
todos los componentes.


ESTRUCTURA DE ARCHIVOS IMPORTANTES
------------------------------------
  instalar.bat         -- Instalador (ejecutar una vez)
  iniciar.bat          -- Arrancar el sistema (CPU)
  iniciar_gpu.bat      -- Arrancar el sistema (GPU NVIDIA)
  detener.bat          -- Detener el sistema
  verificar.bat        -- Diagnostico
  backend\.env         -- Configuracion (SECRET_KEY, modelo IA, etc.)
  logs\backend.log     -- Log del servidor en tiempo real
  database\sistema_cv.db -- Base de datos SQLite
  storage\cvs\         -- CVs subidos
  storage\exports\     -- Reportes exportados


CAMBIAR EL MODELO DE IA
------------------------
Desde la aplicacion web: Menu -> Configuracion -> Modelo IA
Los modelos disponibles dependen de lo que hayas descargado con Ollama.

Para descargar un modelo manualmente, abre una terminal y escribe:
    ollama pull qwen2.5:7b      (rapido, ~4 GB, recomendado)
    ollama pull qwen2.5:14b     (mejor calidad, ~8 GB)
    ollama pull llama3.2:3b     (muy rapido, menor calidad)

Para ver modelos instalados:
    ollama list


PROBLEMAS FRECUENTES
---------------------

El sistema no abre el navegador:
    -> Espera 30 segundos y ve manualmente a http://127.0.0.1:8000
    -> Revisa logs\backend.log para ver errores

"Frontend no buildeado":
    -> Ejecuta instalar.bat de nuevo
    -> O abre una terminal en la carpeta frontend y ejecuta: npm run build

El analisis de CVs no devuelve resultados de IA:
    -> Verifica que Ollama este corriendo: http://localhost:11434
    -> Ejecuta verificar.bat y revisa la seccion Ollama

Puerto 8000 ocupado:
    -> Ejecuta detener.bat
    -> O abre una terminal y ejecuta: netstat -aon | findstr :8000

Error al instalar dependencias de Python:
    -> Asegurate de tener Python 3.11 o superior
    -> Abre una terminal como Administrador y ejecuta:
         pip install -r backend\requirements.txt

Error "Access is denied" al iniciar:
    -> Haz clic derecho en el .bat -> "Ejecutar como administrador"


SOPORTE
--------
Para reportar problemas, incluye el contenido de:
  - logs\backend.log
  - verificacion.log


============================================================
