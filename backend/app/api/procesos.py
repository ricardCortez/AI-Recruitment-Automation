"""
Endpoints de Procesos de selección.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.proceso import Proceso
from app.models.candidato import Candidato
from app.core.dependencies import get_current_user, require_reclutador_or_admin
from app.schemas.proceso import ProcesoCreate, ProcesoOut, RankingResponse
from app.services.ranking_service import obtener_ranking

router = APIRouter()


def _proceso_to_out(proceso: Proceso, db: Session) -> dict:
    """Convierte un Proceso a dict incluyendo total_candidatos real."""
    total = db.query(Candidato).filter(Candidato.proceso_id == proceso.id).count()
    return {
        "id":             proceso.id,
        "nombre_puesto":  proceso.nombre_puesto,
        "requisitos":     proceso.requisitos,
        "creado_por_id":  proceso.creado_por_id,
        "creado_en":      proceso.creado_en,
        "total_candidatos": total,
    }


@router.get("/", response_model=list[ProcesoOut])
def listar_procesos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    procesos = db.query(Proceso).order_by(Proceso.creado_en.desc()).all()
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
