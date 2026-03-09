# -*- coding: utf-8 -*-
"""
Servicio de analisis - SINCRONO.
Usa analizar_cv_completo() que hace una sola llamada a Ollama por CV.
"""

import time
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
        # Usar progress_msg separado de error_msg para evitar race condition
        analisis.progress_msg = "[PROG:{}] {}".format(pct, mensaje)
        db.commit()
        logger.info("  [%s%%] %s", pct, mensaje)
    except Exception as e:
        logger.warning("No se pudo guardar progreso: %s", e)
        try:
            db.rollback()
        except Exception:
            pass


def _extraer_nombre_fallback(texto: str) -> str | None:
    """Extrae el nombre de las primeras lineas del CV como fallback."""
    import re

    NO_NOMBRE = {
        # Titulos profesionales
        "ingeniero","ing","licenciado","lic","bachiller","tecnico","doctor","dr",
        "magister","mg","arquitecto","abogado","contador","analista","especialista",
        "profesional","coordinador","supervisor","gerente","jefe","asistente",
        "desarrollador","programador","consultor","ejecutivo","director",
        # Secciones de CV
        "curriculum","vitae","cv","datos","perfil","resumen","experiencia",
        "educacion","estudios","habilidades","certificados","referencias",
        "informacion","personal","contacto","objetivo","presentacion","summary",
        # Tecnologia / areas
        "sistemas","computacion","informatica","tecnologia","software","hardware",
        "redes","seguridad","administracion","gestion","informatico",
        # Ciudades / paises
        "lima","peru","arequipa","trujillo","chiclayo","cusco","piura","iquitos",
        "tacna","huancayo","ica","pucallpa","cajamarca","chimbote",
        # PALABRAS DE DIRECCION — clave para este fix
        "jiron","jr","jirón","avenida","av","calle","ca","pasaje","pje",
        "manzana","mz","lote","lt","bloque","bl","sector","urbanizacion","urb",
        "villa","condominio","residencial","interior","int","departamento",
        "dpto","piso","parcela","cooperativa","asociacion","agrupacion",
        "vmt","ate","sjl","sjm","smp","vmr","callao","barranco","miraflores",
        "surco","surquillo","chorrillos","lince","breña","rimac","carabayllo",
        "comas","independencia","puente","piedra","lurin","pachacamac",
        "san","santa","santo","gabriel","borja","isidro","miguel","martin",
        # Conectores / preposiciones
        "de","del","la","los","las","en","con","para","por","y","e","o",
        "nombres","apellidos","nacionalidad","idiomas","espanol","ingles",
        "fecha","nacimiento","domicilio","lugar",
    }

    CHARS_MAL = ('+', '|', '#', '(', ')', '@', '°')
    KEYS_MAL  = ['http','www','linkedin','github','telefono','celular',
                 'email','correo','direccion','domicilio','dni','ruc', ':']

    # Patrones que indican direccion o dato de contacto — nunca son nombres
    PATRON_DIRECCION = re.compile(
        r'^\d+|'                          # empieza con numero
        r'\b\d{3,}\b|'                    # tiene numero de 3+ digitos (N° casa)
        r'\b(jr\.?|av\.?|cll?\.?)\b|'    # abreviatura de via
        r'\bmz\b|\blt\b|\bint\b|'        # manzana/lote/interior
        r'\b[A-Z]{2,4}\b.*\b[A-Z]{2,4}\b',  # siglas seguidas tipo "VMT SJL"
        re.IGNORECASE
    )

    def es_palabra_nombre(p: str) -> bool:
        return bool(re.match(r'^[A-Za-z\u00C0-\u024F]+$', p)) and len(p) >= 2

    def es_candidato(linea: str) -> bool:
        if len(linea) < 4 or len(linea) > 65:
            return False
        if any(k in linea.lower() for k in KEYS_MAL):
            return False
        if any(ch in linea for ch in CHARS_MAL):
            return False
        if re.search(r'\d{4}', linea):
            return False
        if re.search(r'\d{5,}', linea):
            return False
        if PATRON_DIRECCION.search(linea):
            return False
        palabras = linea.split()
        if len(palabras) < 1 or len(palabras) > 6:
            return False
        palabras_norm = {p.lower().strip('.,;:') for p in palabras}
        if palabras_norm & NO_NOMBRE:
            return False
        validas = [p for p in palabras if es_palabra_nombre(p)]
        return len(validas) >= 1

    lineas = [l.strip() for l in texto.splitlines() if l.strip()][:25]

    # Intentar lineas individuales primero
    for linea in lineas:
        if not es_candidato(linea):
            continue
        palabras = linea.split()
        validas = [p for p in palabras if es_palabra_nombre(p)]
        if len(validas) >= 2:
            if linea == linea.upper():
                linea = linea.title()
            return linea

    # Intentar unir dos lineas consecutivas cortas (nombre partido en dos renglones)
    for i in range(len(lineas) - 1):
        l1, l2 = lineas[i], lineas[i + 1]
        if es_candidato(l1) and es_candidato(l2):
            unida = l1 + " " + l2
            if len(unida) <= 65:
                palabras = unida.split()
                validas = [p for p in palabras if es_palabra_nombre(p)]
                if len(validas) >= 3:
                    if unida == unida.upper():
                        unida = unida.title()
                    return unida

    return None
