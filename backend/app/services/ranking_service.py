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
    """
    candidatos = (
        db.query(Candidato)
        .filter(Candidato.proceso_id == proceso_id)
        .all()
    )

    items = []
    for c in candidatos:
        analisis = db.query(Analisis).filter(Analisis.candidato_id == c.id).first()
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
