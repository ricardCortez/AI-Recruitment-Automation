"""
Abstracción del motor de IA.
Soporta Ollama (local) y OpenAI según la variable IA_PROVIDER del .env.
"""

import json
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

PROMPT_TEMPLATE = """
Sos un experto en Recursos Humanos. Analizá el siguiente CV y evalualo contra los requisitos del puesto.

=== REQUISITOS DEL PUESTO: {nombre_puesto} ===
{requisitos}

=== CV DEL CANDIDATO ===
{texto_cv}

=== INSTRUCCIONES ===
Respondé ÚNICAMENTE con un objeto JSON válido con esta estructura exacta:
{{
  "puntaje_total": <número del 0 al 100>,
  "criterios": [
    {{
      "criterio": "<nombre del requisito>",
      "cumple": "<si | parcial | no>",
      "descripcion": "<explicación breve de 1-2 oraciones>",
      "puntaje": <número del 0 al 100>
    }}
  ],
  "resumen": "<resumen ejecutivo de 3-4 oraciones: fortalezas, brechas y recomendación>"
}}

Evaluá cada requisito mencionado. El puntaje_total es el promedio ponderado de todos los criterios.
No agregues texto fuera del JSON.
""".strip()


async def analizar_cv(nombre_puesto: str, requisitos: str, texto_cv: str) -> dict:
    """
    Envía el CV a la IA y devuelve el resultado parseado.
    Retorna dict con claves: puntaje_total, criterios, resumen.
    """
    prompt = PROMPT_TEMPLATE.format(
        nombre_puesto=nombre_puesto,
        requisitos=requisitos,
        texto_cv=texto_cv[:6000],  # Limitar para no exceder contexto
    )

    if settings.IA_PROVIDER == "ollama":
        return await _analizar_ollama(prompt)
    elif settings.IA_PROVIDER == "openai":
        return await _analizar_openai(prompt)
    else:
        raise ValueError(f"IA_PROVIDER inválido: {settings.IA_PROVIDER}")


async def _analizar_ollama(prompt: str) -> dict:
    import ollama
    try:
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        texto = response["message"]["content"].strip()
        return _parsear_respuesta(texto)
    except Exception as e:
        logger.error(f"Error Ollama: {e}")
        raise


async def _analizar_openai(prompt: str) -> dict:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        texto = response.choices[0].message.content.strip()
        return _parsear_respuesta(texto)
    except Exception as e:
        logger.error(f"Error OpenAI: {e}")
        raise


def _parsear_respuesta(texto: str) -> dict:
    """Parsea la respuesta JSON de la IA. Intenta limpiar si viene con markdown."""
    # Limpiar bloques de código markdown si los hay
    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]

    try:
        data = json.loads(texto.strip())
        # Validar estructura mínima
        assert "puntaje_total" in data
        assert "criterios" in data
        assert "resumen" in data
        return data
    except Exception as e:
        logger.error(f"Error parseando respuesta IA: {e}\nTexto: {texto[:300]}")
        raise ValueError("La IA no devolvió un JSON válido.")


async def verificar_ollama_disponible() -> bool:
    """Verifica si Ollama está corriendo y tiene el modelo cargado."""
    try:
        import ollama
        models = ollama.list()
        nombres = [m["name"] for m in models.get("models", [])]
        return any(settings.OLLAMA_MODEL in n for n in nombres)
    except Exception:
        return False
