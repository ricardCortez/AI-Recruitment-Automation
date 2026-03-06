"""
Endpoints de gestión de usuarios (solo Admin).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.core.security import (
    hash_password, generate_recovery_code, hash_recovery_code,
    generate_totp_secret, generate_totp_qr_base64,
)
from app.core.dependencies import require_admin
from app.schemas.user import UserCreate, UserUpdate, UserOut, UserCreateResponse

router = APIRouter()


@router.get("/", response_model=list[UserOut])
def listar_usuarios(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.creado_en.desc()).all()


@router.post("/", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail=f"El usuario '{data.username}' ya existe.")

    recovery_code = generate_recovery_code()
    totp_secret   = generate_totp_secret()

    nuevo = User(
        username            = data.username,
        nombre_completo     = data.nombre_completo,
        hashed_password     = hash_password(data.password),
        rol                 = data.rol,
        activo              = True,
        debe_cambiar_clave  = True,
        totp_secret         = totp_secret,
        totp_activo         = False,
        recovery_code_hash  = hash_recovery_code(recovery_code),
        creado_por_id       = current_user.id,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    qr = generate_totp_qr_base64(nuevo.username, totp_secret)

    return UserCreateResponse(
        user=UserOut.model_validate(nuevo),
        recovery_code=recovery_code,
        totp_qr_base64=qr,
    )


@router.put("/{user_id}", response_model=UserOut)
def actualizar_usuario(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if data.nombre_completo is not None:
        user.nombre_completo = data.nombre_completo
    if data.rol is not None:
        user.rol = data.rol
    if data.activo is not None:
        user.activo = data.activo

    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/resetear-clave")
def resetear_clave(
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """El admin resetea la clave de un usuario. Este deberá cambiarla al ingresar."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    temp_password = "Temp@2025!"
    user.hashed_password    = hash_password(temp_password)
    user.debe_cambiar_clave = True
    db.commit()

    return {"mensaje": f"Contraseña reseteada.", "password_temporal": temp_password}
