"""
Motor de IA - SINCRONO, optimizado para velocidad.
Tiempos medidos: ~3m30s por CV con qwen2.5:14b en CPU.
Objetivo con optimizaciones: ~2m20s por CV (-35%).
"""

import json
import re
import os
import threading
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Prompt con rubrica clara para evitar puntajes consecutivos
PROMPT_COMPLETO = """Experto en RRHH. Evaluá este CV con criterio objetivo e independiente.

PUESTO: {nombre_puesto}
REQUISITOS:
{requisitos}

CV:
{texto_cv}

RUBRICA DE PUNTAJE POR CRITERIO:
- 90-100: Cumple ampliamente, supera lo solicitado
- 70-89:  Cumple el requisito claramente
- 50-69:  Cumple parcialmente, hay brechas menores
- 25-49:  Cumple muy poco, brechas importantes
- 0-24:   No cumple o no hay evidencia

IMPORTANTE: Cada criterio es INDEPENDIENTE. No ordenes los puntajes.
Asigná el puntaje que corresponda a la evidencia, no al ranking del candidato.

JSON de respuesta (sin texto adicional):
{{"nombre":"<nombre completo o null>","email":"<email o null>","telefono":"<telefono o null>","puntaje_total":<promedio ponderado 0-100>,"criterios":[{{"criterio":"<requisito exacto>","cumple":"<si|parcial|no>","descripcion":"<evidencia concreta del CV>","puntaje":<0-100 segun rubrica>}}],"resumen":"<3 oraciones: fortalezas concretas, brechas detectadas, recomendacion final>"}}"""


def _get_opciones(max_ctx: int = 3072) -> dict:
    total_cores = os.cpu_count() or 4
    try:
        from app.api.config import leer_config
        cfg = leer_config()
        dispositivo = cfg.get("dispositivo", "cpu")
        threads_cfg = cfg.get("num_threads", total_cores)
        # Dejar 2 cores libres para el sistema
        threads = min(threads_cfg, max(total_cores - 2, 2))
        return {
            "temperature": 0,
            "seed":        42,
            "num_gpu":     999 if dispositivo == "gpu" else 0,
            "num_thread":  threads,
            "num_ctx":     max_ctx,
        }
    except Exception:
        return {
            "temperature": 0,
            "seed":        42,
            "num_gpu":     0,
            "num_thread":  max(total_cores - 2, 2),
            "num_ctx":     max_ctx,
        }


def analizar_cv_completo(nombre_puesto: str, requisitos: str, texto_cv: str) -> dict:
    """
    Una sola llamada a Ollama: extrae datos del candidato + analiza el CV.
    Sin timeout — el analisis puede tardar lo que necesite.
    """
    if not texto_cv or len(texto_cv.strip()) < 50:
        raise ValueError("CV sin texto suficiente para analizar.")

    # 3000 chars captura toda la info relevante de un CV (experiencia, educacion, skills)
    # Reducir de 4000 a 3000 = ~25% menos tokens de entrada
    prompt = PROMPT_COMPLETO.format(
        nombre_puesto=nombre_puesto,
        requisitos=requisitos,
        texto_cv=texto_cv[:3000],
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
        raise RuntimeError("Libreria 'ollama' no instalada. Ejecuta: pip install ollama")

    # Calcular contexto minimo necesario (no desperdiciar memoria)
    prompt_tokens = len(prompt) // 3
    max_tokens    = 1200  # Suficiente para el JSON completo con todos los criterios
    ctx           = min(prompt_tokens + max_tokens + 256, 3072)

    opts = _get_opciones(max_ctx=ctx)
    opts["num_predict"] = max_tokens

    logger.info("  Ollama: modelo=%s ctx=%s gpu=%s threads=%s max_tokens=%s",
                settings.OLLAMA_MODEL, ctx, opts["num_gpu"], opts["num_thread"], max_tokens)

    # Sin timeout — esperamos lo que sea necesario
    # El analisis manual de un CV toma 15-30 min; 2-4 min de IA es siempre mejor
    try:
        r = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options=opts,
        )
        texto = r["message"]["content"].strip()
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
        response_format={"type": "json_object"},
    )
    return _parsear(r.choices[0].message.content.strip())


def _parsear(texto: str) -> dict:
    texto = re.sub(r"```(?:json)?\s*", "", texto).strip().rstrip("`").strip()
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        texto = match.group(0)
    try:
        data = json.loads(texto)
    except json.JSONDecodeError as e:
        logger.error("JSON invalido: %s | Texto: %s", e, texto[:300])
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
