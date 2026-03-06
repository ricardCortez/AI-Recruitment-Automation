from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.models.user import Rol


class UserCreate(BaseModel):
    username: str
    nombre_completo: str
    password: str
    rol: Rol = Rol.RECLUTADOR

    @field_validator("username")
    @classmethod
    def username_lowercase(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def password_minlength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        return v


class UserUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    rol: Optional[Rol] = None
    activo: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    username: str
    nombre_completo: str
    rol: Rol
    activo: bool
    totp_activo: bool
    debe_cambiar_clave: bool
    creado_en: datetime
    ultimo_acceso: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserCreateResponse(BaseModel):
    user: UserOut
    recovery_code: str          # Se muestra una sola vez
    totp_qr_base64: str         # QR para Google Authenticator
    mensaje: str = "Guardá el código de recuperación en un lugar seguro. No se vuelve a mostrar."
