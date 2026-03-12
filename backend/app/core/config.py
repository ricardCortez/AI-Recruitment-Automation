"""
Configuración central del sistema.
Todas las variables se leen del archivo .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Aplicación ────────────────────────────────────────────────────────
    APP_NAME: str = "Sistema CV"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"

    # ── Servidor ──────────────────────────────────────────────────────────
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 5173

    # ── Seguridad ─────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas

    # ── Base de datos ─────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./database/sistema_cv.db"

    # ── IA ────────────────────────────────────────────────────────────────
    IA_PROVIDER: str = "ollama"         # "ollama" | "openai"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Storage ───────────────────────────────────────────────────────────
    STORAGE_CVS_PATH: str = "storage/cvs"
    STORAGE_EXPORTS_PATH: str = "storage/exports"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: str = "pdf"

    # ── Admin por defecto ─────────────────────────────────────────────────
    # Si no se define en .env, seed genera una contraseña aleatoria al primer inicio
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: Optional[str] = None

    @property
    def BASE_DIR(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent

    @property
    def CVS_DIR(self) -> Path:
        return self.BASE_DIR / self.STORAGE_CVS_PATH

    @property
    def EXPORTS_DIR(self) -> Path:
        return self.BASE_DIR / self.STORAGE_EXPORTS_PATH

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024



@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
