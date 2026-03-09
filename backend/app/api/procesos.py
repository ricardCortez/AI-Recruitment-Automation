# -*- coding: utf-8 -*-
"""
Endpoints de Procesos.
Incluye: estado del analisis, tiempo total, fecha/hora local.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.proceso import Proceso
from app.models.candidato import Candidato
from app.models.analisis import Analisis, EstadoAnalisis
from app.core.dependencies import get_current_user, require_reclutador_or_admin
from app.schemas.proceso import ProcesoCreate, ProcesoOut, RankingResponse
from app.services.ranking_service import obtener_ranking
from app.models.enums import ProcesoEstado

router = APIRouter()


def _calcular_estado(proceso_id: int, db: Session) -> dict:
    """
    Calcula el estado real del proceso y el tiempo de analisis.
    estado: 'sin_analisis' | 'en_proceso' | 'finalizado' | 'parcial'
    tiempo_analisis_s: segundos que tomo el analisis
    Usa una sola query con IN para evitar N+1.
    """
    candidatos = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).all()
    total = len(candidatos)
    if total == 0:
        return {"estado": ProcesoEstado.SIN_ANALISIS, "completados": 0, "total": 0, "tiempo_analisis_s": None}

    # Una sola query para todos los análisis del proceso (evita N+1)
    candidato_ids = [c.id for c in candidatos]
    analisis_list = db.query(Analisis).filter(Analisis.candidato_id.in_(candidato_ids)).all()
    analisis_map  = {a.candidato_id: a for a in analisis_list}

    completados = 0
    en_proceso  = 0
    errores     = 0
    tiempo_min  = None
    tiempo_max  = None

    for c in candidatos:
        an = analisis_map.get(c.id)
        if not an:
            continue
        if an.estado == EstadoAnalisis.COMPLETADO:
            completados += 1
            if an.procesado_en:
                if tiempo_min is None or an.procesado_en < tiempo_min:
                    tiempo_min = an.procesado_en
                if tiempo_max is None or an.procesado_en > tiempo_max:
                    tiempo_max = an.procesado_en
        elif an.estado == EstadoAnalisis.PROCESANDO:
            en_proceso += 1
        elif an.estado == EstadoAnalisis.ERROR:
            errores += 1

    if en_proceso > 0:
        estado = ProcesoEstado.EN_PROCESO
    elif completados + errores == total and total > 0:
        estado = ProcesoEstado.FINALIZADO
    elif completados > 0:
        estado = ProcesoEstado.PARCIAL
    else:
        estado = ProcesoEstado.PENDIENTE

    # Tiempo total: leer de Proceso.tiempo_analisis_s (persistido en BD)
    tiempo_s = None
    try:
        proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
        if proceso:
            tiempo_s = getattr(proceso, "tiempo_analisis_s", None)
    except Exception:
        pass

    # Fallback: estimar con procesado_en si no hay tiempo guardado
    if tiempo_s is None and tiempo_min and tiempo_max and completados > 1:
        diff     = (tiempo_max - tiempo_min).total_seconds()
        avg      = diff / max(completados - 1, 1)
        tiempo_s = int(diff + avg)

    return {
        "estado":            estado,
        "completados":       completados,
        "total":             total,
        "tiempo_analisis_s": tiempo_s,
    }


def _proceso_to_out(proceso: Proceso, db: Session) -> dict:
    total  = db.query(Candidato).filter(Candidato.proceso_id == proceso.id).count()
    estado = _calcular_estado(proceso.id, db)

    # creado_en: convertir a local usando offset del servidor
    # El frontend lo convierte a hora local del usuario con JS
    return {
        "id":                proceso.id,
        "nombre_puesto":     proceso.nombre_puesto,
        "requisitos":        proceso.requisitos,
        "creado_por_id":     proceso.creado_por_id,
        "creado_en":         proceso.creado_en,
        "total_candidatos":  total,
        "estado":            estado["estado"],
        "completados":       estado["completados"],
        "tiempo_analisis_s": estado["tiempo_analisis_s"],
    }


@router.get("/", response_model=list[ProcesoOut])
def listar_procesos(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros a devolver"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    procesos = (
        db.query(Proceso)
        .order_by(Proceso.creado_en.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_proceso_to_out(p, db) for p in procesos]


@router.post("/", response_model=ProcesoOut, status_code=status.HTTP_201_CREATED)
def crear_proceso(
    data: ProcesoCreate,
    current_user: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    proceso = Proceso(
        nombre_puesto = data.nombre_puesto,
        requisitos    = data.requisitos,
        creado_por_id = current_user.id,
    )
    db.add(proceso)
    db.commit()
    db.refresh(proceso)
    return _proceso_to_out(proceso, db)


@router.get("/{proceso_id}", response_model=ProcesoOut)
def obtener_proceso(
    proceso_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    return _proceso_to_out(proceso, db)


@router.delete("/{proceso_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_proceso(
    proceso_id: int,
    _: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    db.delete(proceso)
    db.commit()


@router.get("/{proceso_id}/ranking", response_model=RankingResponse)
def ranking_proceso(
    proceso_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    items = obtener_ranking(proceso_id, db)
    return RankingResponse(
        proceso_id    = proceso_id,
        nombre_puesto = proceso.nombre_puesto,
        total         = len(items),
        items         = items,
    )
