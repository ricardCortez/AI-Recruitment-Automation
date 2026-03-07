"""
Servicio de análisis — completamente SÍNCRONO.
Elimina asyncio.run() y async/await que causaban el bug de 1 solo CV procesado.
"""

import traceback
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.candidato import Candidato
from app.models.proceso import Proceso
from app.models.analisis import Analisis, EstadoAnalisis
from app.services.pdf_service import extraer_texto, extraer_email, extraer_telefono
from app.services.ia_service import analizar_cv, extraer_datos_cv
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
MAX_REINTENTOS = 2

# ── Flag de cancelación ───────────────────────────────────────────────────────
_cancelar: set[int] = set()

def solicitar_cancelacion(proceso_id: int): _cancelar.add(proceso_id)
def cancelacion_activa(proceso_id: int) -> bool: return proceso_id in _cancelar
def limpiar_cancelacion(proceso_id: int): _cancelar.discard(proceso_id)


def _prog(analisis: Analisis, db: Session, pct: int, mensaje: str):
    analisis.error_msg = f"[PROG:{pct}] {mensaje}"
    db.commit()
    logger.info(f"  [{pct}%] {mensaje}")


# ── Función principal — SÍNCRONA ──────────────────────────────────────────────
def analizar_proceso(proceso_id: int, db: Session) -> dict:
    """
    Analiza todos los CVs de un proceso secuencialmente.
    SÍNCRONO — sin async/await para evitar conflictos de event loop.
    """
    limpiar_cancelacion(proceso_id)

    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        logger.error(f"Proceso {proceso_id} no encontrado.")
        return {"completados": 0, "errores": 0, "total": 0}

    candidatos = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).all()
    total = len(candidatos)
    resultados = {"completados": 0, "errores": 0, "cancelado": False, "total": total}
    logger.info(f"▶ Proceso {proceso_id} '{proceso.nombre_puesto}' — {total} CVs")

    for idx, candidato in enumerate(candidatos, 1):

        # ── Verificar cancelación ─────────────────────────────────
        if cancelacion_activa(proceso_id):
            logger.info(f"  ⛔ Cancelado por el usuario en CV {idx}.")
            resultados["cancelado"] = True
            for c_resto in candidatos[idx - 1:]:
                an = db.query(Analisis).filter(Analisis.candidato_id == c_resto.id).first()
                if not an:
                    an = Analisis(candidato_id=c_resto.id)
                    db.add(an)
                if an.estado != EstadoAnalisis.COMPLETADO:
                    an.estado    = EstadoAnalisis.ERROR
                    an.error_msg = "Análisis cancelado por el usuario."
            db.commit()
            break

        # ── Obtener o crear registro de análisis ──────────────────
        analisis = db.query(Analisis).filter(Analisis.candidato_id == candidato.id).first()

        if analisis and analisis.estado == EstadoAnalisis.COMPLETADO:
            resultados["completados"] += 1
            continue

        if not analisis:
            analisis = Analisis(candidato_id=candidato.id)
            db.add(analisis)

        analisis.estado    = EstadoAnalisis.PROCESANDO
        analisis.error_msg = f"[PROG:0] Iniciando..."
        db.commit()
        db.refresh(analisis)

        nombre_archivo = Path(candidato.archivo_pdf).stem[:25]

        try:
            # ── 10% Leer PDF ──────────────────────────────────────
            _prog(analisis, db, 10, f"[{idx}/{total}] Leyendo PDF: {nombre_archivo}...")

            if not candidato.texto_cv:
                pdf_path = Path(candidato.archivo_pdf)
                if not pdf_path.exists():
                    raise FileNotFoundError(f"Archivo no encontrado: {pdf_path.name}")

                texto = extraer_texto(pdf_path)
                if not texto or len(texto.strip()) < 50:
                    raise ValueError("PDF sin texto seleccionable (puede ser imagen escaneada).")

                candidato.texto_cv = texto
                if not candidato.email:    candidato.email    = extraer_email(texto)
                if not candidato.telefono: candidato.telefono = extraer_telefono(texto)
                db.commit()

            _prog(analisis, db, 20, f"[{idx}/{total}] PDF leído — {len(candidato.texto_cv):,} caracteres")

            # ── 30% Identificar candidato con IA ─────────────────
            _prog(analisis, db, 30, f"[{idx}/{total}] Identificando datos del candidato...")

            datos = extraer_datos_cv(candidato.texto_cv)

            if datos.get("nombre")   and not candidato.nombre:   candidato.nombre   = datos["nombre"]
            if datos.get("email")    and not candidato.email:    candidato.email    = datos["email"]
            if datos.get("telefono") and not candidato.telefono: candidato.telefono = datos["telefono"]
            db.commit()

            nombre_display = candidato.nombre or nombre_archivo
            encontrados = [k for k, v in datos.items() if v]
            _prog(analisis, db, 40,
                  f"[{idx}/{total}] Candidato: {nombre_display} · {', '.join(encontrados) if encontrados else 'sin datos'}")

            # ── 55% Análisis IA ───────────────────────────────────
            _prog(analisis, db, 55, f"[{idx}/{total}] Evaluando CV de {nombre_display}...")

            resultado    = None
            ultimo_error = None

            for intento in range(1, MAX_REINTENTOS + 1):
                try:
                    if intento > 1:
                        _prog(analisis, db, 55,
                              f"[{idx}/{total}] Reintentando análisis ({intento}/{MAX_REINTENTOS})...")
                    resultado = analizar_cv(
                        nombre_puesto=proceso.nombre_puesto,
                        requisitos=proceso.requisitos,
                        texto_cv=candidato.texto_cv or "",
                    )
                    break
                except ValueError as e:
                    ultimo_error = e
                    logger.warning(f"  JSON inválido intento {intento}: {e}")
                except RuntimeError:
                    raise

            if resultado is None:
                raise ultimo_error or ValueError("La IA no devolvió resultado válido.")

            _prog(analisis, db, 85, f"[{idx}/{total}] Generando resumen de {nombre_display}...")
            _prog(analisis, db, 95, f"[{idx}/{total}] Guardando — Puntaje: {resultado['puntaje_total']:.0f}%")

            # ── Guardar resultado ─────────────────────────────────
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
            logger.info(f"  ✓ [{idx}/{total}] {nombre_display} — {analisis.puntaje_total:.1f}%")

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"  ✗ [{idx}/{total}] CV {candidato.id}: {e}\n{tb}")
            try:
                analisis.estado    = EstadoAnalisis.ERROR
                analisis.error_msg = str(e)
                db.commit()
            except Exception:
                db.rollback()
            resultados["errores"] += 1

    limpiar_cancelacion(proceso_id)
    logger.info(f"■ Proceso {proceso_id} finalizado — {resultados}")
    return resultados
