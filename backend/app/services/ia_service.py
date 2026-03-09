# -*- coding: utf-8 -*-
"""
Motor de IA — v4
- Tokens por modelo: 7b sube a 2500 (es mas verboso con CVs tecnicos largos)
- Retry automatico: si JSON falla, reintenta con prompt minimo de rescate
- Normalizacion de "cumple": acepta "cumple"/"no cumple"/"parcialmente" ademas de si/parcial/no
- _reparar_json mejorado: maneja truncado mid-string
"""

import json
import re
import os
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Parametros por modelo: num_predict = tokens de salida, num_ctx = ventana total
MODELO_PARAMS = {
    "llama3.1:8b":  {"num_predict": 1400, "num_ctx": 4096, "verboso": False},
    "qwen2.5:7b":   {"num_predict": 2500, "num_ctx": 4096, "verboso": True},   # 7b muy verboso
    "qwen2.5:14b":  {"num_predict": 1400, "num_ctx": 4096, "verboso": False},
    "qwen2.5:32b":  {"num_predict": 1400, "num_ctx": 4096, "verboso": False},
}

_INST_CORTA  = " Descripciones MUY CORTAS: max 6 palabras por criterio."
_INST_NORMAL = " Descripciones concisas: max 12 palabras por criterio."

PROMPT_COMPLETO = """Eres un evaluador experto en RRHH. Debes evaluar con MAXIMA PRECISION y RIGOR el CV vs los requisitos del puesto.
REGLA DE ORO: cada candidato recibe el puntaje que REALMENTE merece segun su CV. NO nivelar todos en rangos similares.{instruccion}
Responde SOLO JSON valido, sin markdown ni texto extra.

PUESTO: {nombre_puesto}
REQUISITOS EXACTOS DEL PUESTO:
{requisitos}

CV DEL CANDIDATO:
{texto_cv}

INSTRUCCIONES PASO A PASO:

PASO 1 — Define los criterios principales agrupando los requisitos (ej: Experiencia, Conocimientos Tecnicos, Funciones, Idiomas).

PASO 2 — Asigna PESO a cada criterio segun su importancia para el puesto. Todos los pesos deben sumar exactamente 100.

PASO 3 — Para cada criterio, compara LITERALMENTE lo que pide el requisito vs lo que tiene el candidato:
  - Lee el requisito palabra por palabra
  - Busca en el CV si cumple CADA punto del requisito
  - Asigna PUNTAJE 0-100 con esta escala ESTRICTA:
      95-100 = supera ampliamente (ej: pide 3-4 anos, tiene 8+; pide intermedio, tiene avanzado)
      80-94  = cumple bien la mayoria de puntos del criterio
      65-79  = cumple los puntos principales pero falta alguno secundario
      45-64  = cumple parcialmente, faltan puntos importantes
      20-44  = brechas importantes, cumple menos de la mitad
      0-19   = no cumple o casi no tiene lo que se pide

PASO 4 — puntaje_total = suma exacta de (peso_i * puntaje_i / 100) para todos los criterios.
  VERIFICA que el calculo sea correcto antes de responder.

PASO 5 — cumple: "si" si puntaje>=70 | "parcial" si 40-69 | "no" si <40

PASO 6 — descripcion: UNA sola frase corta (max 10 palabras) describiendo lo hallado en el CV para ese criterio. Ejemplos: "8 anos en TI, jefatura en empresas medianas" / "Inglés avanzado certificado" / "Sin experiencia en instituciones educativas".

PASO 7 — resumen: primera palabra "APTO" o "NO APTO", luego fortalezas y brechas especificas del CV.

JSON exacto (sin texto antes ni despues):
{{"nombre":"<str|null>","email":"<str|null>","telefono":"<str|null>","puntaje_total":<0-100>,"criterios":[{{"criterio":"<str>","peso":<0-100>,"puntaje":<0-100>,"cumple":"<si|parcial|no>","descripcion":"<frase corta de lo hallado en el CV>"}}],"resumen":"<APTO/NO APTO: fortalezas y brechas>"}}"""

