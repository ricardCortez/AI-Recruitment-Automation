# -*- coding: utf-8 -*-
"""
Servicio de análisis — pipeline paralelo.

Arquitectura:
  1. Pre-procesamiento rápido (PDF → texto, regex para nombre/email/teléfono)
  2. Extracción de secciones relevantes (sin LLM)
  3. Llamada a Ollama con prompt mínimo
  4. Guardado de resultados

Los pasos 1-3 se ejecutan en paralelo con ThreadPoolExecutor.
Cada worker crea su propia sesión de DB para evitar conflictos de SQLite.
"""

import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.candidato import Candidato
from app.models.proceso import Proceso
from app.models.analisis import Analisis, EstadoAnalisis
from app.services.pdf_service import (
    extraer_texto, extraer_nombre, extraer_email, extraer_telefono,
    extraer_secciones_relevantes,
)
from app.services.ia_service import analizar_cv_completo
from app.services.extractor_nombre import NOMBRE_NO_IDENTIFICADO
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
MAX_REINTENTOS = 2


# ── Compresión de texto ────────────────────────────────────────────────────────

def _comprimir_texto(texto: str) -> str:
    """
    Colapsa líneas en blanco consecutivas a una sola y elimina espacios
    al inicio/fin de cada línea. Reduce tokens sin perder información.
    """
    lineas = texto.splitlines()
    resultado: list[str] = []
    blancos_consecutivos = 0
    for linea in lineas:
        limpia = linea.strip()
        if not limpia:
            blancos_consecutivos += 1
            if blancos_consecutivos == 1:
                resultado.append("")
        else:
            blancos_consecutivos = 0
            resultado.append(limpia)
    return "\n".join(resultado).strip()


# ── Cancelación ───────────────────────────────────────────────────────────────

_cancelar: set[int] = set()

def solicitar_cancelacion(proceso_id: int):
    _cancelar.add(proceso_id)

def cancelacion_activa(proceso_id: int) -> bool:
    return proceso_id in _cancelar

def limpiar_cancelacion(proceso_id: int):
    _cancelar.discard(proceso_id)


# ── Progreso ──────────────────────────────────────────────────────────────────

def _prog(analisis: Analisis, db: Session, pct: int, mensaje: str):
    try:
        analisis.progress_msg = "[PROG:{}] {}".format(pct, mensaje)
        db.commit()
        logger.info("  [%s%%] %s", pct, mensaje)
    except Exception as e:
        logger.warning("No se pudo guardar progreso: %s", e)
        try:
            db.rollback()
        except Exception:
            pass


# ── Workers ───────────────────────────────────────────────────────────────────

def _get_max_workers() -> int:
    """
    2 workers en CPU (pipeline: mientras Ollama trabaja, el otro pre-procesa el siguiente CV).
    3 workers en GPU (mayor concurrencia: la GPU puede atender más de una inferencia).
    """
    try:
        from app.api.config import leer_config
        cfg = leer_config()
        return 3 if cfg.get("dispositivo") == "gpu" else 2
    except Exception:
        return 2


