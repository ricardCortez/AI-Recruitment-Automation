# -*- coding: utf-8 -*-
"""
Construye el ranking de candidatos de un proceso ordenado por puntaje.
Devuelve dicts puros (no modelos SQLAlchemy) para evitar errores de
serializacion Pydantic con resultado_json y campos opcionales.
"""

import json
from sqlalchemy.orm import Session

from app.models.candidato import Candidato
from app.models.analisis import Analisis, EstadoAnalisis


def _safe_json(valor):
    """
    Devuelve el valor ya deserializado por SQLAlchemy (lista o dict),
    o intenta parsear si llega como string. Nunca lanza excepcion.
    detalle_json es Column(JSON) -> SQLAlchemy lo devuelve como list directamente.
    """
    if valor is None:
        return None
    # SQLAlchemy ya deserializa Column(JSON) -> list o dict, pasar directo
    if isinstance(valor, (list, dict)):
        return valor
    # Fallback: si por alguna razon llega como string
    try:
        return json.loads(valor)
    except Exception:
        return None


def _candidato_dict(c: Candidato) -> dict:
    return {
        "id":        c.id,
        "nombre":    c.nombre,
        "email":     c.email,
        "telefono":  c.telefono,
        "proceso_id": c.proceso_id,
    }


def _analisis_dict(a: Analisis | None) -> dict | None:
    if a is None:
        return None
    resultado = _safe_json(a.detalle_json)
    return {
        "id":             a.id,
        "candidato_id":   a.candidato_id,
        "estado":         a.estado.value if a.estado else None,
        "puntaje_total":  a.puntaje_total,
        "detalle_json": resultado,
        "resumen_ia":     a.resumen_ia,
        "proveedor_ia":   a.proveedor_ia,
        "error_msg":      a.error_msg,
        "procesado_en":   a.procesado_en.isoformat() if a.procesado_en else None,
    }


def obtener_ranking(proceso_id: int, db: Session) -> list[dict]:
    """
    Retorna lista de dicts con candidato y analisis, ordenados por puntaje.
    Candidatos sin analisis o con error van al final.
    """
    candidatos = (
        db.query(Candidato)
        .filter(Candidato.proceso_id == proceso_id)
        .all()
    )

    candidato_ids = [c.id for c in candidatos]
    analisis_list = (
        db.query(Analisis)
        .filter(Analisis.candidato_id.in_(candidato_ids))
        .all()
    )
    analisis_map = {a.candidato_id: a for a in analisis_list}

    items = []
    for c in candidatos:
        analisis = analisis_map.get(c.id)
        puntaje  = (
            analisis.puntaje_total
            if analisis and analisis.estado == EstadoAnalisis.COMPLETADO
               and analisis.puntaje_total is not None
            else -1
        )
        items.append({
            "candidato": _candidato_dict(c),
            "analisis":  _analisis_dict(analisis),
            "puntaje":   puntaje,
        })

    items.sort(key=lambda x: x["puntaje"], reverse=True)

    return [
        {
            "posicion":  i + 1,
            "candidato": item["candidato"],
            "analisis":  item["analisis"],
        }
        for i, item in enumerate(items)
    ]
