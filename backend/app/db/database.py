"""
Conexión a la base de datos SQLite y gestión de sesiones.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # necesario para SQLite
    echo=settings.ENVIRONMENT == "development",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def create_tables():
    """Crea todas las tablas si no existen."""
    from app.models import user, proceso, candidato, analisis  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependencia FastAPI: entrega una sesión de DB y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
