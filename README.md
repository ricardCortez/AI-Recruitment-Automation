# Sistema CV — Análisis Automatizado de CVs con IA

Sistema web local para el área de RR.HH que automatiza el análisis de CVs usando inteligencia artificial.

## Inicio rápido

1. Copiá `.env.example` → `backend/.env` y editá la `SECRET_KEY`
2. Doble clic en **`iniciar.bat`**
3. El navegador se abre automáticamente en `http://localhost:5173`

**Usuario por defecto:** `admin` / `Admin@2025!`

## Requisitos

- Python 3.11+
- Node.js 18+
- Ollama instalado con el modelo `llama3.1:8b` (Versión 2)

## Estructura

```
AI-Recruitment-Automation/
│
├── iniciar.bat                        ← Lanzador principal (CPU)
├── iniciar_gpu.bat                    ← Lanzador con GPU (CUDA)
├── detener.bat                        ← Detiene todos los servicios
├── run_system.py                      ← Lanzador Python (CPU/GPU/stop)
├── SistemaCV.spec                     ← Config de PyInstaller
├── .env.example                       ← Plantilla de variables de entorno
│
├── build/                             ← Artefactos de PyInstaller (auto-generado)
├── dist/                              ← Ejecutable compilado   (auto-generado)
│
├── backend/
│   ├── main.py                        ← Punto de entrada FastAPI + lifespan
│   ├── config.json                    ← Configuración IA persistida (modelo, GPU, threads)
│   ├── requirements.txt
│   ├── .env                           ← Variables de entorno (SECRET_KEY, DB, etc.)
│   ├── limpiar_db.py                  ← Utilidad: resetea la base de datos
│   ├── migrate_v5.py                  ← Migración manual de esquema DB
│   │
│   ├── app/
│   │   ├── api/                       ← Endpoints REST
│   │   │   ├── auth.py                ← Login, token JWT, recuperar clave
│   │   │   ├── config.py              ← GET/POST /config  (leer/guardar config IA)
│   │   │   ├── cvs.py                 ← Upload CVs, disparar análisis, estado, re-analizar
│   │   │   ├── procesos.py            ← CRUD de procesos de selección, ranking
│   │   │   ├── reportes.py            ← Exportar Excel
│   │   │   └── users.py               ← CRUD usuarios, reset clave
│   │   │
│   │   ├── core/
│   │   │   ├── config.py              ← Settings Pydantic (lee .env)
│   │   │   ├── dependencies.py        ← Dependencias FastAPI (auth guards)
│   │   │   └── security.py            ← JWT, hashing de contraseñas
│   │   │
│   │   ├── db/
│   │   │   ├── database.py            ← Engine SQLAlchemy + migraciones automáticas
│   │   │   └── seed.py                ← Seed inicial (usuario admin)
│   │   │
│   │   ├── models/                    ← ORM SQLAlchemy
│   │   │   ├── analisis.py            ← Resultado del análisis IA por candidato
│   │   │   ├── candidato.py           ← Candidato (PDF + datos extraídos)
│   │   │   ├── proceso.py             ← Proceso de selección (puesto + requisitos)
│   │   │   ├── user.py                ← Usuario del sistema
│   │   │   └── enums.py               ← EstadoAnalisis, ProcesoEstado, Rol
│   │   │
│   │   ├── schemas/                   ← Pydantic request/response
│   │   │   ├── auth.py
│   │   │   ├── proceso.py
│   │   │   └── user.py
│   │   │
│   │   ├── services/                  ← Lógica de negocio
│   │   │   ├── analisis_service.py    ← Orquestador paralelo (ThreadPoolExecutor)
│   │   │   ├── ia_service.py          ← Motor Ollama/OpenAI + parseo JSON
│   │   │   ├── pdf_service.py         ← Extracción PDF + secciones relevantes
│   │   │   ├── extractor_nombre.py    ← Extracción de nombre (5 capas, sin IA)
│   │   │   ├── export_service.py      ← Generación Excel
│   │   │   └── ranking_service.py     ← Ordenamiento de candidatos por puntaje
│   │   │
│   │   └── utils/
│   │       ├── file_utils.py          ← Validación y guardado de PDFs
│   │       ├── hardware.py            ← Monitor CPU/RAM/GPU en tiempo real
│   │       └── logger.py              ← Logging rotativo a archivo
│   │
│   ├── database/                      ← SQLite (auto-generado)
│   ├── storage/cvs/                   ← PDFs subidos (auto-generado)
│   ├── storage/exports/               ← Excels exportados (auto-generado)
│   ├── logs/                          ← Logs rotativos del backend
│   ├── tests/
│   │   └── test_auth.py
│   └── venv/                          ← Entorno virtual Python
│
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    ├── package.json
    │
    └── src/
        ├── main.jsx                   ← Entry point React
        ├── App.jsx                    ← Router principal
        ├── index.css
        │
        ├── pages/
        │   ├── Login.jsx              ← Autenticación
        │   ├── RecuperarClave.jsx     ← Reset de contraseña
        │   ├── Dashboard.jsx          ← Vista principal (procesos recientes)
        │   ├── NuevoAnalisis.jsx      ← Upload CVs + configuración del proceso
        │   ├── Resultados.jsx         ← Ranking de candidatos del proceso
        │   ├── DetalleCandidato.jsx   ← Análisis completo de un candidato
        │   ├── Usuarios.jsx           ← Gestión de usuarios (admin)
        │   ├── CrearUsuario.jsx       ← Formulario nuevo usuario
        │   ├── Configuracion.jsx      ← Config IA (modelo, GPU/CPU, threads)
        │   └── Perfil.jsx             ← Cambio de contraseña y 2FA
        │
        ├── components/
        │   ├── layout/
        │   │   ├── AppLayout.jsx      ← Shell con sidebar
        │   │   ├── Sidebar.jsx        ← Navegación lateral
        │   │   └── ProtectedRoute.jsx ← Guard de autenticación
        │   │
        │   ├── ui/
        │   │   └── index.jsx          ← Card, Badge, Spinner, PageContainer, etc.
        │   │
        │   └── lg/                    ← Design system visual (glassmorphism)
        │       ├── components.jsx     ← GlassCard, ScoreRing, ActionButton, etc.
        │       ├── theme.js           ← Paleta de colores y tokens
        │       └── ThemeContext.jsx   ← Contexto dark/light mode
        │
        ├── context/
        │   ├── AuthContext.jsx        ← Estado global de sesión JWT
        │   └── AnalisisContext.jsx    ← Estado del análisis en curso (polling)
        │
        └── services/
            ├── api.js                 ← Instancia Axios (base URL + interceptores)
            ├── authService.js         ← Login, logout, cambio de clave
            └── procesoService.js      ← Todos los endpoints (procesos, CVs, config, reportes)

```

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Tailwind CSS |
| Backend | Python 3.11 + FastAPI |
| IA Local | Ollama + Llama 3.1 8B |
| Base de datos | SQLite |
| Auth | JWT + bcrypt + TOTP (2FA) |
