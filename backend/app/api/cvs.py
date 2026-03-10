# -*- coding: utf-8 -*-
"""
Endpoints de CVs. v5 — agrega endpoint de historial de candidato.
"""

import os
import re
import threading
import traceback
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db, SessionLocal
from app.models.user import User
from app.models.proceso import Proceso
from app.models.candidato import Candidato
from app.models.analisis import Analisis, EstadoAnalisis
from app.core.dependencies import require_reclutador_or_admin
from app.utils.file_utils import validar_pdf, get_cv_path, guardar_archivo
from app.services.analisis_service import analizar_proceso, solicitar_cancelacion, cancelacion_activa
from app.schemas.proceso import CandidatoOut

router = APIRouter()


# -- Ruta fija ANTES de /{proceso_id}/... ------------------------------------
@router.get("/ollama/estado")
async def estado_ollama(_: User = Depends(require_reclutador_or_admin)):
    from app.services.ia_service import verificar_ollama
    return await verificar_ollama()


# -- Background task ---------------------------------------------------------
def _worker(proceso_id: int):
    db = SessionLocal()
    try:
        analizar_proceso(proceso_id, db)
    except Exception as e:
        tb = traceback.format_exc()
        from app.utils.logger import get_logger
        get_logger(__name__).error("Error en worker proceso %s: %s | %s", proceso_id, e, tb)
    finally:
        db.close()


def analizar_en_background(proceso_id: int):
    t = threading.Thread(target=_worker, args=(proceso_id,), daemon=True)
    t.start()


# -- Upload CVs --------------------------------------------------------------
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


# -- Disparar analisis -------------------------------------------------------
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

    proceso.inicio_analisis   = datetime.now(timezone.utc)
    proceso.tiempo_analisis_s = None
    db.commit()

    background_tasks.add_task(analizar_en_background, proceso_id)
    label = "CVs" if total != 1 else "CV"
    return {"mensaje": "Analisis iniciado para {} {}.".format(total, label), "total": total}


