"""
Seed inicial: crea el usuario administrador por defecto si no existe.
Se ejecuta automáticamente al iniciar el servidor.
"""

import secrets
import string

from app.db.database import SessionLocal, create_tables
from app.models.user import User, Rol
from app.core.security import hash_password, generate_totp_secret, generate_recovery_code, hash_recovery_code
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _generar_password() -> str:
    """Genera contraseña segura aleatoria de 16 caracteres."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(16))


def run_seed():
    create_tables()
    db = SessionLocal()
    try:
        existe = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if existe:
            return  # Ya fue creado anteriormente

        # Usar contraseña de .env o generar una aleatoria
        password = settings.ADMIN_PASSWORD or _generar_password()

        recovery_code = generate_recovery_code()
        totp_secret   = generate_totp_secret()

        admin = User(
            username           = settings.ADMIN_USERNAME,
            nombre_completo    = "Administrador del Sistema",
            hashed_password    = hash_password(password),
            rol                = Rol.ADMIN,
            activo             = True,
            debe_cambiar_clave = False,
            totp_secret        = totp_secret,
            totp_activo        = False,
            recovery_code_hash = hash_recovery_code(recovery_code),
        )
        db.add(admin)
        db.commit()

        logger.info("=" * 50)
        logger.info("Usuario administrador creado:")
        logger.info("  Usuario:   %s", settings.ADMIN_USERNAME)
        logger.info("  Contraseña: %s  ← Guardala y cambiala luego", password)
        logger.info("  Cód. recuperación: %s  ← Guardalo en un lugar seguro", recovery_code)
        logger.info("=" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
