"""
Modelo: Candidato (CV cargado dentro de un proceso).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Candidato(Base):
    __tablename__ = "candidatos"

    id          = Column(Integer, primary_key=True, index=True)
    proceso_id  = Column(Integer, ForeignKey("procesos.id"), nullable=False)
    nombre      = Column(String(200), nullable=True)   # Extraído del CV
    email       = Column(String(200), nullable=True)
    telefono    = Column(String(50), nullable=True)
    archivo_pdf = Column(String(300), nullable=False)  # Ruta relativa al archivo
    texto_cv    = Column(String, nullable=True)         # Texto extraído del PDF
    cargado_en  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    proceso  = relationship("Proceso", back_populates="candidatos")
    analisis = relationship("Analisis", back_populates="candidato", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Candidato '{self.nombre}' proceso={self.proceso_id}>"
