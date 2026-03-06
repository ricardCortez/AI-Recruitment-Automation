"""
Modelo: Proceso de selección de personal.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Proceso(Base):
    __tablename__ = "procesos"

    id              = Column(Integer, primary_key=True, index=True)
    nombre_puesto   = Column(String(200), nullable=False)
    requisitos      = Column(Text, nullable=False)   # Texto libre del reclutador
    creado_por_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    creado_en       = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    candidatos = relationship("Candidato", back_populates="proceso", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Proceso '{self.nombre_puesto}'>"
