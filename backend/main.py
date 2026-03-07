"""
Sistema CV — Punto de entrada principal del backend.
"""

from fastapi import FastAPI
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
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Apagando servidor.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST para el Sistema Automatizado de Análisis de CVs",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
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
