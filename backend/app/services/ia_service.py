"""
Motor de IA — Ollama + OpenAI.
- qwen2.5:14b como modelo principal
- Extracción de datos del CV en llamada separada y liviana
- temperature=0 + seed fijo para consistencia
"""

import json
import re
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Prompts ───────────────────────────────────────────────────────────────────

PROMPT_EXTRAER_DATOS = """Analizá este texto de CV y extraé los datos de contacto de la persona.
Respondé SOLO con este JSON, sin texto adicional:
{{
  "nombre": "<nombre completo de la persona, o null si no se encuentra>",
  "email": "<email, o null>",
  "telefono": "<teléfono con código de país si está, o null>"
}}

Texto del CV:
{texto}"""

PROMPT_ANALISIS = """Sos un experto en Recursos Humanos. Evaluá este CV contra los requisitos del puesto de manera objetiva y consistente.

PUESTO: {nombre_puesto}

REQUISITOS:
{requisitos}

CV DEL CANDIDATO:
{texto_cv}

Respondé SOLO con este JSON exacto, sin texto adicional ni bloques de código:
{{
  "puntaje_total": <número 0-100, promedio ponderado de criterios>,
  "criterios": [
    {{
      "criterio": "<nombre exacto del requisito evaluado>",
      "cumple": "<si | parcial | no>",
      "descripcion": "<explicación objetiva de 1-2 oraciones con evidencia del CV>",
      "puntaje": <número 0-100>
    }}
  ],
  "resumen": "<3-4 oraciones: fortalezas principales, brechas detectadas y recomendación final>"
}}

Reglas:
- Evaluá CADA requisito listado por separado
- Basate SOLO en lo que dice el CV, no asumas experiencia no mencionada
- "si" = cumple claramente, "parcial" = cumple en parte, "no" = no hay evidencia
- El puntaje_total es el promedio de todos los criterios"""


# ── Función principal de análisis ─────────────────────────────────────────────

async def analizar_cv(nombre_puesto: str, requisitos: str, texto_cv: str) -> dict:
    if not texto_cv or len(texto_cv.strip()) < 50:
        raise ValueError("CV sin texto suficiente para analizar.")

    prompt = PROMPT_ANALISIS.format(
        nombre_puesto=nombre_puesto,
        requisitos=requisitos,
        texto_cv=texto_cv[:7000],
    )

    if settings.IA_PROVIDER == "ollama":
        return await _llamar_ollama(prompt, max_tokens=2500)
    elif settings.IA_PROVIDER == "openai":
        return await _llamar_openai(prompt)
    else:
        raise ValueError(f"IA_PROVIDER inválido: '{settings.IA_PROVIDER}'")


# ── Extracción de datos del CV (llamada liviana) ──────────────────────────────

async def extraer_datos_cv(texto_cv: str) -> dict:
    """
    Usa la IA para extraer nombre, email y teléfono del CV.
    Mucho más preciso que heurísticas de texto.
    Retorna dict con claves: nombre, email, telefono (pueden ser None).
    """
    prompt = PROMPT_EXTRAER_DATOS.format(texto=texto_cv[:2000])

    try:
        if settings.IA_PROVIDER == "ollama":
            import ollama
            r = ollama.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0, "seed": 42, "num_predict": 150},
            )
            texto = r["message"]["content"].strip()
        else:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            r = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            texto = r.choices[0].message.content.strip()

        data = _parsear_json(texto)
        return {
            "nombre":   _limpiar_string(data.get("nombre")),
            "email":    _limpiar_string(data.get("email")),
            "telefono": _limpiar_string(data.get("telefono")),
        }

    except Exception as e:
        logger.warning(f"No se pudieron extraer datos del CV con IA: {e}")
        return {"nombre": None, "email": None, "telefono": None}


def _limpiar_string(valor) -> str | None:
    if not valor or str(valor).lower() in ("null", "none", "n/a", "no encontrado", ""):
        return None
    return str(valor).strip()


# ── Llamadas a modelos ────────────────────────────────────────────────────────

async def _llamar_ollama(prompt: str, max_tokens: int = 2500) -> dict:
    try:
        import ollama
    except ImportError:
        raise RuntimeError("Librería 'ollama' no instalada. Ejecutá: pip install ollama")

    try:
        # Leer config de GPU/CPU guardada
        from app.api.config import leer_config
        cfg = leer_config()

        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": cfg.get("temperature", 0),
                "seed":        cfg.get("seed", 42),
                "num_predict": max_tokens,
                "num_ctx":     8192,
                # num_gpu: 0=CPU, 999=todas las capas en GPU (Ollama no acepta -1)
                "num_gpu":    999 if cfg.get("dispositivo") == "gpu" else 0,
                "num_thread": cfg.get("num_threads", 4),
            },
        )
        texto = response["message"]["content"].strip()
        return _parsear_json(texto)

    except Exception as e:
        msg = str(e).lower()
        if "connection" in msg or "refused" in msg or "connect" in msg:
            raise RuntimeError("Ollama no responde. Verificá que esté corriendo.")
        if "model" in msg and ("not found" in msg or "pull" in msg):
            raise RuntimeError(
                f"Modelo '{settings.OLLAMA_MODEL}' no descargado. "
                f"Ejecutá: ollama pull {settings.OLLAMA_MODEL}"
            )
        raise RuntimeError(f"Error Ollama: {e}")


async def _llamar_openai(prompt: str) -> dict:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise RuntimeError("Librería 'openai' no instalada.")

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no configurada en .env")

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    r = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return _parsear_json(r.choices[0].message.content.strip())


# ── Parser JSON ───────────────────────────────────────────────────────────────

def _parsear_json(texto: str) -> dict:
    texto = re.sub(r"```(?:json)?\s*", "", texto).strip().rstrip("`").strip()
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        texto = match.group(0)

    try:
        data = json.loads(texto)
    except json.JSONDecodeError as e:
        logger.error(f"JSON inválido de la IA:\n{texto[:400]}")
        raise ValueError(f"La IA no devolvió JSON válido: {e}")

    # Validar solo si es respuesta de análisis completo
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


# ── Verificar estado de Ollama ────────────────────────────────────────────────

async def verificar_ollama() -> dict:
    try:
        import ollama
        models = ollama.list()
        nombres = [m["name"] for m in models.get("models", [])]
        modelo_base = settings.OLLAMA_MODEL.split(":")[0]
        modelo_ok = any(modelo_base in n for n in nombres)
        return {
            "ollama_disponible": True,
            "modelo_disponible": modelo_ok,
            "modelo_requerido": settings.OLLAMA_MODEL,
            "modelos_instalados": nombres,
        }
    except Exception as e:
        return {
            "ollama_disponible": False,
            "modelo_disponible": False,
            "modelo_requerido": settings.OLLAMA_MODEL,
            "error": str(e),
        }
