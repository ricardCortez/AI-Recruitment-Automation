"""
Motor de IA — completamente SÍNCRONO.
ollama.chat() es bloqueante — no necesita async/await.
Esto evita conflictos de event loop en background tasks.
"""

import json
import re
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

PROMPT_ANALISIS = """Sos un experto en Recursos Humanos. Evaluá este CV contra los requisitos del puesto.

PUESTO: {nombre_puesto}

REQUISITOS:
{requisitos}

CV:
{texto_cv}

Respondé SOLO con este JSON, sin texto adicional ni bloques de código:
{{
  "puntaje_total": <número 0-100>,
  "criterios": [
    {{
      "criterio": "<requisito evaluado>",
      "cumple": "<si | parcial | no>",
      "descripcion": "<1-2 oraciones con evidencia del CV>",
      "puntaje": <número 0-100>
    }}
  ],
  "resumen": "<3-4 oraciones: fortalezas, brechas y recomendación>"
}}

Evaluá CADA requisito. Sé objetivo y basate solo en lo que dice el CV."""

PROMPT_DATOS = """Del siguiente texto de CV extraé los datos de contacto.
Respondé SOLO con este JSON, sin texto adicional:
{{
  "nombre": "<nombre completo o null>",
  "email": "<email o null>",
  "telefono": "<teléfono o null>"
}}

CV:
{texto}"""


def _get_ollama_options() -> dict:
    """Lee la config guardada para GPU/CPU/threads."""
    try:
        from app.api.config import leer_config
        cfg = leer_config()
        return {
            "temperature": 0,
            "seed":        42,
            "num_gpu":     999 if cfg.get("dispositivo") == "gpu" else 0,
            "num_thread":  cfg.get("num_threads", 4),
            "num_ctx":     8192,
        }
    except Exception:
        return {"temperature": 0, "seed": 42, "num_gpu": 0, "num_thread": 4}


def analizar_cv(nombre_puesto: str, requisitos: str, texto_cv: str) -> dict:
    """Analiza un CV contra los requisitos. SÍNCRONO."""
    if not texto_cv or len(texto_cv.strip()) < 50:
        raise ValueError("CV sin texto suficiente para analizar.")

    prompt = PROMPT_ANALISIS.format(
        nombre_puesto=nombre_puesto,
        requisitos=requisitos,
        texto_cv=texto_cv[:7000],
    )

    if settings.IA_PROVIDER == "ollama":
        return _ollama(prompt, max_tokens=2500)
    elif settings.IA_PROVIDER == "openai":
        return _openai(prompt)
    else:
        raise ValueError(f"IA_PROVIDER inválido: '{settings.IA_PROVIDER}'")


def extraer_datos_cv(texto_cv: str) -> dict:
    """Extrae nombre, email y teléfono del CV con IA. SÍNCRONO."""
    prompt = PROMPT_DATOS.format(texto=texto_cv[:2000])
    try:
        if settings.IA_PROVIDER == "ollama":
            opts = _get_ollama_options()
            opts["num_predict"] = 150
            opts.pop("num_ctx", None)
            import ollama
            r = ollama.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options=opts,
            )
            data = _parsear_json(r["message"]["content"].strip())
        else:
            import openai
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            r = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            data = _parsear_json(r.choices[0].message.content.strip())

        return {
            "nombre":   _limpiar(data.get("nombre")),
            "email":    _limpiar(data.get("email")),
            "telefono": _limpiar(data.get("telefono")),
        }
    except Exception as e:
        logger.warning(f"No se pudo extraer datos con IA: {e}")
        return {"nombre": None, "email": None, "telefono": None}


def _ollama(prompt: str, max_tokens: int = 2500) -> dict:
    try:
        import ollama
    except ImportError:
        raise RuntimeError("Librería 'ollama' no instalada. Ejecutá: pip install ollama")

    opts = _get_ollama_options()
    opts["num_predict"] = max_tokens

    try:
        r = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options=opts,
        )
        return _parsear_json(r["message"]["content"].strip())
    except Exception as e:
        msg = str(e).lower()
        if "connection" in msg or "refused" in msg:
            raise RuntimeError("Ollama no responde. Verificá que esté corriendo.")
        if "not found" in msg or "pull" in msg:
            raise RuntimeError(f"Modelo '{settings.OLLAMA_MODEL}' no descargado.")
        raise RuntimeError(f"Error Ollama: {e}")


def _openai(prompt: str) -> dict:
    try:
        import openai
    except ImportError:
        raise RuntimeError("Librería 'openai' no instalada.")
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no configurada.")
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    r = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return _parsear_json(r.choices[0].message.content.strip())


def _parsear_json(texto: str) -> dict:
    texto = re.sub(r"```(?:json)?\s*", "", texto).strip().rstrip("`").strip()
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        texto = match.group(0)
    try:
        data = json.loads(texto)
    except json.JSONDecodeError as e:
        logger.error(f"JSON inválido:\n{texto[:400]}")
        raise ValueError(f"La IA no devolvió JSON válido: {e}")

    if "puntaje_total" in data:
        data["puntaje_total"] = max(0.0, min(100.0, float(data["puntaje_total"])))
        if "criterios" not in data or not isinstance(data["criterios"], list):
            raise ValueError("Falta 'criterios' como lista.")
        if "resumen" not in data:
            data["resumen"] = "Sin resumen disponible."
        for c in data["criterios"]:
            c["puntaje"] = max(0.0, min(100.0, float(c.get("puntaje", 0))))
            c["cumple"] = c.get("cumple", "no").lower().strip()
            if c["cumple"] not in ("si", "parcial", "no"):
                c["cumple"] = "no"
    return data


def _limpiar(v) -> str | None:
    if not v or str(v).lower() in ("null", "none", "n/a", "no encontrado", ""):
        return None
    return str(v).strip()


async def verificar_ollama() -> dict:
    """Verifica Ollama (sigue siendo async para el endpoint FastAPI)."""
    try:
        import ollama
        models = ollama.list()
        nombres = [m["name"] for m in models.get("models", [])]
        base = settings.OLLAMA_MODEL.split(":")[0]
        modelo_ok = any(base in n for n in nombres)
        return {
            "ollama_disponible": True,
            "modelo_disponible": modelo_ok,
            "modelo_requerido":  settings.OLLAMA_MODEL,
            "modelos_instalados": nombres,
        }
    except Exception as e:
        return {
            "ollama_disponible": False,
            "modelo_disponible": False,
            "modelo_requerido":  settings.OLLAMA_MODEL,
            "error": str(e),
        }
