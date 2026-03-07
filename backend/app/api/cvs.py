"""
Endpoints de CVs. El estado devuelve progreso granular por sub-pasos.
"""

import re
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db, SessionLocal
from app.models.user import User
from app.models.proceso import Proceso
from app.models.candidato import Candidato
from app.core.dependencies import require_reclutador_or_admin
from app.utils.file_utils import validar_pdf, get_cv_path, guardar_archivo
from app.services.analisis_service import analizar_proceso, solicitar_cancelacion, cancelacion_activa
from app.schemas.proceso import CandidatoOut

router = APIRouter()


# ── Ruta fija ANTES de /{proceso_id}/... ────────────────────────────────────
@router.get("/ollama/estado")
async def estado_ollama(_: User = Depends(require_reclutador_or_admin)):
    from app.services.ia_service import verificar_ollama
    return await verificar_ollama()


# ── Background task con sesión propia ────────────────────────────────────────
def analizar_en_background(proceso_id: int):
    """Background task — síncrono, sin asyncio.run()."""
    db = SessionLocal()
    try:
        analizar_proceso(proceso_id, db)
    except Exception as e:
        import traceback
        from app.utils.logger import get_logger
        get_logger(__name__).error(f"Error crítico en background task: {e}
{traceback.format_exc()}")
    finally:
        db.close()


# ── Upload CVs ────────────────────────────────────────────────────────────────
@router.post("/{proceso_id}/upload", response_model=list[CandidatoOut])
async def subir_cvs(
    proceso_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    if not files:
        raise HTTPException(status_code=400, detail="No se recibieron archivos.")

    creados = []
    for file in files:
        validar_pdf(file)
        destino = get_cv_path(proceso_id, file.filename)
        await guardar_archivo(file, destino)
        candidato = Candidato(proceso_id=proceso_id, archivo_pdf=str(destino))
        db.add(candidato)
        db.commit()
        db.refresh(candidato)
        creados.append(candidato)

    return creados


# ── Disparar análisis ─────────────────────────────────────────────────────────
@router.post("/{proceso_id}/analizar")
async def analizar(
    proceso_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")

    total = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).count()
    if total == 0:
        raise HTTPException(status_code=400, detail="No hay CVs cargados.")

    background_tasks.add_task(analizar_en_background, proceso_id)
    return {"mensaje": f"Análisis iniciado para {total} CV{'s' if total != 1 else ''}.", "total": total}


# ── Cancelar análisis ────────────────────────────────────────────────────────
@router.post("/{proceso_id}/cancelar")
def cancelar_analisis(
    proceso_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    from app.models.analisis import Analisis, EstadoAnalisis

    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")

    solicitar_cancelacion(proceso_id)
    return {"mensaje": "Cancelación solicitada. Se detendrá al terminar el CV actual."}


# ── Estado con progreso granular ──────────────────────────────────────────────
@router.get("/{proceso_id}/estado")
def estado_analisis(
    proceso_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    from app.models.analisis import Analisis, EstadoAnalisis

    db.expire_all()

    candidatos = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).all()
    total = len(candidatos)
    estados = {
        "total": total,
        "pendiente": 0, "procesando": 0, "completado": 0, "error": 0,
        "log_actual": "",
        "sub_pct": 0,          # Progreso dentro del CV actual (0-100)
        "progreso_global": 0,  # Progreso total incluyendo sub-pasos (0-100)
    }

    completados = 0
    sub_pct     = 0
    log_actual  = ""

    for c in candidatos:
        an = db.query(Analisis).filter(Analisis.candidato_id == c.id).first()
        if not an:
            estados["pendiente"] += 1
        else:
            estados[an.estado.value] += 1
            if an.estado == EstadoAnalisis.COMPLETADO:
                completados += 1
            elif an.estado == EstadoAnalisis.ERROR:
                completados += 1  # Contar errores como "procesados" para la barra
            elif an.estado == EstadoAnalisis.PROCESANDO and an.error_msg:
                # Parsear [PROG:45] Mensaje
                match = re.match(r'\[PROG:(\d+)\]\s*(.*)', an.error_msg)
                if match:
                    sub_pct    = int(match.group(1))
                    log_actual = match.group(2)

    estados["log_actual"] = log_actual
    estados["sub_pct"]    = sub_pct

    # Progreso global: CVs completados + fracción del CV actual
    if total > 0:
        estados["progreso_global"] = int((completados * 100 + sub_pct) / total)

    estados["listo"] = total > 0 and (estados["completado"] + estados["error"]) == total

    # Detectar si fue cancelado (algún error_msg dice "cancelado")
    from app.services.analisis_service import cancelacion_activa
    estados["cancelado"] = cancelacion_activa(proceso_id)

    return estados


# ── Eliminar candidato ────────────────────────────────────────────────────────
@router.delete("/{proceso_id}/candidatos/{candidato_id}")
def eliminar_candidato(
    proceso_id: int,
    candidato_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    import os
    c = db.query(Candidato).filter(
        Candidato.id == candidato_id, Candidato.proceso_id == proceso_id
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidato no encontrado.")
    try:
        if os.path.exists(c.archivo_pdf):
            os.remove(c.archivo_pdf)
    except Exception:
        pass
    db.delete(c)
    db.commit()
    return {"mensaje": "Candidato eliminado."}