def _analizar_candidato_worker(
    proceso_id: int,
    candidato_id: int,
    idx: int,
    total: int,
    nombre_puesto: str,
    requisitos: str,
) -> dict:
    """
    Procesa UN candidato. Crea y cierra su propia sesión de DB.
    Retorna {"ok": True/False, ...}.
    """
    db = SessionLocal()
    try:
        candidato = db.query(Candidato).filter(Candidato.id == candidato_id).first()
        if not candidato:
            return {"ok": False, "error": "Candidato {} no encontrado.".format(candidato_id)}

        # Saltar si ya está completado
        analisis = db.query(Analisis).filter(Analisis.candidato_id == candidato_id).first()
        if analisis and analisis.estado == EstadoAnalisis.COMPLETADO:
            return {"ok": True, "saltado": True}

        if not analisis:
            analisis = Analisis(candidato_id=candidato_id)
            db.add(analisis)

        try:
            analisis.estado    = EstadoAnalisis.PROCESANDO
            analisis.error_msg = "[PROG:0] Iniciando..."
            db.commit()
            db.refresh(analisis)
        except Exception as e:
            logger.error("Error iniciando analisis candidato %s: %s", candidato_id, e)
            db.rollback()
            return {"ok": False, "error": str(e)}

        nombre_archivo = Path(candidato.archivo_pdf).stem[:25]

        # ── 10 %: Leer PDF ─────────────────────────────────────────────────
        _prog(analisis, db, 10, "[{}/{}] Leyendo PDF: {}...".format(idx, total, nombre_archivo))

        if not candidato.texto_cv:
            pdf_path = Path(candidato.archivo_pdf)
            if not pdf_path.exists():
                raise FileNotFoundError("Archivo no encontrado: {}".format(pdf_path.name))

            texto = extraer_texto(pdf_path)
            if not texto or len(texto.strip()) < 50:
                raise ValueError(
                    "'{name}' no tiene texto seleccionable. "
                    "El PDF parece estar escaneado como imagen. "
                    "Convertilo a PDF con texto (usá OCR) antes de subirlo.".format(
                        name=pdf_path.name
                    )
                )

            candidato.texto_cv = texto
            if not candidato.nombre:
                candidato.nombre = extraer_nombre(texto, pdf_path=pdf_path)
            if not candidato.email:    candidato.email    = extraer_email(texto)
            if not candidato.telefono: candidato.telefono = extraer_telefono(texto)
            db.commit()

        _prog(analisis, db, 20,
              "[{}/{}] PDF leido — {:,} chars".format(idx, total, len(candidato.texto_cv)))

        # ── Verificar cancelación antes de llamar a Ollama ─────────────────
        if cancelacion_activa(proceso_id):
            analisis.estado    = EstadoAnalisis.ERROR
            analisis.error_msg = "Cancelado por el usuario."
            analisis.progress_msg = None
            db.commit()
            return {"ok": False, "cancelado": True}

        # ── 40 %: Preparar texto y llamar a la IA ──────────────────────────
        _prog(analisis, db, 40, "[{}/{}] Analizando con IA...".format(idx, total))

        # 1. Comprimir (elimina líneas en blanco redundantes)
        texto_comprimido = _comprimir_texto(candidato.texto_cv or "")
        # 2. Extraer secciones relevantes (envía < texto al LLM → inferencia más rápida)
        texto_para_ia = extraer_secciones_relevantes(texto_comprimido)

        resultado    = None
        ultimo_error = None

        for intento in range(1, MAX_REINTENTOS + 1):
            if cancelacion_activa(proceso_id):
                break
            try:
                if intento > 1:
                    _prog(analisis, db, 40,
                          "[{}/{}] Reintentando ({}/{})...".format(idx, total, intento, MAX_REINTENTOS))
                resultado = analizar_cv_completo(
                    nombre_puesto=nombre_puesto,
                    requisitos=requisitos,
                    texto_cv=texto_para_ia,
                )
                break
            except ValueError as e:
                ultimo_error = e
                logger.warning("  JSON invalido intento %s: %s", intento, e)
            except RuntimeError:
                raise

        if cancelacion_activa(proceso_id):
            analisis.estado    = EstadoAnalisis.ERROR
            analisis.error_msg = "Cancelado por el usuario."
            analisis.progress_msg = None
            db.commit()
            return {"ok": False, "cancelado": True}

        if resultado is None:
            raise ultimo_error or ValueError("La IA no devolvio resultado valido.")

        # ── 85 %: Guardar datos del candidato ──────────────────────────────
        _prog(analisis, db, 85, "[{}/{}] Guardando resultado...".format(idx, total))

        nombre_ia = resultado.get("nombre")
        # La IA tiene todo el texto del CV y es más precisa que la heurística.
        # Siempre usamos el nombre que devuelve la IA si proporciona uno.
        # Solo conservamos el nombre previo si la IA no devolvió ninguno.
        if nombre_ia:
            candidato.nombre = nombre_ia
        elif not candidato.nombre or candidato.nombre == NOMBRE_NO_IDENTIFICADO:
            candidato.nombre = None  # Sin nombre confirmado
        if resultado.get("email")    and not candidato.email:    candidato.email    = resultado["email"]
        if resultado.get("telefono") and not candidato.telefono: candidato.telefono = resultado["telefono"]

        # ── 95 %: Guardar análisis ──────────────────────────────────────────
        _prog(analisis, db, 95,
              "[{}/{}] Puntaje: {:.0f}%".format(idx, total, resultado["puntaje_total"]))

        analisis.estado         = EstadoAnalisis.COMPLETADO
        analisis.puntaje_total  = float(resultado["puntaje_total"])
        analisis.detalle_json   = resultado["criterios"]
        analisis.resumen_ia     = resultado["resumen"]
        analisis.alertas_json   = resultado.get("alertas", [])   # ← antes no se guardaba
        analisis.preguntas_json = resultado.get("preguntas", []) # ← antes no se guardaba
        analisis.proveedor_ia   = settings.IA_PROVIDER
        analisis.procesado_en   = datetime.now(timezone.utc)
        analisis.error_msg      = None
        analisis.progress_msg   = None
        db.commit()
        db.refresh(analisis)

        nombre_display = candidato.nombre or nombre_archivo
        logger.info("  OK [%s/%s] %s — %.1f%%", idx, total, nombre_display, analisis.puntaje_total)
        return {"ok": True, "puntaje": analisis.puntaje_total, "nombre": nombre_display}

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("  ERROR [%s/%s] candidato %s: %s\n%s", idx, total, candidato_id, e, tb)
        try:
            analisis = db.query(Analisis).filter(Analisis.candidato_id == candidato_id).first()
            if analisis:
                analisis.estado       = EstadoAnalisis.ERROR
                analisis.error_msg    = str(e)
                analisis.progress_msg = None
                db.commit()
        except Exception as e2:
            logger.error("  No se pudo guardar error: %s", e2)
            try:
                db.rollback()
            except Exception:
                pass
        return {"ok": False, "error": str(e)}

    finally:
        db.close()


