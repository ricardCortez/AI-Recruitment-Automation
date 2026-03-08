"""
Servicio de analisis - SINCRONO.
Usa analizar_cv_completo() que hace una sola llamada a Ollama por CV.
"""

import traceback
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.candidato import Candidato
from app.models.proceso import Proceso
from app.models.analisis import Analisis, EstadoAnalisis
from app.services.pdf_service import extraer_texto, extraer_email, extraer_telefono
from app.services.ia_service import analizar_cv_completo
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
MAX_REINTENTOS = 2

# -- Flag de cancelacion ---------------------------------------------------
_cancelar: set[int] = set()

def solicitar_cancelacion(proceso_id: int):
    _cancelar.add(proceso_id)

def cancelacion_activa(proceso_id: int) -> bool:
    return proceso_id in _cancelar

def limpiar_cancelacion(proceso_id: int):
    _cancelar.discard(proceso_id)


def _prog(analisis: Analisis, db: Session, pct: int, mensaje: str):
    try:
        analisis.error_msg = "[PROG:{}] {}".format(pct, mensaje)
        db.commit()
        logger.info("  [%s%%] %s", pct, mensaje)
    except Exception as e:
        logger.warning("No se pudo guardar progreso: %s", e)
        try:
            db.rollback()
        except Exception:
            pass


def analizar_proceso(proceso_id: int, db: Session) -> dict:
    import time
    limpiar_cancelacion(proceso_id)

    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        logger.error("Proceso %s no encontrado.", proceso_id)
        return {"completados": 0, "errores": 0, "total": 0}

    candidatos = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).all()
    total = len(candidatos)
    resultados = {"completados": 0, "errores": 0, "cancelado": False, "total": total}
    tiempo_inicio = time.time()
    logger.info("Proceso %s '%s' - %s CVs", proceso_id, proceso.nombre_puesto, total)

    for idx, candidato in enumerate(candidatos, 1):

        # -- Verificar cancelacion ----------------------------------------
        if cancelacion_activa(proceso_id):
            logger.info("  Cancelado en CV %s.", idx)
            resultados["cancelado"] = True
            for c_resto in candidatos[idx - 1:]:
                try:
                    an = db.query(Analisis).filter(Analisis.candidato_id == c_resto.id).first()
                    if not an:
                        an = Analisis(candidato_id=c_resto.id)
                        db.add(an)
                    if an.estado != EstadoAnalisis.COMPLETADO:
                        an.estado    = EstadoAnalisis.ERROR
                        an.error_msg = "Cancelado por el usuario."
                except Exception:
                    pass
            try:
                db.commit()
            except Exception:
                db.rollback()
            break

        # -- Obtener o crear analisis -------------------------------------
        try:
            analisis = db.query(Analisis).filter(Analisis.candidato_id == candidato.id).first()
        except Exception as e:
            logger.error("Error consultando analisis para candidato %s: %s", candidato.id, e)
            db.rollback()
            resultados["errores"] += 1
            continue

        if analisis and analisis.estado == EstadoAnalisis.COMPLETADO:
            resultados["completados"] += 1
            continue

        if not analisis:
            analisis = Analisis(candidato_id=candidato.id)
            db.add(analisis)

        try:
            analisis.estado    = EstadoAnalisis.PROCESANDO
            analisis.error_msg = "[PROG:0] Iniciando..."
            db.commit()
            db.refresh(analisis)
        except Exception as e:
            logger.error("Error iniciando analisis candidato %s: %s", candidato.id, e)
            db.rollback()
            resultados["errores"] += 1
            continue

        nombre_archivo = Path(candidato.archivo_pdf).stem[:25]

        try:
            # -- 10%: Leer PDF --------------------------------------------
            _prog(analisis, db, 10, "[{}/{}] Leyendo PDF: {}...".format(idx, total, nombre_archivo))

            if not candidato.texto_cv:
                pdf_path = Path(candidato.archivo_pdf)
                if not pdf_path.exists():
                    raise FileNotFoundError("Archivo no encontrado: {}".format(pdf_path.name))

                texto = extraer_texto(pdf_path)
                if not texto or len(texto.strip()) < 50:
                    raise ValueError("PDF sin texto seleccionable (posible imagen escaneada).")

                candidato.texto_cv = texto
                if not candidato.email:    candidato.email    = extraer_email(texto)
                if not candidato.telefono: candidato.telefono = extraer_telefono(texto)
                db.commit()

            _prog(analisis, db, 20,
                  "[{}/{}] PDF leido - {:,} caracteres".format(idx, total, len(candidato.texto_cv)))

            # -- 40%: Llamar a la IA (datos + analisis en una sola llamada)
            _prog(analisis, db, 40,
                  "[{}/{}] Analizando con IA...".format(idx, total))

            resultado    = None
            ultimo_error = None

            for intento in range(1, MAX_REINTENTOS + 1):
                try:
                    if intento > 1:
                        _prog(analisis, db, 40,
                              "[{}/{}] Reintentando ({}/{})...".format(idx, total, intento, MAX_REINTENTOS))
                    resultado = analizar_cv_completo(
                        nombre_puesto=proceso.nombre_puesto,
                        requisitos=proceso.requisitos,
                        texto_cv=candidato.texto_cv or "",
                    )
                    break
                except ValueError as e:
                    ultimo_error = e
                    logger.warning("  JSON invalido intento %s: %s", intento, e)
                except RuntimeError:
                    raise

            if resultado is None:
                raise ultimo_error or ValueError("La IA no devolvio resultado valido.")

            # -- 85%: Guardar datos del candidato -------------------------
            _prog(analisis, db, 85,
                  "[{}/{}] Guardando resultado...".format(idx, total))

            # Actualizar datos del candidato si la IA los encontro
            if resultado.get("nombre")   and not candidato.nombre:   candidato.nombre   = resultado["nombre"]
            if resultado.get("email")    and not candidato.email:    candidato.email    = resultado["email"]
            if resultado.get("telefono") and not candidato.telefono: candidato.telefono = resultado["telefono"]

            # -- 95%: Guardar analisis ------------------------------------
            _prog(analisis, db, 95,
                  "[{}/{}] Puntaje: {:.0f}%".format(idx, total, resultado["puntaje_total"]))

            analisis.estado        = EstadoAnalisis.COMPLETADO
            analisis.puntaje_total = float(resultado["puntaje_total"])
            analisis.detalle_json  = resultado["criterios"]
            analisis.resumen_ia    = resultado["resumen"]
            analisis.proveedor_ia  = settings.IA_PROVIDER
            analisis.procesado_en  = datetime.now(timezone.utc)
            analisis.error_msg     = None
            db.commit()
            db.refresh(analisis)

            resultados["completados"] += 1
            nombre_display = candidato.nombre or nombre_archivo
            logger.info("  OK [%s/%s] %s - %.1f%%", idx, total, nombre_display, analisis.puntaje_total)

        except Exception as e:
            tb = traceback.format_exc()
            logger.error("  ERROR [%s/%s] candidato %s: %s\n%s", idx, total, candidato.id, e, tb)
            try:
                analisis.estado    = EstadoAnalisis.ERROR
                analisis.error_msg = str(e)
                db.commit()
            except Exception as e2:
                logger.error("  No se pudo guardar error: %s", e2)
                try:
                    db.rollback()
                except Exception:
                    pass
            resultados["errores"] += 1

    limpiar_cancelacion(proceso_id)
    tiempo_total = int(time.time() - tiempo_inicio)
    resultados["tiempo_total_s"] = tiempo_total
    logger.info("Proceso %s finalizado en %ss: %s", proceso_id, tiempo_total, resultados)
    return resultados