# Prompt minimo de rescate — usado en retry cuando el JSON del primer intento falla
PROMPT_RESCATE = """Evalua este CV para el puesto. Responde SOLO con JSON valido. Sin texto extra.

PUESTO: {nombre_puesto}
REQUISITOS: {requisitos_cortos}
CV (resumen): {cv_corto}

JSON (peso=importancia del criterio, puntaje=0-100 cumplimiento, puntaje_total=suma(peso*puntaje/100)):
{{"nombre":"<str>","email":"<str>","telefono":"<str>","puntaje_total":<0-100>,"criterios":[{{"criterio":"<str>","peso":<0-100>,"puntaje":<0-100>,"cumple":"<si|parcial|no>","descripcion":"<breve>"}}],"resumen":"<APTO/NO APTO: razon>"}}"""


def _params_modelo(modelo: str) -> dict:
    if modelo in MODELO_PARAMS:
        return MODELO_PARAMS[modelo]
    for key, val in MODELO_PARAMS.items():
        if modelo.startswith(key.split(":")[0]):
            return val
    return {"num_predict": 2000, "num_ctx": 4096, "verboso": True}


def _get_opciones(max_ctx: int = 4096) -> dict:
    total_logicos = os.cpu_count() or 4
    # Threads optimos por defecto: todos los hilos logicos menos 2 para el SO
    optimo_default = max(total_logicos - 2, 2)
    try:
        from app.api.config import leer_config
        cfg = leer_config()
        dispositivo = cfg.get("dispositivo", "cpu")
        # Usar el valor del config pero nunca menos que el optimo del hardware real
        threads = max(cfg.get("num_threads", optimo_default), optimo_default)
        if dispositivo == "gpu":
            return {"temperature": 0, "seed": 42, "num_gpu": 999,
                    "num_ctx": max_ctx, "keep_alive": -1}
        else:
            return {"temperature": 0, "seed": 42, "num_gpu": 0,
                    "num_thread": threads, "num_ctx": max_ctx,
                    "keep_alive": -1, "mmap": True, "f16_kv": False}
    except Exception:
        return {"temperature": 0, "seed": 42, "num_gpu": 0,
                "num_thread": optimo_default,
                "num_ctx": max_ctx, "keep_alive": -1, "mmap": True}


def analizar_cv_completo(nombre_puesto: str, requisitos: str, texto_cv: str) -> dict:
    if not texto_cv or len(texto_cv.strip()) < 50:
        raise ValueError("CV sin texto suficiente para analizar.")

    texto = texto_cv.strip()
    if len(texto) > 2000:
        texto = texto[:1500] + "\n...\n" + texto[-500:]

    params = _params_modelo(settings.OLLAMA_MODEL)
    instruccion = _INST_CORTA if params["verboso"] else _INST_NORMAL

    prompt = PROMPT_COMPLETO.format(
        instruccion=instruccion,
        nombre_puesto=nombre_puesto,
        requisitos=requisitos,
        texto_cv=texto,
    )

    if settings.IA_PROVIDER == "ollama":
        return _llamar_ollama(prompt, nombre_puesto, requisitos, texto)
    elif settings.IA_PROVIDER == "openai":
        return _llamar_openai(prompt)
    else:
        raise ValueError("IA_PROVIDER invalido: '{}'".format(settings.IA_PROVIDER))


