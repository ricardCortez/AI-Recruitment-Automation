"""
Seguridad: JWT, hashing de contraseñas y Google Authenticator (2FA).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import pyotp
import qrcode
import io
import base64

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Hashing ──────────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ──────────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ── Código de recuperación ────────────────────────────────────────────────────
def generate_recovery_code() -> str:
    """Genera un código único de recuperación tipo XXXX-XXXX-XXXX."""
    part = lambda: secrets.token_hex(2).upper()
    return f"{part()}-{part()}-{part()}"


def hash_recovery_code(code: str) -> str:
    return pwd_context.hash(code)


def verify_recovery_code(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Google Authenticator (TOTP) ───────────────────────────────────────────────
def generate_totp_secret() -> str:
    """Genera una clave secreta para Google Authenticator."""
    return pyotp.random_base32()


def generate_totp_qr_base64(username: str, secret: str) -> str:
    """Genera el QR de Google Authenticator como imagen base64."""
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(
        name=username,
        issuer_name=settings.APP_NAME
    )
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp_code(secret: str, code: str) -> bool:
    """Verifica el código de 6 dígitos del Google Authenticator."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
