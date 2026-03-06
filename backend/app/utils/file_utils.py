"""
Utilidades para manejo de archivos: validación, rutas, limpieza.
"""

import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings


def validar_pdf(file: UploadFile) -> None:
    """Valida que el archivo sea PDF y no supere el tamaño máximo."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se aceptan archivos PDF. Recibido: {file.filename}",
        )
    # El tamaño se verifica al leer el contenido


def get_cv_path(proceso_id: int, filename: str) -> Path:
    """Devuelve la ruta donde se guardará el PDF de un CV."""
    carpeta = settings.CVS_DIR / str(proceso_id)
    carpeta.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
    return carpeta / safe_name


def get_export_path(proceso_id: int) -> Path:
    """Devuelve la ruta para el Excel exportado."""
    settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return settings.EXPORTS_DIR / f"ranking_proceso_{proceso_id}.xlsx"


async def guardar_archivo(file: UploadFile, destino: Path) -> int:
    """Guarda un archivo subido en disco. Retorna el tamaño en bytes."""
    contenido = await file.read()
    if len(contenido) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {settings.MAX_FILE_SIZE_MB} MB.",
        )
    destino.write_bytes(contenido)
    return len(contenido)
