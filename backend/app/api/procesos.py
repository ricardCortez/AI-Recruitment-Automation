"""
Endpoints de Procesos de selección.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.proceso import Proceso
from app.core.dependencies import get_current_user, require_reclutador_or_admin
from app.schemas.proceso import ProcesoCreate, ProcesoOut
from app.services.ranking_service import obtener_ranking
from app.schemas.proceso import RankingResponse

router = APIRouter()


@router.get("/", response_model=list[ProcesoOut])
def listar_procesos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Proceso)
    # Supervisores y reclutadores ven todos los procesos (solo lectura para supervisor)
    return query.order_by(Proceso.creado_en.desc()).all()


@router.post("/", response_model=ProcesoOut, status_code=status.HTTP_201_CREATED)
def crear_proceso(
    data: ProcesoCreate,
    current_user: User = Depends(require_reclutador_or_admin),
    db: Session = Depends(get_db),
):
    proceso = Proceso(
        nombre_puesto=data.nombre_puesto,
        requisitos=data.requisitos,
        creado_por_id=current_user.id,
    )
    db.add(proceso)
    db.commit()
    db.refresh(proceso)
    return proceso


@router.get("/{proceso_id}", response_model=ProcesoOut)
def obtener_proceso(
    proceso_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")
    return proceso


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
        proceso_id=proceso_id,
        nombre_puesto=proceso.nombre_puesto,
        total=len(items),
        items=items,
    )