def _llamar_ollama(prompt: str, nombre_puesto: str = "", requisitos: str = "", texto_cv: str = "") -> dict:
    try:
        import ollama
    except ImportError:
        raise RuntimeError("Libreria 'ollama' no instalada.")

    nombre_lower = settings.OLLAMA_MODEL.lower()
    if "-base" in nombre_lower and "-instruct" not in nombre_lower:
        raise RuntimeError(
            "Modelo '{}' es BASE, no sigue instrucciones. Usa variante -instruct.".format(settings.OLLAMA_MODEL)
        )

    params     = _params_modelo(settings.OLLAMA_MODEL)
    max_tokens = params["num_predict"]
    max_ctx    = params["num_ctx"]

    prompt_tokens = len(prompt) // 3
    ctx = min(prompt_tokens + max_tokens + 256, max_ctx)

    opts = _get_opciones(max_ctx=ctx)
    opts["num_predict"] = max_tokens

    logger.info("  Ollama [%s]: ctx=%s gpu=%s threads=%s tokens=%s prompt_chars=%s",
                settings.OLLAMA_MODEL, ctx,
                opts.get("num_gpu", 0), opts.get("num_thread", "GPU"),
                max_tokens, len(prompt))

    # ── Intento 1: prompt completo ──────────────────────────────────────────
    try:
        r = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options=opts,
        )
        texto = r["message"]["content"].strip()

        if not texto:
            raise RuntimeError("Respuesta vacia — modelo posiblemente BASE.")

        logger.info("  Respuesta: %s chars", len(texto))
        return _parsear(texto)

    except (RuntimeError, ValueError) as e:
        # Si el error es de conexion/modelo, no reintentar
        msg = str(e).lower()
        if "ollama no responde" in msg or "no descargado" in msg or "base" in msg or "vacia" in msg:
            raise RuntimeError("Error Ollama: {}".format(e))
        logger.warning("  Intento 1 fallido (%s) — reintentando con prompt de rescate...", e)

    except Exception as e:
        msg = str(e).lower()
        if "connection" in msg or "refused" in msg:
            raise RuntimeError("Ollama no responde. Verifica que este corriendo.")
        if "not found" in msg or "pull" in msg:
            raise RuntimeError("Modelo '{}' no descargado.".format(settings.OLLAMA_MODEL))
        logger.warning("  Intento 1 fallido (%s) — reintentando con prompt de rescate...", e)

    # ── Intento 2: prompt minimo de rescate ──────────────────────────────────
    try:
        # Prompt mucho mas corto: menos tokens de entrada = mas tokens disponibles para salida
        req_cortos = requisitos[:300] if len(requisitos) > 300 else requisitos
        cv_corto   = texto_cv[:500]   if len(texto_cv)   > 500  else texto_cv

        prompt_rescate = PROMPT_RESCATE.format(
            nombre_puesto=nombre_puesto,
            requisitos_cortos=req_cortos,
            cv_corto=cv_corto,
        )

        ctx_rescate = min(len(prompt_rescate) // 3 + 1000 + 128, max_ctx)
        opts_rescate = _get_opciones(max_ctx=ctx_rescate)
        opts_rescate["num_predict"] = 1000  # suficiente para JSON minimo

        logger.info("  Rescate: ctx=%s tokens=1000 prompt_chars=%s", ctx_rescate, len(prompt_rescate))

        r2 = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt_rescate}],
            options=opts_rescate,
        )
        texto2 = r2["message"]["content"].strip()
        logger.info("  Rescate respuesta: %s chars", len(texto2))
        resultado = _parsear(texto2)
        resultado["_rescate"] = True  # marcar que fue el intento de rescate
        return resultado

    except Exception as e2:
        msg2 = str(e2).lower()
        if "connection" in msg2 or "refused" in msg2:
            raise RuntimeError("Ollama no responde. Verifica que este corriendo.")
        raise RuntimeError("Error Ollama (ambos intentos fallaron): {}".format(e2))


def _llamar_openai(prompt: str) -> dict:
    try:
        import openai
    except ImportError:
        raise RuntimeError("Libreria 'openai' no instalada.")
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no configurada.")
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    r = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1800,
        response_format={"type": "json_object"},
    )
    return _parsear(r.choices[0].message.content.strip())


