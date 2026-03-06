from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    debe_cambiar_clave: bool = False
    rol: str
    nombre_completo: str


class CambiarClaveRequest(BaseModel):
    password_actual: str
    password_nueva: str


class RecuperarConAdminRequest(BaseModel):
    username: str
    nueva_password: str       # Solo admin puede llamar este endpoint


class RecuperarConCodigoRequest(BaseModel):
    username: str
    recovery_code: str
    nueva_password: str


class RecuperarConTotpRequest(BaseModel):
    username: str
    totp_code: str
    nueva_password: str


class VerificarTotpRequest(BaseModel):
    totp_code: str


class TotpSetupResponse(BaseModel):
    qr_base64: str
    secret: str
    mensaje: str = "Escaneá el QR con Google Authenticator y confirmá con un código."
