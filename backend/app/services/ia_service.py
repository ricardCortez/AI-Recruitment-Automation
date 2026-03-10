# -*- coding: utf-8 -*-
"""
Motor de IA — v5
- Valoracion de excedente: candidatos que superan lo requerido obtienen puntajes 90-100
- Descripcion explicita del excedente en cada criterio
- Resumen con "VALOR AGREGADO" cuando el candidato supera requisitos
- Tokens y retry sin cambios respecto a v4
"""

import json
import re
import os
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

MODELO_PARAMS = {
    "llama3.1:8b":  {"num_predict": 1400, "num_ctx": 4096, "verboso": False},
    "qwen2.5:7b":   {"num_predict": 2500, "num_ctx": 4096, "verboso": True},
    "qwen2.5:14b":  {"num_predict": 1400, "num_ctx": 4096, "verboso": False},
    "qwen2.5:32b":  {"num_predict": 1400, "num_ctx": 4096, "verboso": False},
}

_INST_CORTA  = " Descripciones MUY CORTAS: max 8 palabras por criterio."
_INST_NORMAL = " Descripciones concisas: max 14 palabras por criterio."

PROMPT_COMPLETO = """Eres un evaluador experto en RRHH. Tu tarea es evaluar con MAXIMA PRECISION el CV vs los requisitos del puesto.{instruccion}
Responde SOLO JSON valido, sin markdown ni texto extra.

PUESTO: {nombre_puesto}
REQUISITOS EXACTOS DEL PUESTO:
{requisitos}

CV DEL CANDIDATO:
{texto_cv}

═══════════════════════════════════════════════════════════════
PRINCIPIO FUNDAMENTAL — LEE ESTO ANTES DE EVALUAR:
Un candidato que tiene MAS de lo requerido es MAS VALIOSO que uno
que solo cumple exactamente. Tener experiencia adicional, certificaciones
extra, habilidades adicionales relevantes o conocimientos que van mas alla
de lo pedido AUMENTA el puntaje. No penalices el excedente: premialo.
═══════════════════════════════════════════════════════════════

ESCALA DE PUNTAJE 0-100 (aplica criterio por criterio):

  100    = EXCEDE MUY AMPLIAMENTE: tiene el doble o mas de lo pedido.
           Ej: piden 3 anos → tiene 10+; piden 1 idioma → tiene 3; piden 1 cert → tiene 4+
  90-99  = EXCEDE NOTABLEMENTE: tiene significativamente mas de lo requerido.
           Ej: piden 3 anos → tiene 6-9; piden intermedio → tiene avanzado certificado
  80-89  = SUPERA LO REQUERIDO: cumple todo y tiene algo extra relevante.
           Ej: piden 3 anos → tiene 4-5; pide tecnico → tiene licenciatura + experiencia
  70-79  = CUMPLE EXACTAMENTE: satisface los requisitos del criterio sin excedente notable.
  55-69  = CUMPLE PARCIALMENTE: cumple los puntos principales pero falta algo secundario.
  35-54  = CUMPLE A MEDIAS: brechas importantes, cumple menos de la mitad.
  10-34  = CUMPLE POCO: tiene algo relacionado pero hay brechas criticas.
   0-9   = NO CUMPLE: no tiene lo que se pide o es completamente irrelevante.

REGLAS CRITICAS:
1. Si el candidato tiene MAS anos de experiencia que los requeridos → puntaje MAYOR que 70.
   Formula orientativa: puntaje_experiencia = min(100, 70 + (anos_extra / anos_requeridos) * 30)
2. Si el candidato tiene certificaciones o titulos ADICIONALES relevantes al puesto → sube el puntaje del criterio correspondiente.
3. Si domina herramientas/tecnologias ADICIONALES a las pedidas y son utiles para el puesto → sube el puntaje.
4. Si el nivel de idioma SUPERA lo requerido (ej: pide B2, tiene C1/nativo) → puntaje 90+.
5. El excedente debe mencionarse SIEMPRE en la descripcion del criterio.
6. No todas las personas pueden tener puntaje similar: diferencia a los candidatos claramente.

INSTRUCCIONES PASO A PASO:

PASO 1 — Agrupa los requisitos en criterios principales (ej: Experiencia, Formacion Academica, Conocimientos Tecnicos, Idiomas, etc.).

PASO 2 — Asigna PESO a cada criterio segun su importancia para el puesto. Todos los pesos deben sumar exactamente 100.

PASO 3 — Para cada criterio:
  a) Lee LITERALMENTE lo que pide el requisito.
  b) Busca en el CV todo lo que el candidato tiene relacionado a ese criterio.
  c) Determina si cumple, cumple parcial, no cumple O si EXCEDE lo requerido.
  d) Asigna el puntaje usando la escala de arriba (premia el excedente).
  e) En descripcion: menciona lo hallado Y si supera el requisito, indica cuanto supera.
     Ejemplos de descripcion con excedente:
       "10 anos en TI vs 3 pedidos, jefatura en 2 empresas" 
       "Python+SQL+Spark, pide solo Python y SQL — extras valorables"
       "Ingles C2 nativo vs B2 requerido — supera ampliamente"
       "MBA + Licenciatura vs Licenciatura requerida"

PASO 4 — puntaje_total = suma exacta de (peso_i * puntaje_i / 100).
  VERIFICA el calculo antes de responder.

PASO 5 — cumple: "si" si puntaje>=70 | "parcial" si 40-69 | "no" si <40

PASO 6 — resumen: empieza con "APTO", "APTO CON RESERVAS" o "NO APTO".
  Menciona explicitamente si el candidato supera requisitos con la frase "VALOR AGREGADO:" seguida de que aporta extra.
  Ejemplo: "APTO — VALOR AGREGADO: 10 anos de exp (pide 3), certificaciones AWS adicionales, ingles nativo."

JSON exacto (sin texto antes ni despues):
{{"nombre":"<str|null>","email":"<str|null>","telefono":"<str|null>","puntaje_total":<0-100>,"criterios":[{{"criterio":"<str>","peso":<0-100>,"puntaje":<0-100>,"cumple":"<si|parcial|no>","descripcion":"<frase con excedente si aplica>"}}],"resumen":"<APTO/NO APTO: fortalezas, brechas y valor agregado>"}}"""


