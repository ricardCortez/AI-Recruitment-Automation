"""
Conexión a la base de datos SQLite y gestión de sesiones.
"""

from sqlalchemy import create_engine, text
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


def _aplicar_migraciones():
    """Aplica columnas nuevas a tablas existentes (SQLite no soporta ALTER TABLE automático)."""
    migraciones = [
        # Crítico 3: Separar progress_msg de error_msg en analisis
        "ALTER TABLE analisis ADD COLUMN progress_msg TEXT",
        # Crítico 5: Persistir tiempo de análisis en proceso (sobrevive reinicios del servidor)
        "ALTER TABLE procesos ADD COLUMN tiempo_analisis_s INTEGER",
        "ALTER TABLE procesos ADD COLUMN inicio_analisis DATETIME",
        # Bajo 24: Índice en creado_en para ORDER BY DESC eficiente
        "CREATE INDEX IF NOT EXISTS ix_procesos_creado_en ON procesos (creado_en)",
        # v5: alertas y preguntas generadas por la IA
        "ALTER TABLE analisis ADD COLUMN alertas_json JSON",
        "ALTER TABLE analisis ADD COLUMN preguntas_json JSON",
    ]
    with engine.connect() as conn:
        for sql in migraciones:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Columna ya existe — ignorar


def create_tables():
    """Crea todas las tablas si no existen y aplica migraciones incrementales."""
    from app.models import user, proceso, candidato, analisis  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _aplicar_migraciones()


def get_db():
    """Dependencia FastAPI: entrega una sesión de DB y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
