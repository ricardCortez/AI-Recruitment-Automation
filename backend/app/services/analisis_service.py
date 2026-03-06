"""
Orquestación del análisis completo de un proceso: extrae texto → llama IA → guarda resultados.
"""

from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.candidato import Candidato
from app.models.analisis import Analisis, EstadoAnalisis
from app.services.pdf_service import extraer_datos_basicos
from app.services.ia_service import analizar_cv
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def analizar_proceso(proceso_id: int, db: Session) -> dict:
    """
    Analiza todos los candidatos pendientes de un proceso.
    Retorna un resumen con el conteo de resultados.
    """
    candidatos = (
        db.query(Candidato)
        .filter(Candidato.proceso_id == proceso_id)
        .all()
    )

    resultados = {"completados": 0, "errores": 0, "total": len(candidatos)}

    for candidato in candidatos:
        analisis = db.query(Analisis).filter(Analisis.candidato_id == candidato.id).first()

        # Saltar si ya fue analizado
        if analisis and analisis.estado == EstadoAnalisis.COMPLETADO:
            resultados["completados"] += 1
            continue

        # Crear o reutilizar registro de análisis
        if not analisis:
            analisis = Analisis(candidato_id=candidato.id)
            db.add(analisis)

        analisis.estado = EstadoAnalisis.PROCESANDO
        db.commit()

        try:
            # 1. Extraer texto del PDF si no fue extraído antes
            if not candidato.texto_cv:
                pdf_path = Path(candidato.archivo_pdf)
                datos = extraer_datos_basicos(pdf_path)
                candidato.texto_cv = datos["texto"]
                if not candidato.nombre and datos["nombre"]:
                    candidato.nombre = datos["nombre"]
                if not candidato.email and datos["email"]:
                    candidato.email = datos["email"]
                if not candidato.telefono and datos["telefono"]:
                    candidato.telefono = datos["telefono"]
                db.commit()

            # 2. Llamar a la IA
            resultado = await analizar_cv(
                nombre_puesto=candidato.proceso.nombre_puesto,
                requisitos=candidato.proceso.requisitos,
                texto_cv=candidato.texto_cv or "",
            )

            # 3. Guardar resultados
            analisis.estado        = EstadoAnalisis.COMPLETADO
            analisis.puntaje_total = float(resultado["puntaje_total"])
            analisis.detalle_json  = resultado["criterios"]
            analisis.resumen_ia    = resultado["resumen"]
            analisis.proveedor_ia  = settings.IA_PROVIDER
            analisis.procesado_en  = datetime.now(timezone.utc)
            db.commit()

            resultados["completados"] += 1
            logger.info(f"Candidato {candidato.id} analizado. Puntaje: {analisis.puntaje_total:.1f}%")

        except Exception as e:
            analisis.estado    = EstadoAnalisis.ERROR
            analisis.error_msg = str(e)
            db.commit()
            resultados["errores"] += 1
            logger.error(f"Error analizando candidato {candidato.id}: {e}")

    return resultados