# -- Cancelar analisis -------------------------------------------------------
@router.post("/{proceso_id}/cancelar")
def cancelar_analisis(
    proceso_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    solicitar_cancelacion(proceso_id)
    return {"mensaje": "Cancelacion solicitada. Se detendra al terminar el CV actual."}


# -- Estado con progreso granular --------------------------------------------
@router.get("/{proceso_id}/estado")
def estado_analisis(
    proceso_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    db.expire_all()

    candidatos = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).all()
    total = len(candidatos)
    estados = {
        "total": total,
        "pendiente": 0, "procesando": 0, "completado": 0, "error": 0,
        "log_actual": "",
        "sub_pct": 0,
        "progreso_global": 0,
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
                completados += 1
            elif an.estado == EstadoAnalisis.PROCESANDO and an.progress_msg:
                if an.progress_msg.startswith("[PROG:"):
                    match = re.match(r'\[PROG:(\d+)\]\s*(.*)', an.progress_msg)
                    if match:
                        sub_pct    = int(match.group(1))
                        log_actual = match.group(2)

    estados["log_actual"] = log_actual
    estados["sub_pct"]    = sub_pct

    if total > 0:
        estados["progreso_global"] = int((completados * 100 + sub_pct) / total)

    listo = total > 0 and (estados["completado"] + estados["error"]) == total
    estados["listo"]    = listo
    estados["cancelado"] = cancelacion_activa(proceso_id)

    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if proceso and proceso.inicio_analisis:
        inicio  = proceso.inicio_analisis.replace(tzinfo=timezone.utc) if proceso.inicio_analisis.tzinfo is None else proceso.inicio_analisis
        elapsed = int((datetime.now(timezone.utc) - inicio).total_seconds())
        estados["tiempo_transcurrido_s"] = elapsed
        if listo and not proceso.tiempo_analisis_s:
            proceso.tiempo_analisis_s = elapsed
            db.commit()
    else:
        tiempo_guardado = proceso.tiempo_analisis_s if proceso else None
        estados["tiempo_transcurrido_s"] = tiempo_guardado or 0

    return estados


# -- Re-analizar un candidato individual -------------------------------------
@router.post("/{candidato_id}/reanalizar")
def reanalizar_candidato(
    candidato_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not candidato:
        raise HTTPException(status_code=404, detail="Candidato no encontrado.")

    analisis = db.query(Analisis).filter(Analisis.candidato_id == candidato_id).first()
    if analisis:
        analisis.estado        = EstadoAnalisis.PENDIENTE
        analisis.puntaje_total = None
        analisis.error_msg     = None
        analisis.progress_msg  = None
        db.commit()

    proceso_id = candidato.proceso_id
    t = threading.Thread(
        target=lambda: _reanalizar_worker(proceso_id, candidato_id),
        daemon=True
    )
    t.start()
    return {"mensaje": "Re-analisis iniciado."}


def _reanalizar_worker(proceso_id: int, candidato_id: int):
    db = SessionLocal()
    try:
        from app.services.analisis_service import analizar_proceso
        # Forzar re-analisis marcando el analisis como pendiente
        candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
        if candidato:
            candidato.texto_cv = None  # Forzar re-lectura del PDF
            db.commit()
        # Crear proceso temporal con solo este candidato
        # En la práctica analizar_proceso saltea los completados,
        # por eso lo marcamos pendiente arriba
        analizar_proceso(proceso_id, db)
    except Exception as e:
        from app.utils.logger import get_logger
        get_logger(__name__).error("Error re-analizando candidato %s: %s", candidato_id, e)
    finally:
        db.close()


# -- Historial de candidato entre procesos -----------------------------------
@router.get("/{candidato_id}/historial")
def historial_candidato(
    candidato_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    """
    Devuelve todos los procesos en los que aparece la misma persona
    (identificada por email o nombre), incluyendo el proceso actual.
    """
    candidato_base = db.query(Candidato).filter(Candidato.id == candidato_id).first()
    if not candidato_base:
        raise HTTPException(status_code=404, detail="Candidato no encontrado.")

    # Buscar candidatos coincidentes por email (primero) o nombre
    coincidentes = []

    if candidato_base.email:
        coincidentes = db.query(Candidato).filter(
            Candidato.email == candidato_base.email,
            Candidato.id != candidato_id,
        ).all()
    elif candidato_base.nombre:
        # Buscar por nombre exacto como fallback
        coincidentes = db.query(Candidato).filter(
            Candidato.nombre == candidato_base.nombre,
            Candidato.id != candidato_id,
        ).all()

    todos = [candidato_base] + coincidentes

    historial = []
    for c in todos:
        proceso = db.query(Proceso).filter(Proceso.id == c.proceso_id).first()
        analisis = db.query(Analisis).filter(
            Analisis.candidato_id == c.id,
            Analisis.estado == EstadoAnalisis.COMPLETADO,
        ).first()

        if not proceso:
            continue

        historial.append({
            "candidato_id":  c.id,
            "proceso_id":    proceso.id,
            "nombre_puesto": proceso.nombre_puesto,
            "creado_en":     proceso.creado_en.isoformat() if proceso.creado_en else None,
            "es_actual":     c.id == candidato_id,
            "puntaje":       analisis.puntaje_total if analisis else None,
            "resumen":       analisis.resumen_ia[:120] if analisis and analisis.resumen_ia else None,
            "estado_analisis": analisis.estado if analisis else "sin_analisis",
        })

    # Ordenar: proceso actual primero, luego por fecha desc
    historial.sort(key=lambda x: (not x["es_actual"], x["creado_en"] or ""), reverse=False)

    return {
        "candidato_id":   candidato_id,
        "nombre":         candidato_base.nombre,
        "email":          candidato_base.email,
        "total_procesos": len(historial),
        "historial":      historial,
    }


# -- Eliminar candidato ------------------------------------------------------
@router.delete("/{proceso_id}/candidatos/{candidato_id}")
def eliminar_candidato(
    proceso_id: int,
    candidato_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
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
