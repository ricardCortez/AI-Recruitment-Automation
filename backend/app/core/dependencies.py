"""
Dependencias reutilizables para inyección en los endpoints de FastAPI.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, Rol

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extrae y valida el usuario desde el token JWT."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    user = db.query(User).filter(User.id == user_id, User.activo == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo.")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Solo permite acceso a Administradores."""
    if current_user.rol != Rol.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol Administrador.")
    return current_user


def require_reclutador_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Permite acceso a Reclutadores y Administradores."""
    if current_user.rol not in (Rol.ADMIN, Rol.RECLUTADOR):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado.")
    return current_user
