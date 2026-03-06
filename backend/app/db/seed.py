"""
Seed inicial: crea el usuario administrador por defecto si no existe.
Se ejecuta automáticamente al iniciar el servidor.
"""

from app.db.database import SessionLocal, create_tables
from app.models.user import User, Rol
from app.core.security import hash_password, generate_totp_secret, generate_recovery_code, hash_recovery_code
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_seed():
    create_tables()
    db = SessionLocal()
    try:
        existe = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if existe:
            return  # Ya fue creado anteriormente

        recovery_code = generate_recovery_code()
        totp_secret   = generate_totp_secret()

        admin = User(
            username         = settings.ADMIN_USERNAME,
            nombre_completo  = "Administrador del Sistema",
            hashed_password  = hash_password(settings.ADMIN_PASSWORD),
            rol              = Rol.ADMIN,
            activo           = True,
            debe_cambiar_clave = False,
            totp_secret      = totp_secret,
            totp_activo      = False,
            recovery_code_hash = hash_recovery_code(recovery_code),
        )
        db.add(admin)
        db.commit()

        logger.info("=" * 50)
        logger.info("Usuario administrador creado:")
        logger.info(f"  Usuario:   {settings.ADMIN_USERNAME}")
        logger.info(f"  Contraseña: {settings.ADMIN_PASSWORD}")
        logger.info(f"  Cód. recuperación: {recovery_code}  ← Guardalo en un lugar seguro")
        logger.info("=" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
