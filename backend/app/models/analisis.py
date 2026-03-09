"""
Modelo: Resultado del análisis IA de un candidato.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


class EstadoAnalisis(str, enum.Enum):
    PENDIENTE   = "pendiente"
    PROCESANDO  = "procesando"
    COMPLETADO  = "completado"
    ERROR       = "error"


class Analisis(Base):
    __tablename__ = "analisis"

    id              = Column(Integer, primary_key=True, index=True)
    candidato_id    = Column(Integer, ForeignKey("candidatos.id"), nullable=False)
    estado          = Column(Enum(EstadoAnalisis), default=EstadoAnalisis.PENDIENTE)
    puntaje_total   = Column(Float, nullable=True)           # 0.0 – 100.0
    detalle_json    = Column(JSON, nullable=True)            # Lista de criterios evaluados
    resumen_ia      = Column(Text, nullable=True)            # Texto generado por la IA
    proveedor_ia    = Column(String(50), nullable=True)      # "ollama" | "openai"
    error_msg       = Column(Text, nullable=True)            # Error real al fallar
    progress_msg    = Column(Text, nullable=True)            # Progreso durante procesamiento "[PROG:50] ..."
    procesado_en    = Column(DateTime, nullable=True)
    creado_en       = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relación
    candidato = relationship("Candidato", back_populates="analisis")

    def __repr__(self):
        return f"<Analisis candidato={self.candidato_id} puntaje={self.puntaje_total}>"
