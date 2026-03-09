# -*- coding: utf-8 -*-
import re
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

# Patrones de prompt injection más comunes
_PATRONES_INJECTION = re.compile(
    r'(ignora\s+(las\s+)?instrucciones|ignore\s+(all\s+|previous\s+)?instructions?|'
    r'olvida\s+(todo|las\s+instrucciones)|forget\s+(everything|instructions?)|'
    r'act\s+as|actua\s+como|nuevo\s+rol|new\s+role|'
    r'system\s*:|<\s*system\s*>|###\s*instructions?)',
    re.IGNORECASE,
)


# ── Proceso ──────────────────────────────────────────────────────────────────
class ProcesoCreate(BaseModel):
    nombre_puesto: str
    requisitos: str

    @field_validator("nombre_puesto")
    @classmethod
    def validar_nombre(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre del puesto no puede estar vacío.")
        if len(v) > 200:
            raise ValueError("El nombre del puesto no puede superar 200 caracteres.")
        return v

    @field_validator("requisitos")
    @classmethod
    def validar_requisitos(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Los requisitos no pueden estar vacíos.")
        if len(v) > 5000:
            raise ValueError("Los requisitos no pueden superar 5000 caracteres.")
        if _PATRONES_INJECTION.search(v):
            raise ValueError("Los requisitos contienen instrucciones no permitidas.")
        return v


class ProcesoOut(BaseModel):
    id: int
    nombre_puesto: str
    requisitos: str
    creado_por_id: int
    creado_en: datetime
    total_candidatos: int = 0
    estado: str = "sin_analisis"
    completados: int = 0
    tiempo_analisis_s: Optional[int] = None

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
