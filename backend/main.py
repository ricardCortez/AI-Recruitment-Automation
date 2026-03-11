"""
Sistema CV — Punto de entrada principal del backend.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import create_tables
from app.db.seed import run_seed
from app.api import auth, users, procesos, cvs, reportes, config
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ejecuta tareas al iniciar y al apagar el servidor."""
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    create_tables()
    run_seed()
    logger.info("Base de datos lista.")
    # Aplicar configuración de IA guardada (config.json) sobre los defaults de .env
    try:
        from app.api.config import leer_config
        saved_cfg = leer_config()
        settings.OLLAMA_MODEL = saved_cfg.get("modelo", settings.OLLAMA_MODEL)
        logger.info("Modelo IA cargado desde config.json: %s", settings.OLLAMA_MODEL)
    except Exception as e:
        logger.warning("No se pudo leer config.json al inicio: %s", e)
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Apagando servidor.")


class _UTCResponse(JSONResponse):
    """Serializa datetimes con sufijo Z para que el navegador los convierta a hora local."""
    def render(self, content) -> bytes:
        import json
        from datetime import datetime
        def _enc(obj):
            if isinstance(obj, datetime):
                s = obj.isoformat()
                return s if (s.endswith("Z") or "+" in s) else s + "Z"
            raise TypeError(repr(obj))
        return json.dumps(content, default=_enc, ensure_ascii=False).encode("utf-8")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST para el Sistema Automatizado de Análisis de CVs",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
    default_response_class=_UTCResponse,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.FRONTEND_PORT}",
        f"http://127.0.0.1:{settings.FRONTEND_PORT}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rutas ────────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router,      prefix=f"{API_PREFIX}/auth",     tags=["Autenticación"])
app.include_router(users.router,     prefix=f"{API_PREFIX}/users",    tags=["Usuarios"])
app.include_router(procesos.router,  prefix=f"{API_PREFIX}/procesos", tags=["Procesos"])
app.include_router(cvs.router,       prefix=f"{API_PREFIX}/cvs",      tags=["CVs"])
app.include_router(reportes.router,  prefix=f"{API_PREFIX}/reportes", tags=["Reportes"])
app.include_router(config.router,    prefix=f"{API_PREFIX}/config",   tags=["Configuración"])


@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verificar que el servidor está corriendo."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# ── Servir frontend estático ────────────────────────────────────────────────
from pathlib import Path as _Path
from fastapi.responses import FileResponse as _FileResponse

_FRONTEND_DIST = _Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    _assets = _FRONTEND_DIST / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Serve React SPA for all non-API routes."""
        index = _FRONTEND_DIST / "index.html"
        if index.exists():
            return _FileResponse(str(index))
        return {"error": "Frontend no buildeado. Ejecuta: cd frontend && npm run build"}
