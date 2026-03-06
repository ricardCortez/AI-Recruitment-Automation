"""
Modelo de base de datos: Usuarios y roles del sistema.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum

from app.db.database import Base


class Rol(str, enum.Enum):
    ADMIN      = "admin"
    RECLUTADOR = "reclutador"
    SUPERVISOR = "supervisor"


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    username         = Column(String(50), unique=True, nullable=False, index=True)
    nombre_completo  = Column(String(120), nullable=False)
    hashed_password  = Column(String(255), nullable=False)
    rol              = Column(Enum(Rol), nullable=False, default=Rol.RECLUTADOR)
    activo           = Column(Boolean, default=True, nullable=False)

    # Seguridad
    debe_cambiar_clave  = Column(Boolean, default=True)
    totp_secret         = Column(String(64), nullable=True)
    totp_activo         = Column(Boolean, default=False)
    recovery_code_hash  = Column(String(255), nullable=True)

    # Auditoría
    creado_en         = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ultimo_acceso     = Column(DateTime, nullable=True)
    creado_por_id     = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<User {self.username} ({self.rol.value})>"