def _reparar_json(texto: str) -> str:
    """
    Intenta reparar JSON invalido o truncado.
    Cubre: truncado al final, cadena sin cerrar, criterio incompleto.
    """
    reparado = texto.rstrip()
    if not reparado:
        return reparado

    # 1. Cerrar cadena abierta (numero impar de comillas en los ultimos 300 chars)
    zona = reparado[-300:] if len(reparado) > 300 else reparado
    # Contar comillas no escapadas
    comillas = len(re.findall(r'(?<!\\)"', zona))
    if comillas % 2 != 0:
        reparado += '"'

    # 2. Limpiar trailing incompleto
    reparado = reparado.rstrip().rstrip(',').rstrip(':').rstrip(',')

    # 3. Eliminar criterio incompleto (tiene "criterio" pero le faltan "cumple" o "puntaje")
    ultimo_criterio = reparado.rfind('"criterio"')
    if ultimo_criterio > 0:
        fragmento = reparado[ultimo_criterio:]
        if not all(k in fragmento for k in ('"cumple"', '"puntaje"')):
            inicio = reparado.rfind('{', 0, ultimo_criterio)
            if inicio > 0:
                reparado = reparado[:inicio].rstrip(',').rstrip()

    # 4. Cerrar estructuras abiertas
    faltan_c = max(0, reparado.count('[') - reparado.count(']'))
    faltan_l = max(0, reparado.count('{') - reparado.count('}'))
    reparado += ']' * faltan_c + '}' * faltan_l

    # 5. Inyectar "resumen" si falta despues de reparar
    try:
        parcial = json.loads(reparado)
        if "resumen" not in parcial:
            reparado = reparado.rstrip('}').rstrip() + ',"resumen":"Analisis completado."}'
    except Exception:
        pass

    return reparado


# Mapa de valores de "cumple" que el modelo puede devolver -> normalizados
_CUMPLE_MAP = {
    "si": "si", "sí": "si", "cumple": "si", "yes": "si", "true": "si", "1": "si",
    "no": "no", "no cumple": "no", "false": "no", "0": "no",
    "parcial": "parcial", "parcialmente": "parcial", "partial": "parcial",
    "cumple parcialmente": "parcial", "parcial cumple": "parcial",
}


def _normalizar_cumple(valor: str) -> str:
    v = str(valor).lower().strip()
    return _CUMPLE_MAP.get(v, "no")


def _parsear(texto: str) -> dict:
    texto = re.sub(r"```(?:json)?\s*", "", texto).strip().rstrip("`").strip()
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        texto = match.group(0)

    try:
        data = json.loads(texto)
    except json.JSONDecodeError as e:
        logger.warning("JSON invalido (%s) - intentando reparar...", e)
        try:
            texto_reparado = _reparar_json(texto)
            data = json.loads(texto_reparado)
            logger.info("JSON reparado exitosamente")
        except json.JSONDecodeError as e2:
            logger.error("JSON no reparable: %s | Texto: %s", e2, texto[:300])
            raise ValueError("La IA no devolvio JSON valido: {}".format(e))

    if "puntaje_total" not in data:
        raise ValueError("Falta puntaje_total en la respuesta.")
    if "criterios" not in data or not isinstance(data["criterios"], list):
        raise ValueError("Falta criterios como lista.")
    if "resumen" not in data:
        data["resumen"] = "Sin resumen disponible."

    data["puntaje_total"] = max(0.0, min(100.0, float(data["puntaje_total"])))
    for c in data["criterios"]:
        c["puntaje"] = max(0.0, min(100.0, float(c.get("puntaje", 0))))
        c["cumple"]  = _normalizar_cumple(c.get("cumple", "no"))

    for campo in ("nombre", "email", "telefono"):
        v = data.get(campo)
        if not v or str(v).lower() in ("null", "none", "n/a", "no encontrado", ""):
            data[campo] = None
        else:
            data[campo] = str(v).strip()

    return data


async def verificar_ollama() -> dict:
    try:
        import ollama
        models  = ollama.list()
        nombres = [m["name"] for m in models.get("models", [])]
        base    = settings.OLLAMA_MODEL.split(":")[0]
        ok      = any(base in n for n in nombres)
        return {
            "ollama_disponible":  True,
            "modelo_disponible":  ok,
            "modelo_requerido":   settings.OLLAMA_MODEL,
            "modelos_instalados": nombres,
        }
    except Exception as e:
        return {
            "ollama_disponible":  False,
            "modelo_disponible":  False,
            "modelo_requerido":   settings.OLLAMA_MODEL,
            "error": str(e),
        }
