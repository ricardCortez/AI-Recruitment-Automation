"""
Servicio de análisis con:
- Progreso granular en tiempo real
- Control de cancelación (stop/cancel)
- El background task verifica el flag entre cada CV
"""

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

# ── Flag de cancelación en memoria ──────────────────────────────────────────
# Set de proceso_ids que deben detenerse. El background task lo consulta entre CVs.
_cancelar: set[int] = set()

def solicitar_cancelacion(proceso_id: int):
    _cancelar.add(proceso_id)

def cancelacion_activa(proceso_id: int) -> bool:
    return proceso_id in _cancelar

def limpiar_cancelacion(proceso_id: int):
    _cancelar.discard(proceso_id)


def _prog(analisis: Analisis, db: Session, pct: int, mensaje: str):
    analisis.error_msg = f"[PROG:{pct}] {mensaje}"
    db.commit()
    logger.info(f"  [{pct}%] {mensaje}")


async def analizar_proceso(proceso_id: int, db: Session) -> dict:
    limpiar_cancelacion(proceso_id)

    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        logger.error(f"Proceso {proceso_id} no encontrado.")
        return {"completados": 0, "errores": 0, "total": 0}

    candidatos = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).all()
    resultados = {"completados": 0, "errores": 0, "cancelado": False, "total": len(candidatos)}
    logger.info(f"Proceso {proceso_id} '{proceso.nombre_puesto}' — {len(candidatos)} CVs")

    for idx, candidato in enumerate(candidatos, 1):

        # ── Verificar cancelación antes de cada CV ─────────────────
        if cancelacion_activa(proceso_id):
            logger.info(f"  ⛔ Proceso {proceso_id} cancelado por el usuario.")
            resultados["cancelado"] = True

            # Marcar candidatos pendientes/procesando como cancelados
            an_actual = db.query(Analisis).filter(Analisis.candidato_id == candidato.id).first()
            if an_actual and an_actual.estado in (EstadoAnalisis.PENDIENTE, EstadoAnalisis.PROCESANDO):
                an_actual.estado    = EstadoAnalisis.ERROR
                an_actual.error_msg = "Análisis cancelado por el usuario."
                db.commit()

            # Marcar el resto también
            for c_resto in candidatos[idx:]:
                an = db.query(Analisis).filter(Analisis.candidato_id == c_resto.id).first()
                if not an:
                    an = Analisis(candidato_id=c_resto.id)
                    db.add(an)
                an.estado    = EstadoAnalisis.ERROR
                an.error_msg = "Análisis cancelado por el usuario."
            db.commit()
            break

        analisis = db.query(Analisis).filter(Analisis.candidato_id == candidato.id).first()

        if analisis and analisis.estado == EstadoAnalisis.COMPLETADO:
            resultados["completados"] += 1
            continue

        if not analisis:
            analisis = Analisis(candidato_id=candidato.id)
            db.add(analisis)

        analisis.estado    = EstadoAnalisis.PROCESANDO
        analisis.error_msg = f"[PROG:0] Iniciando análisis..."
        db.commit()
        db.refresh(analisis)

        nombre_archivo = Path(candidato.archivo_pdf).stem[:25]

        try:
            # ── 10%: Leer PDF ─────────────────────────────────────
            _prog(analisis, db, 10, f"[{idx}/{len(candidatos)}] Leyendo PDF: {nombre_archivo}...")

            if not candidato.texto_cv:
                pdf_path = Path(candidato.archivo_pdf)
                if not pdf_path.exists():
                    raise FileNotFoundError(f"Archivo no encontrado: {pdf_path}")

                texto = extraer_texto(pdf_path)
                if not texto or len(texto.strip()) < 50:
                    raise ValueError("El PDF no tiene texto seleccionable (posible imagen escaneada).")

                candidato.texto_cv = texto
                if not candidato.email:    candidato.email    = extraer_email(texto)
                if not candidato.telefono: candidato.telefono = extraer_telefono(texto)
                db.commit()

            _prog(analisis, db, 20, f"[{idx}/{len(candidatos)}] PDF leído — {len(candidato.texto_cv):,} caracteres")

            # ── 30%: Identificar candidato ────────────────────────
            _prog(analisis, db, 30, f"[{idx}/{len(candidatos)}] Identificando datos del candidato...")

            datos_ia = await extraer_datos_cv(candidato.texto_cv)

            if datos_ia.get("nombre")   and not candidato.nombre:   candidato.nombre   = datos_ia["nombre"]
            if datos_ia.get("email")    and not candidato.email:    candidato.email    = datos_ia["email"]
            if datos_ia.get("telefono") and not candidato.telefono: candidato.telefono = datos_ia["telefono"]
            db.commit()

            nombre_display = candidato.nombre or nombre_archivo
            encontrados = [k for k, v in datos_ia.items() if v]
            _prog(analisis, db, 40,
                  f"[{idx}/{len(candidatos)}] Candidato: {nombre_display} · {', '.join(encontrados) if encontrados else 'sin datos de contacto'}")

            # ── 50%: Análisis IA ──────────────────────────────────
            _prog(analisis, db, 50, f"[{idx}/{len(candidatos)}] Evaluando conocimientos de {nombre_display}...")

            resultado    = None
            ultimo_error = None

            for intento in range(1, MAX_REINTENTOS + 1):
                try:
                    if intento == 1:
                        _prog(analisis, db, 60, f"[{idx}/{len(candidatos)}] Analizando experiencia laboral y formación...")
                    else:
                        _prog(analisis, db, 60, f"[{idx}/{len(candidatos)}] Reintentando análisis ({intento}/{MAX_REINTENTOS})...")

                    resultado = await analizar_cv(
                        nombre_puesto=proceso.nombre_puesto,
                        requisitos=proceso.requisitos,
                        texto_cv=candidato.texto_cv or "",
                    )
                    break
                except ValueError as e:
                    ultimo_error = e
                except RuntimeError:
                    raise

            if resultado is None:
                raise ultimo_error or ValueError("La IA no devolvió resultado válido.")

            _prog(analisis, db, 85, f"[{idx}/{len(candidatos)}] Generando resumen ejecutivo de {nombre_display}...")
            _prog(analisis, db, 95, f"[{idx}/{len(candidatos)}] Guardando — Puntaje: {resultado['puntaje_total']:.0f}%")

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
            logger.info(f"  ✓ {nombre_display} — {analisis.puntaje_total:.1f}%")

        except Exception as e:
            analisis.estado    = EstadoAnalisis.ERROR
            analisis.error_msg = str(e)
            db.commit()
            resultados["errores"] += 1
            logger.error(f"  ✗ CV {candidato.id}: {e}")

    limpiar_cancelacion(proceso_id)
    logger.info(f"Proceso {proceso_id} finalizado — {resultados}")
    return resultados
