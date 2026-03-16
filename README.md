# Sistema CV — Análisis Automatizado de CVs con IA

Sistema web local para el área de RR.HH que automatiza la lectura, extracción y evaluación de CVs usando inteligencia artificial local (Ollama). Procesa múltiples candidatos en paralelo y genera un ranking por compatibilidad con el puesto.

---

## Inicio rápido

1. Copiá `.env.example` → `backend/.env` y editá la `SECRET_KEY`
2. Doble clic en **`instalar.bat`** (solo la primera vez)
3. Doble clic en **`iniciar.bat`**
4. El navegador se abre automáticamente en `http://localhost:5173`

**Credenciales por defecto:** `admin` / `Admin@2025!`

> La contraseña se toma de `ADMIN_PASSWORD` en `backend/.env`. Cambiala luego desde la pantalla de Perfil.

---

## Requisitos

| Componente | Versión mínima |
|------------|---------------|
| Python     | 3.11+         |
| Node.js    | 18+           |
| Ollama     | Cualquier versión reciente |
| Modelo IA  | `qwen2.5:7b` (recomendado) o cualquier modelo Ollama |

> El modelo se puede cambiar desde **Configuración → Modelo IA** dentro de la app. También se puede usar GPU (CUDA) desde esa misma pantalla o lanzando `iniciar_gpu.bat`.

---

## Funcionalidades

- **Gestión de procesos de selección** — creá un proceso por puesto, definís los requisitos y subís los CVs.
- **Análisis paralelo con IA local** — los CVs se procesan en paralelo (2–3 workers según CPU/GPU). No se envía información a servidores externos.
- **Extracción inteligente de nombre** — sistema de 7 capas sin IA: heurísticas estructurales, prefijos profesionales, conectores, stopwords, metadatos PDF y nombre de archivo (con split de CamelCase).
- **Ranking de candidatos** — puntaje 0–100 con desglose por criterios (experiencia, habilidades, educación, idiomas).
- **Alertas y preguntas sugeridas** — la IA genera alertas sobre riesgos del candidato y preguntas de entrevista personalizadas.
- **Edición de nombre inline** — si la extracción automática no es correcta, el nombre se puede corregir manualmente desde el detalle del candidato (se persiste en la base de datos).
- **Historial multi-proceso** — el detalle de un candidato muestra si la misma persona postuló a otros procesos anteriores.
- **Re-análisis individual** — se puede volver a analizar un candidato sin reprocesar todo el lote.
- **Exportación Excel** — ranking completo exportable con todos los puntajes y datos de contacto.
- **Gestión de usuarios** — roles Admin y Reclutador, reset de contraseña, 2FA opcional (TOTP).
- **Monitor de hardware** — uso de CPU, RAM y GPU visible en tiempo real desde la interfaz.
- **Cancelación de análisis** — se puede abortar un análisis en curso sin perder los candidatos ya procesados.

---

## Lanzadores

| Archivo | Función |
|---------|---------|
| `instalar.bat` | Instala dependencias Python y Node (solo la primera vez) |
| `iniciar.bat` | Inicia backend + frontend en CPU |
| `iniciar_gpu.bat` | Inicia backend + frontend en GPU (requiere CUDA) |
| `detener.bat` | Detiene todos los servicios |
| `verificar.bat` | Verifica que el entorno esté correctamente configurado |

---

## Estructura del proyecto