# ── Orquestador principal ─────────────────────────────────────────────────────

def analizar_proceso(proceso_id: int, db: Session) -> dict:
    limpiar_cancelacion(proceso_id)

    proceso = db.query(Proceso).filter(Proceso.id == proceso_id).first()
    if not proceso:
        logger.error("Proceso %s no encontrado.", proceso_id)
        return {"completados": 0, "errores": 0, "total": 0}

    candidatos = db.query(Candidato).filter(Candidato.proceso_id == proceso_id).all()
    total      = len(candidatos)
    tiempo_inicio = time.time()
    resultados = {"completados": 0, "errores": 0, "cancelado": False, "total": total}

    nombre_puesto = proceso.nombre_puesto
    requisitos    = proceso.requisitos

    # Separar ya-completados de los que hay que procesar
    ya_completados = 0
    pendientes: list[tuple[int, Candidato]] = []
    for idx, candidato in enumerate(candidatos, 1):
        analisis = db.query(Analisis).filter(Analisis.candidato_id == candidato.id).first()
        if analisis and analisis.estado == EstadoAnalisis.COMPLETADO:
            ya_completados += 1
        else:
            pendientes.append((idx, candidato))

    resultados["completados"] = ya_completados
    max_workers = _get_max_workers()
    logger.info(
        "Proceso %s '%s' — %s CVs (%s pendientes, %s workers)",
        proceso_id, nombre_puesto, total, len(pendientes), max_workers,
    )

    if not pendientes:
        return resultados

    # Lanzar workers en paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map: dict[Future, tuple] = {
            executor.submit(
                _analizar_candidato_worker,
                proceso_id, candidato.id, idx, total, nombre_puesto, requisitos,
            ): (idx, candidato)
            for idx, candidato in pendientes
        }

        for future in as_completed(future_map):
            result = future.result()

            if result.get("cancelado"):
                resultados["cancelado"] = True
                # Cancelar futures que aún no empezaron
                for f in future_map:
                    f.cancel()

            elif result.get("saltado"):
                resultados["completados"] += 1

            elif result.get("ok"):
                resultados["completados"] += 1

            else:
                resultados["errores"] += 1

            # Si se canceló, marcar los que no se pudieron procesar
            if resultados["cancelado"]:
                for f, (_, c) in future_map.items():
                    if not f.done():
                        try:
                            _db = SessionLocal()
                            an = _db.query(Analisis).filter(Analisis.candidato_id == c.id).first()
                            if an and an.estado != EstadoAnalisis.COMPLETADO:
                                an.estado    = EstadoAnalisis.ERROR
                                an.error_msg = "Cancelado por el usuario."
                                _db.commit()
                        except Exception:
                            pass
                        finally:
                            _db.close()
                break

    limpiar_cancelacion(proceso_id)
    tiempo_total = int(time.time() - tiempo_inicio)
    resultados["tiempo_total_s"] = tiempo_total
    logger.info("Proceso %s finalizado en %ss: %s", proceso_id, tiempo_total, resultados)
    return resultados
