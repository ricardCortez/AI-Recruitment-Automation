from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Proceso ──────────────────────────────────────────────────────────────────
class ProcesoCreate(BaseModel):
    nombre_puesto: str
    requisitos: str


class ProcesoOut(BaseModel):
    id: int
    nombre_puesto: str
    requisitos: str
    creado_por_id: int
    creado_en: datetime
    total_candidatos: int = 0

    model_config = {"from_attributes": True}


# ── Candidato ─────────────────────────────────────────────────────────────────
class CandidatoOut(BaseModel):
    id: int
    proceso_id: int
    nombre: Optional[str]
    email: Optional[str]
    telefono: Optional[str]
    archivo_pdf: str
    cargado_en: datetime

    model_config = {"from_attributes": True}


# ── Análisis ──────────────────────────────────────────────────────────────────
class CriterioEvaluado(BaseModel):
    criterio: str
    cumple: str          # "si" | "parcial" | "no"
    descripcion: str
    puntaje: float       # 0–100


class AnalisisOut(BaseModel):
    id: int
    candidato_id: int
    estado: str
    puntaje_total: Optional[float]
    detalle_json: Optional[List[CriterioEvaluado]]
    resumen_ia: Optional[str]
    proveedor_ia: Optional[str]
    procesado_en: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Ranking ───────────────────────────────────────────────────────────────────
class RankingItem(BaseModel):
    posicion: int
    candidato: CandidatoOut
    analisis: Optional[AnalisisOut]

    model_config = {"from_attributes": True}


class RankingResponse(BaseModel):
    proceso_id: int
    nombre_puesto: str
    total: int
    items: List[RankingItem]
