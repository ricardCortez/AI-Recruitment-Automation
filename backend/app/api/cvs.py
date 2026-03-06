"""
Endpoints de carga de CVs y disparo del análisis IA.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.user import User
from app.models.proceso import Proceso
from app.models.candidato import Candidato
from app.core.dependencies import require_reclutador_or_admin
from app.utils.file_utils import validar_pdf, get_cv_path, guardar_archivo
from app.services.analisis_service import analizar_proceso
from app.schemas.proceso import CandidatoOut

router = APIRouter()


@router.post("/{proceso_id}/upload", response_model=list[CandidatoOut])
async def subir_cvs(
    proceso_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    """Sube uno o más PDFs de CVs a un proceso existente."""
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")

    candidatos_creados = []
    for file in files:
        validar_pdf(file)
        destino = get_cv_path(proceso_id, file.filename)
        await guardar_archivo(file, destino)

        candidato = Candidato(
            proceso_id=proceso_id,
            archivo_pdf=str(destino),
        )
        db.add(candidato)
        db.commit()
        db.refresh(candidato)
        candidatos_creados.append(candidato)

    return candidatos_creados


@router.post("/{proceso_id}/analizar")
async def analizar(
    proceso_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    """
    Dispara el análisis IA de todos los CVs del proceso.
    Corre en background para no bloquear la respuesta.
    """
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")

    total = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).count()
    if total == 0:
        raise HTTPException(status_code=400, detail="No hay CVs cargados en este proceso.")

    background_tasks.add_task(analizar_proceso, proceso_id, db)

    return {"mensaje": f"Análisis iniciado para {total} CVs.", "proceso_id": proceso_id}


@router.get("/{proceso_id}/estado")
def estado_analisis(
    proceso_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    """Retorna el progreso del análisis para mostrar en la pantalla de carga."""
    from app.models.analisis import Analisis, EstadoAnalisis

    candidatos = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).all()
    estados = {"total": len(candidatos), "pendiente": 0, "procesando": 0, "completado": 0, "error": 0}

    for c in candidatos:
        an = db.query(Analisis).filter(Analisis.candidato_id == c.id).first()
        if not an:
            estados["pendiente"] += 1
        else:
            estados[an.estado.value] += 1

    estados["listo"] = estados["completado"] == estados["total"] and estados["total"] > 0
    return estados
