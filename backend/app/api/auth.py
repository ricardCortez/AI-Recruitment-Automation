"""
Endpoints de autenticación: login, logout, cambio de clave, recuperación, 2FA.
"""

import time
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.core.security import (
    verify_password, hash_password, create_access_token,
    verify_recovery_code, verify_totp_code,
    generate_totp_secret, generate_totp_qr_base64,
)
from app.core.dependencies import get_current_user, require_admin
from app.schemas.auth import (
    LoginRequest, TokenResponse, CambiarClaveRequest,
    RecuperarConCodigoRequest, RecuperarConTotpRequest,
    VerificarTotpRequest, TotpSetupResponse,
)

router = APIRouter()

# ── Rate limiting simple en memoria ──────────────────────────────────────────
_login_intentos: dict[str, list[float]] = defaultdict(list)
_MAX_INTENTOS   = 10    # máximo de intentos por ventana
_VENTANA_SEG    = 60    # ventana de 60 segundos


def _verificar_rate_limit(identifier: str):
    """Bloquea si se superan MAX_INTENTOS en VENTANA_SEG segundos."""
    ahora   = time.time()
    recents = [t for t in _login_intentos[identifier] if ahora - t < _VENTANA_SEG]
    _login_intentos[identifier] = recents
    if len(recents) >= _MAX_INTENTOS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de login. Esperá 1 minuto.",
        )
    _login_intentos[identifier].append(ahora)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Aplicar rate limit por IP
    client_ip = request.client.host if request.client else "unknown"
    _verificar_rate_limit(client_ip)
    user = db.query(User).filter(User.username == data.username.lower()).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos.")

    if not user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo. Contactá al administrador.")

    # Actualizar último acceso
    user.ultimo_acceso = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": str(user.id), "rol": user.rol.value})
    return TokenResponse(
        access_token=token,
        debe_cambiar_clave=user.debe_cambiar_clave,
        rol=user.rol.value,
        nombre_completo=user.nombre_completo,
    )


@router.post("/cambiar-clave")
def cambiar_clave(
    data: CambiarClaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.password_actual, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta.")
    if len(data.password_nueva) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La nueva contraseña debe tener al menos 8 caracteres.")

    current_user.hashed_password   = hash_password(data.password_nueva)
    current_user.debe_cambiar_clave = False
    db.commit()
    return {"mensaje": "Contraseña actualizada correctamente."}


@router.post("/recuperar/codigo")
def recuperar_con_codigo(data: RecuperarConCodigoRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username.lower(), User.activo == True).first()
    if not user or not user.recovery_code_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Datos inválidos.")
    if not verify_recovery_code(data.recovery_code.upper().replace(" ", ""), user.recovery_code_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código de recuperación incorrecto.")

    user.hashed_password    = hash_password(data.nueva_password)
    user.debe_cambiar_clave = True
    db.commit()
    return {"mensaje": "Contraseña restablecida. Deberás cambiarla al ingresar."}


@router.post("/recuperar/totp")
def recuperar_con_totp(data: RecuperarConTotpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username.lower(), User.activo == True).first()
    if not user or not user.totp_activo or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA no configurado para este usuario.")
    if not verify_totp_code(user.totp_secret, data.totp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código 2FA incorrecto.")

    user.hashed_password    = hash_password(data.nueva_password)
    user.debe_cambiar_clave = True
    db.commit()
    return {"mensaje": "Contraseña restablecida. Deberás cambiarla al ingresar."}


@router.get("/totp/setup", response_model=TotpSetupResponse)
def totp_setup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Genera QR para vincular Google Authenticator. No activa el 2FA hasta confirmar."""
    if not current_user.totp_secret:
        current_user.totp_secret = generate_totp_secret()
        db.commit()
    qr = generate_totp_qr_base64(current_user.username, current_user.totp_secret)
    return TotpSetupResponse(qr_base64=qr, secret=current_user.totp_secret)


@router.post("/totp/confirmar")
def totp_confirmar(
    data: VerificarTotpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Activa el 2FA después de que el usuario confirma con un código válido."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Primero generá el QR desde /totp/setup.")
    if not verify_totp_code(current_user.totp_secret, data.totp_code):
        raise HTTPException(status_code=400, detail="Código incorrecto. Verificá la hora de tu dispositivo.")

    current_user.totp_activo = True
    db.commit()
    return {"mensaje": "Google Authenticator activado correctamente."}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "nombre_completo": current_user.nombre_completo,
        "rol": current_user.rol.value,
        "totp_activo": current_user.totp_activo,
    }
