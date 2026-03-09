"""
Construye el ranking de candidatos de un proceso ordenado por puntaje.
"""

from sqlalchemy.orm import Session

from app.models.candidato import Candidato
from app.models.analisis import Analisis, EstadoAnalisis


def obtener_ranking(proceso_id: int, db: Session) -> list[dict]:
    """
    Retorna lista de candidatos ordenados por puntaje descendente.
    Candidatos sin análisis van al final.
    Usa una sola query con IN para evitar N+1.
    """
    candidatos = (
        db.query(Candidato)
        .filter(Candidato.proceso_id == proceso_id)
        .all()
    )

    # Una sola query para todos los análisis (evita N+1)
    candidato_ids = [c.id for c in candidatos]
    analisis_list = db.query(Analisis).filter(Analisis.candidato_id.in_(candidato_ids)).all()
    analisis_map  = {a.candidato_id: a for a in analisis_list}

    items = []
    for c in candidatos:
        analisis = analisis_map.get(c.id)
        items.append({
            "candidato": c,
            "analisis":  analisis,
            "puntaje":   analisis.puntaje_total if analisis and analisis.estado == EstadoAnalisis.COMPLETADO else -1,
        })

    items.sort(key=lambda x: x["puntaje"], reverse=True)

    return [
        {"posicion": i + 1, "candidato": item["candidato"], "analisis": item["analisis"]}
        for i, item in enumerate(items)
    ]
