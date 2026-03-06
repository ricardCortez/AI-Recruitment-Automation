"""
Endpoints de exportación (Excel).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User
from app.models.proceso import Proceso
from app.core.dependencies import get_current_user
from app.services.ranking_service import obtener_ranking
from app.services.export_service import generar_excel_ranking
from app.utils.file_utils import get_export_path

router = APIRouter()


@router.get("/{proceso_id}/excel")
def exportar_excel(
    proceso_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado.")

    items    = obtener_ranking(proceso_id, db)
    destino  = get_export_path(proceso_id)
    generar_excel_ranking(proceso.nombre_puesto, items, destino)

    return FileResponse(
        path=str(destino),
        filename=f"Ranking_{proceso.nombre_puesto.replace(' ', '_')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