def analizar_proceso(proceso_id: int, db: Session) -> dict:
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
            for c_resto in candidatos[idx:]:
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
            analisis.estado       = EstadoAnalisis.PROCESANDO
            analisis.progress_msg = "[PROG:0] Iniciando..."
            analisis.error_msg    = None  # Limpiar error previo al reiniciar
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
                    raise ValueError(
                        "'{name}' no tiene texto seleccionable. "
                        "El PDF parece estar escaneado como imagen. "
                        "Convertilo a PDF con texto (usá OCR) antes de subirlo.".format(
                            name=pdf_path.name
                        )
                    )

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

            # Actualizar datos del candidato — commit separado para asegurar persistencia
            nombre_ia    = resultado.get("nombre")
            email_ia     = resultado.get("email")
            telefono_ia  = resultado.get("telefono")

            # Fallback: extraer nombre del texto del CV si la IA no lo devolvio
            if not nombre_ia and candidato.texto_cv:
                nombre_ia = _extraer_nombre_fallback(candidato.texto_cv)

            if nombre_ia:   candidato.nombre   = nombre_ia.strip()
            if email_ia:    candidato.email    = email_ia.strip()
            if telefono_ia: candidato.telefono = telefono_ia.strip()

            # Commit y refresh explicito del candidato ANTES de continuar
            try:
                db.commit()
                db.refresh(candidato)
                logger.info("  Candidato guardado: nombre='%s' email='%s'", candidato.nombre, candidato.email)
            except Exception as e_c:
                logger.warning("  Error guardando candidato: %s", e_c)
                db.rollback()

            # -- 95%: Recalcular puntaje desde criterios (no confiar en el valor del modelo)
            criterios_ia = resultado.get("criterios") or []
            tiene_peso = criterios_ia and criterios_ia[0].get("peso") is not None
            if tiene_peso and criterios_ia:
                puntaje_calculado = round(sum(
                    (c.get("peso", 0) * c.get("puntaje", 0) / 100)
                    for c in criterios_ia
                ), 1)
            else:
                puntajes = [c.get("puntaje", 0) for c in criterios_ia if c.get("puntaje") is not None]
                puntaje_calculado = round(sum(puntajes) / len(puntajes), 1) if puntajes else round(float(resultado.get("puntaje_total", 0)), 1)

            logger.info("  Puntaje IA=%s, recalculado=%s", resultado.get("puntaje_total"), puntaje_calculado)

            _prog(analisis, db, 95,
                  "[{}/{}] Puntaje: {:.0f}%".format(idx, total, puntaje_calculado))

            analisis.estado        = EstadoAnalisis.COMPLETADO
            analisis.puntaje_total = puntaje_calculado
            analisis.detalle_json  = resultado["criterios"]
            analisis.resumen_ia    = resultado["resumen"]
            analisis.proveedor_ia  = "{}/{}".format(settings.IA_PROVIDER, settings.OLLAMA_MODEL) if settings.IA_PROVIDER == "ollama" else settings.IA_PROVIDER
            analisis.procesado_en  = datetime.now(timezone.utc)
            analisis.error_msg     = None
            analisis.progress_msg  = None  # Limpiar progreso al completar
            db.commit()
            db.refresh(analisis)

            resultados["completados"] += 1
            nombre_display = candidato.nombre or nombre_archivo
            logger.info("  OK [%s/%s] %s - %.1f%%", idx, total, nombre_display, analisis.puntaje_total)

        except Exception as e:
            tb = traceback.format_exc()
            logger.error("  ERROR [%s/%s] candidato %s: %s\n%s", idx, total, candidato.id, e, tb)
            try:
                analisis.estado       = EstadoAnalisis.ERROR
                analisis.error_msg    = str(e)
                analisis.progress_msg = None  # Limpiar progreso al fallar
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