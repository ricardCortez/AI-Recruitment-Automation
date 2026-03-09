# -*- coding: utf-8 -*-
"""
Motor de IA optimizado.
- Tokens y contexto dinamicos segun modelo seleccionado
- _reparar_json: cierra JSON truncado por limite de tokens
- keep_alive=-1, mmap/f16_kv para CPU
"""

import json
import re
import os
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Parametros optimos por modelo
# num_predict: cuantos tokens puede generar para el JSON completo
# num_ctx: contexto maximo (prompt + respuesta)
# verbosidad: cuanto escribe el modelo (ajusta el prompt)
MODELO_PARAMS = {
    "llama3.1:8b":                  {"num_predict": 1200, "num_ctx": 4096, "verboso": False},
    "qwen2.5:7b":                   {"num_predict": 1800, "num_ctx": 4096, "verboso": True},
    "qwen2.5:14b":                  {"num_predict": 1200, "num_ctx": 4096, "verboso": False},
    "qwen2.5:32b":                  {"num_predict": 1200, "num_ctx": 4096, "verboso": False},
}

# Instruccion adicional para modelos verbosos
_INSTRUCCION_CORTA = " Descripciones MUY CORTAS (max 8 palabras cada una)."
_INSTRUCCION_NORMAL = " Descripciones concisas (max 15 palabras cada una)."

PROMPT_COMPLETO = """Experto RRHH. Evalua el CV para el puesto indicado.{instruccion}
Responde SOLO JSON, sin texto extra ni markdown.

PUESTO: {nombre_puesto}
REQUISITOS:
{requisitos}

CV:
{texto_cv}

RUBRICA: 90-100=supera | 70-89=cumple | 50-69=parcial | 25-49=brecha | 0-24=no cumple

JSON:
{{"nombre":"<str|null>","email":"<str|null>","telefono":"<str|null>","puntaje_total":<int>,"criterios":[{{"criterio":"<str>","cumple":"<si|parcial|no>","descripcion":"<breve>","puntaje":<int>}}],"resumen":"<Fortalezas: X. Brechas: Y.>"}}"""


def _params_modelo(modelo: str) -> dict:
    """Devuelve num_predict y num_ctx optimos para el modelo activo."""
    base = modelo.split(":")[0] + ":" + modelo.split(":")[1] if ":" in modelo else modelo
    # Buscar coincidencia exacta primero, luego por prefijo
    if modelo in MODELO_PARAMS:
        return MODELO_PARAMS[modelo]
    for key, val in MODELO_PARAMS.items():
        if modelo.startswith(key.split(":")[0]):
            return val
    # Default seguro
    return {"num_predict": 1500, "num_ctx": 4096, "verboso": True}


def _get_opciones(max_ctx: int = 4096) -> dict:
    total_cores = os.cpu_count() or 4
    try:
        from app.api.config import leer_config
        cfg = leer_config()
        dispositivo = cfg.get("dispositivo", "cpu")
        threads_cfg = cfg.get("num_threads", max(total_cores - 2, 2))
        threads = min(threads_cfg, max(total_cores - 2, 2))

        if dispositivo == "gpu":
            return {
                "temperature": 0,
                "seed":        42,
                "num_gpu":     999,
                "num_ctx":     max_ctx,
                "keep_alive":  -1,
            }
        else:
            return {
                "temperature": 0,
                "seed":        42,
                "num_gpu":     0,
                "num_thread":  threads,
                "num_ctx":     max_ctx,
                "keep_alive":  -1,
                "mmap":        True,
                "f16_kv":      False,
            }
    except Exception:
        return {
            "temperature": 0,
            "seed":        42,
            "num_gpu":     0,
            "num_thread":  max(total_cores - 2, 2),
            "num_ctx":     max_ctx,
            "keep_alive":  -1,
            "mmap":        True,
        }