PROMPT_RESCATE = """Evalua este CV para el puesto. Responde SOLO con JSON valido. Sin texto extra.
IMPORTANTE: si el candidato tiene MAS de lo requerido en algun criterio, asigna puntaje > 70 (puede llegar a 100).

PUESTO: {nombre_puesto}
REQUISITOS: {requisitos_cortos}
CV (resumen): {cv_corto}

JSON (peso=importancia, puntaje=0-100 donde >70 significa supera requisito, puntaje_total=suma(peso*puntaje/100)):
{{"nombre":"<str>","email":"<str>","telefono":"<str>","puntaje_total":<0-100>,"criterios":[{{"criterio":"<str>","peso":<0-100>,"puntaje":<0-100>,"cumple":"<si|parcial|no>","descripcion":"<breve, indica si supera requisito>"}}],"resumen":"<APTO/NO APTO: razon y valor agregado si aplica>"}}"""


def _params_modelo(modelo: str) -> dict:
    if modelo in MODELO_PARAMS:
        return MODELO_PARAMS[modelo]
    for key, val in MODELO_PARAMS.items():
        if modelo.startswith(key.split(":")[0]):
            return val
    return {"num_predict": 2000, "num_ctx": 4096, "verboso": True}


def _get_opciones(max_ctx: int = 4096) -> dict:
    total_logicos = os.cpu_count() or 4
    optimo_default = max(total_logicos - 2, 2)
    try:
        from app.api.config import leer_config
        cfg = leer_config()
        dispositivo = cfg.get("dispositivo", "cpu")
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

    # ── Intento 2: prompt de rescate ─────────────────────────────────────────
    try:
        req_cortos = requisitos[:300] if len(requisitos) > 300 else requisitos
        cv_corto   = texto_cv[:500]   if len(texto_cv)   > 500  else texto_cv

        prompt_rescate = PROMPT_RESCATE.format(
            nombre_puesto=nombre_puesto,
            requisitos_cortos=req_cortos,
            cv_corto=cv_corto,
        )

        ctx_rescate = min(len(prompt_rescate) // 3 + 1000 + 128, max_ctx)
        opts_rescate = _get_opciones(max_ctx=ctx_rescate)
        opts_rescate["num_predict"] = 1000

        logger.info("  Rescate: ctx=%s tokens=1000 prompt_chars=%s", ctx_rescate, len(prompt_rescate))

        r2 = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt_rescate}],
            options=opts_rescate,
        )
        texto2 = r2["message"]["content"].strip()
        logger.info("  Rescate respuesta: %s chars", len(texto2))
        resultado = _parsear(texto2)
        resultado["_rescate"] = True
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
    reparado = texto.rstrip()
    if not reparado:
        return reparado

    zona = reparado[-300:] if len(reparado) > 300 else reparado
    comillas = len(re.findall(r'(?<!\\)"', zona))
    if comillas % 2 != 0:
        reparado += '"'

    reparado = reparado.rstrip().rstrip(',').rstrip(':').rstrip(',')

    ultimo_criterio = reparado.rfind('"criterio"')
    if ultimo_criterio > 0:
        fragmento = reparado[ultimo_criterio:]
        if not all(k in fragmento for k in ('"cumple"', '"puntaje"')):
            inicio = reparado.rfind('{', 0, ultimo_criterio)
            if inicio > 0:
                reparado = reparado[:inicio].rstrip(',').rstrip()

    faltan_c = max(0, reparado.count('[') - reparado.count(']'))
    faltan_l = max(0, reparado.count('{') - reparado.count('}'))
    reparado += ']' * faltan_c + '}' * faltan_l

    try:
        parcial = json.loads(reparado)
        if "resumen" not in parcial:
            reparado = reparado.rstrip('}').rstrip() + ',"resumen":"Analisis completado."}'
    except Exception:
        pass

    return reparado


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