```
AI-Recruitment-Automation/
│
├── iniciar.bat                        ← Lanzador principal (detecta venv automáticamente)
├── iniciar_gpu.bat                    ← Lanzador con GPU (CUDA)
├── instalar.bat                       ← Instalador de dependencias (primera vez)
├── detener.bat                        ← Detiene todos los servicios
├── verificar.bat                      ← Verifica el entorno
├── run_system.py                      ← Lanzador Python alternativo
├── .env.example                       ← Plantilla de variables de entorno
│
├── backend/
│   ├── main.py                        ← Punto de entrada FastAPI + lifespan
│   ├── config.json                    ← Configuración IA persistida (modelo, GPU, threads)
│   ├── requirements.txt
│   ├── .env                           ← Variables de entorno (SECRET_KEY, DB, etc.)
│   ├── limpiar_db.py                  ← Utilidad: resetea la base de datos
│   │
│   └── app/
│       ├── api/                       ← Endpoints REST
│       │   ├── auth.py                ← Login, token JWT, recuperar clave
│       │   ├── config.py              ← GET/POST /config  (leer/guardar config IA)
│       │   ├── cvs.py                 ← Upload, análisis, estado, re-analizar,
│       │   │                             cancelar, editar nombre (PATCH)
│       │   ├── procesos.py            ← CRUD de procesos de selección, ranking
│       │   ├── reportes.py            ← Exportar Excel
│       │   └── users.py               ← CRUD usuarios, reset clave
│       │
│       ├── core/
│       │   ├── config.py              ← Settings Pydantic (lee .env)
│       │   ├── dependencies.py        ← Dependencias FastAPI (auth guards)
│       │   └── security.py            ← JWT, hashing de contraseñas, TOTP
│       │
│       ├── db/
│       │   ├── database.py            ← Engine SQLAlchemy + migraciones automáticas
│       │   └── seed.py                ← Seed inicial (usuario admin)
│       │
│       ├── models/                    ← ORM SQLAlchemy
│       │   ├── analisis.py            ← Resultado del análisis IA por candidato
│       │   ├── candidato.py           ← Candidato (PDF + datos extraídos)
│       │   ├── proceso.py             ← Proceso de selección (puesto + requisitos)
│       │   └── user.py                ← Usuario del sistema
│       │
│       ├── schemas/                   ← Pydantic request/response
│       │   ├── auth.py
│       │   ├── proceso.py
│       │   └── user.py
│       │
│       ├── services/                  ← Lógica de negocio
│       │   ├── analisis_service.py    ← Orquestador paralelo (ThreadPoolExecutor)
│       │   ├── ia_service.py          ← Motor Ollama + parseo JSON
│       │   ├── pdf_service.py         ← Extracción PDF, texto, email, teléfono,
│       │   │                             secciones relevantes, nombre (3 pasos)
│       │   ├── extractor_nombre.py    ← Extracción de nombre sin IA:
│       │   │                             7 capas (heurística, score, stopwords,
│       │   │                             conectores, metadatos PDF, archivo)
│       │   ├── export_service.py      ← Generación Excel
│       │   └── ranking_service.py     ← Ordenamiento de candidatos por puntaje
│       │
│       └── utils/
│           ├── file_utils.py          ← Validación y guardado de PDFs
│           ├── hardware.py            ← Monitor CPU/RAM/GPU en tiempo real
│           └── logger.py              ← Logging rotativo a archivo
│
├── backend/database/                  ← SQLite (auto-generado)
├── backend/storage/cvs/               ← PDFs subidos (auto-generado)
├── backend/storage/exports/           ← Excels exportados (auto-generado)
├── backend/logs/                      ← Logs rotativos del backend
├── backend/venv/                      ← Entorno virtual Python
│
└── frontend/
    ├── dist/                          ← Build de producción (servido por FastAPI)
    ├── index.html
    ├── vite.config.js
    ├── package.json
    │
    └── src/
        ├── main.jsx                   ← Entry point React
        ├── App.jsx                    ← Router principal
        │
        ├── pages/
        │   ├── Login.jsx              ← Autenticación
        │   ├── RecuperarClave.jsx     ← Reset de contraseña
        │   ├── Dashboard.jsx          ← Vista principal (procesos recientes)
        │   ├── NuevoAnalisis.jsx      ← Upload CVs + configuración del proceso
        │   ├── Resultados.jsx         ← Ranking de candidatos del proceso
        │   ├── DetalleCandidato.jsx   ← Análisis completo + edición de nombre inline
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
        │   ├── ui/
        │   │   └── index.jsx          ← Card, Badge, Spinner, PageContainer, etc.
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
            ├── api.js                 ← Instancia Axios (base URL + interceptores JWT)
            ├── authService.js         ← Login, logout, cambio de clave
            └── procesoService.js      ← Endpoints: procesos, CVs, nombre, reportes, usuarios
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.11 + FastAPI + SQLAlchemy |
| IA Local | Ollama (`qwen2.5:7b` por defecto) |
| Base de datos | SQLite |
| Auth | JWT + bcrypt + TOTP (2FA) |
| PDF | pdfplumber |
| Export | openpyxl |

---

## Variables de entorno (`backend/.env`)

| Variable | Descripción | Por defecto |
|----------|-------------|-------------|
| `SECRET_KEY` | Clave de firma JWT — **cambiala** | — |
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///./database/sistema_cv.db` |
| `ADMIN_USERNAME` | Usuario administrador inicial | `admin` |
| `ADMIN_PASSWORD` | Contraseña administrador inicial | `Admin@2025!` |
| `OLLAMA_BASE_URL` | URL de Ollama | `http://localhost:11434` |

---

## Flujo de análisis

```
PDF subido
    │
    ├─ pdfplumber → texto crudo
    │
    ├─ extractor_nombre (7 capas, sin IA)
    │     heurística estructural → score → stopwords → conectores
    │     → metadatos PDF → nombre de archivo (CamelCase split)
    │
    ├─ compresión de texto (colapsa líneas en blanco redundantes)
    │
    ├─ extracción de secciones relevantes
    │     (experiencia, habilidades, educación, etc. — reduce tokens ~30%)
    │
    └─ Ollama LLM
          → puntaje 0-100 por criterio
          → nombre/email/teléfono (override si mejora el resultado)
          → resumen ejecutivo
          → alertas de riesgo
          → preguntas de entrevista sugeridas
```

---

## Notas de operación

- **El backend sirve el frontend** como archivos estáticos desde `frontend/dist/`. No se necesita un servidor Node en producción.
- **Los logs** se guardan en `backend/logs/` con rotación diaria.
- **Modelos Ollama** compatibles: `qwen2.5:7b` (recomendado), `llama3.1:8b`, `mistral`, `gemma2`, y cualquier otro modelo con capacidad de respuesta JSON.
- **PDFs escaneados como imagen** no son procesables. El sistema los rechaza con un mensaje claro indicando que deben tener texto seleccionable (usar OCR previamente).
- **Nombre incorrecto**: si la extracción automática falla, el nombre se puede editar directamente desde el detalle del candidato (ícono ✏️ junto al nombre).