def analizar_cv_completo(nombre_puesto: str, requisitos: str, texto_cv: str) -> dict:
    if not texto_cv or len(texto_cv.strip()) < 50:
        raise ValueError("CV sin texto suficiente para analizar.")

    texto = texto_cv.strip()
    if len(texto) > 2000:
        texto = texto[:1500] + "\n...\n" + texto[-500:]

    # Ajustar instruccion segun verbosidad del modelo
    params = _params_modelo(settings.OLLAMA_MODEL)
    instruccion = _INSTRUCCION_CORTA if params["verboso"] else _INSTRUCCION_NORMAL

    prompt = PROMPT_COMPLETO.format(
        instruccion=instruccion,
        nombre_puesto=nombre_puesto,
        requisitos=requisitos,
        texto_cv=texto,
    )

    if settings.IA_PROVIDER == "ollama":
        return _llamar_ollama(prompt)
    elif settings.IA_PROVIDER == "openai":
        return _llamar_openai(prompt)
    else:
        raise ValueError("IA_PROVIDER invalido: '{}'".format(settings.IA_PROVIDER))


def _llamar_ollama(prompt: str) -> dict:
    try:
        import ollama
    except ImportError:
        raise RuntimeError("Libreria 'ollama' no instalada.")

    params = _params_modelo(settings.OLLAMA_MODEL)
    max_tokens = params["num_predict"]
    max_ctx    = params["num_ctx"]

    prompt_tokens = len(prompt) // 3
    ctx = min(prompt_tokens + max_tokens + 256, max_ctx)

    opts = _get_opciones(max_ctx=ctx)
    opts["num_predict"] = max_tokens

    # Detectar modelo base (no instruct) — no siguen instrucciones via chat
    nombre_lower = settings.OLLAMA_MODEL.lower()
    if "-base" in nombre_lower and "-instruct" not in nombre_lower:
        raise RuntimeError(
            "El modelo '{}' es un modelo BASE y no sigue instrucciones. "
            "Usa la variante '-instruct' (ej: qwen2.5-coder:14b-instruct-q3_K_M).".format(settings.OLLAMA_MODEL)
        )

    logger.info("  Ollama [%s]: ctx=%s gpu=%s threads=%s tokens=%s prompt_chars=%s",
                settings.OLLAMA_MODEL, ctx,
                opts.get("num_gpu", 0), opts.get("num_thread", "GPU"),
                max_tokens, len(prompt))

    try:
        r = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options=opts,
        )
        texto = r["message"]["content"].strip()
        # Respuesta vacia = modelo no siguio instrucciones (posible base model sin detectar)
        if not texto:
            raise RuntimeError(
                "El modelo devolvio respuesta vacia. Verificá que sea una variante '-instruct', "
                "no '-base'. Modelo actual: '{}'.".format(settings.OLLAMA_MODEL)
            )
        logger.info("  Respuesta: %s chars", len(texto))
        return _parsear(texto)
    except Exception as e:
        msg = str(e).lower()
        if "connection" in msg or "refused" in msg:
            raise RuntimeError("Ollama no responde. Verifica que este corriendo.")
        if "not found" in msg or "pull" in msg:
            raise RuntimeError("Modelo '{}' no descargado.".format(settings.OLLAMA_MODEL))
        raise RuntimeError("Error Ollama: {}".format(e))


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
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    return _parsear(r.choices[0].message.content.strip())


def _reparar_json(texto: str) -> str:
    """Cierra JSON truncado por limite de tokens."""
    reparado = texto.rstrip()

    zona_final = reparado[-200:] if len(reparado) > 200 else reparado
    if zona_final.count('"') % 2 != 0:
        reparado += '"'

    reparado = reparado.rstrip().rstrip(',').rstrip(':').rstrip(',')

    ultimo_criterio = reparado.rfind('"criterio"')
    if ultimo_criterio > 0:
        fragmento = reparado[ultimo_criterio:]
        if not all(k in fragmento for k in ('"cumple"', '"puntaje"')):
            inicio = reparado.rfind('{', 0, ultimo_criterio)
            if inicio > 0:
                reparado = reparado[:inicio].rstrip(',').rstrip()

    faltan_c = reparado.count('[') - reparado.count(']')
    faltan_l = reparado.count('{') - reparado.count('}')
    for _ in range(max(0, faltan_c)):
        reparado += ']'
    for _ in range(max(0, faltan_l)):
        reparado += '}'

    try:
        parcial = json.loads(reparado)
        if "resumen" not in parcial:
            reparado = reparado.rstrip('}').rstrip()
            reparado += ',"resumen":"Analisis completado."}'
    except Exception:
        pass

    return reparado


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
        c["cumple"]  = c.get("cumple", "no").lower().strip()
        if c["cumple"] not in ("si", "parcial", "no"):
            c["cumple"] = "no"

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
