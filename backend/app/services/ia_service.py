# -*- coding: utf-8 -*-
"""
Motor de IA — v6
- Valoracion de excedente (v5)
- Deteccion de alertas en el CV (inconsistencias, vacios, señales de riesgo)
- Generacion de preguntas especificas para entrevista
"""

import json
import re
import os
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

MODELO_PARAMS = {
    "llama3.1:8b":  {"num_predict": 1800, "num_ctx": 4096, "verboso": False},
    "qwen2.5:7b":   {"num_predict": 3000, "num_ctx": 4096, "verboso": True},
    "qwen2.5:14b":  {"num_predict": 1800, "num_ctx": 4096, "verboso": False},
    "qwen2.5:32b":  {"num_predict": 1800, "num_ctx": 4096, "verboso": False},
}

_INST_CORTA  = " Descripciones MUY CORTAS: max 8 palabras. Preguntas directas y breves."
_INST_NORMAL = " Descripciones concisas: max 14 palabras. Preguntas claras y especificas."

PROMPT_COMPLETO = """Eres un evaluador experto en RRHH. Evalua con MAXIMA PRECISION el CV vs los requisitos.{instruccion}
Responde SOLO JSON valido, sin markdown ni texto extra.

PUESTO: {nombre_puesto}
REQUISITOS EXACTOS DEL PUESTO:
{requisitos}

CV DEL CANDIDATO:
{texto_cv}

═══════════════════════════════════════════════════════════════
PRINCIPIO FUNDAMENTAL:
Un candidato que tiene MAS de lo requerido es MAS VALIOSO.
Experiencia extra, certs adicionales, habilidades adicionales relevantes
AUMENTAN el puntaje. No penalices el excedente: PREMIALO.
═══════════════════════════════════════════════════════════════

ESCALA DE PUNTAJE (aplica criterio por criterio):
  100    = Tiene doble o mas de lo pedido (ej: piden 3 años → tiene 10+)
  90-99  = Excede notablemente (piden 3 años → tiene 6-9; piden B2 → tiene C2)
  80-89  = Supera lo requerido: cumple todo + algo extra relevante
  70-79  = Cumple exactamente los requisitos
  55-69  = Cumple parcialmente, falta algo secundario
  35-54  = Cumple a medias, brechas importantes
  10-34  = Cumple poco, brechas criticas
   0-9   = No cumple

REGLAS CRITICAS:
1. Mas años de exp que los pedidos → puntaje > 70. Formula: min(100, 70 + (extra/requeridos)*30)
2. Certificaciones o titulos ADICIONALES relevantes → sube el puntaje del criterio
3. Herramientas/tecnologias extra utiles para el puesto → sube el puntaje
4. Nivel de idioma superior al requerido → puntaje 90+
5. El excedente SIEMPRE se menciona en la descripcion

INSTRUCCIONES:

PASO 1 — Criterios: agrupa los requisitos (ej: Experiencia, Formacion, Conocimientos, Idiomas).
PASO 2 — Pesos: asigna importancia a cada criterio. Todos deben sumar exactamente 100.
PASO 3 — Evalua cada criterio (puntaje 0-100, premia excedente, describe excedente si aplica).
PASO 4 — puntaje_total = suma(peso_i * puntaje_i / 100). Verifica el calculo.
PASO 5 — cumple: "si">=70 | "parcial" 40-69 | "no"<40
PASO 6 — resumen: "APTO"/"APTO CON RESERVAS"/"NO APTO" + fortalezas + brechas.
          Si supera requisitos, agregar "VALOR AGREGADO: <detalle>"

PASO 7 — alertas: Detecta señales de riesgo o inconsistencias en el CV. Para cada alerta:
  - tipo: "inconsistencia" | "vacio" | "riesgo" | "verificar"
  - nivel: "alta" | "media" | "baja"
  - descripcion: que se detecto (max 15 palabras)
  Tipos de alertas a buscar:
  * "inconsistencia": fechas solapadas, saltos inexplicables de carrera, años que no cierran
  * "vacio": falta de info clave (sin email, sin institucion en el titulo, experiencia sin fechas)
  * "riesgo": rotacion alta (muchos trabajos cortos <1 año), brecha laboral larga sin explicar
  * "verificar": titulo sin nombre de institucion, certificacion sin entidad emisora, logros sin metricas verificables
  Si el CV no tiene alertas reales, devolver lista vacia [].
  Maximo 5 alertas. Solo incluir las que realmente detectas en el CV.

PASO 8 — preguntas: Genera 4-5 preguntas especificas para la entrevista basadas en:
  a) Brechas detectadas: preguntar sobre lo que falta o es parcial
  b) Excedentes: profundizar en lo que el candidato tiene de mas (aprovecharlo)
  c) Alertas criticas: aclarar inconsistencias o vacios importantes
  d) Fit cultural/puesto: preguntas sobre motivacion y expectativas segun el rol
  Para cada pregunta:
  - categoria: "brecha" | "excedente" | "alerta" | "fit"
  - pregunta: la pregunta textual (max 25 palabras)
  - objetivo: que informacion busca obtener (max 10 palabras)

JSON exacto (sin texto antes ni despues):
{{"nombre":"<str|null>","email":"<str|null>","telefono":"<str|null>","puntaje_total":<0-100>,"criterios":[{{"criterio":"<str>","peso":<0-100>,"puntaje":<0-100>,"cumple":"<si|parcial|no>","descripcion":"<frase con excedente si aplica>"}}],"resumen":"<APTO/NO APTO + valor agregado si aplica>","alertas":[{{"tipo":"<inconsistencia|vacio|riesgo|verificar>","nivel":"<alta|media|baja>","descripcion":"<texto>"}}],"preguntas":[{{"categoria":"<brecha|excedente|alerta|fit>","pregunta":"<texto>","objetivo":"<texto>"}}]}}"""


PROMPT_RESCATE = """Evalua este CV para el puesto. Responde SOLO con JSON valido.
Si el candidato tiene MAS de lo requerido, puntaje > 70 (hasta 100).

PUESTO: {nombre_puesto}
REQUISITOS: {requisitos_cortos}
CV: {cv_corto}

JSON (puntaje>70 si supera requisito; alertas=inconsistencias detectadas; preguntas=para entrevista):
{{"nombre":"<str>","email":"<str>","telefono":"<str>","puntaje_total":<0-100>,"criterios":[{{"criterio":"<str>","peso":<int>,"puntaje":<int>,"cumple":"<si|parcial|no>","descripcion":"<breve>"}}],"resumen":"<APTO/NO APTO>","alertas":[{{"tipo":"<inconsistencia|vacio|riesgo|verificar>","nivel":"<alta|media|baja>","descripcion":"<texto>"}}],"preguntas":[{{"categoria":"<brecha|excedente|alerta|fit>","pregunta":"<texto>","objetivo":"<texto>"}}]}}"""


def _params_modelo(modelo: str) -> dict:
    if modelo in MODELO_PARAMS:
        return MODELO_PARAMS[modelo]
    for key, val in MODELO_PARAMS.items():
        if modelo.startswith(key.split(":")[0]):
            return val
    return {"num_predict": 2500, "num_ctx": 4096, "verboso": True}


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
            "Modelo '{}' es BASE. Usa variante -instruct.".format(settings.OLLAMA_MODEL)
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
        if any(k in msg for k in ("ollama no responde", "no descargado", "base", "vacia")):
            raise RuntimeError("Error Ollama: {}".format(e))
        logger.warning("  Intento 1 fallido (%s) — reintentando con rescate...", e)

    except Exception as e:
        msg = str(e).lower()
        if "connection" in msg or "refused" in msg:
            raise RuntimeError("Ollama no responde. Verifica que este corriendo.")
        if "not found" in msg or "pull" in msg:
            raise RuntimeError("Modelo '{}' no descargado.".format(settings.OLLAMA_MODEL))
        logger.warning("  Intento 1 fallido (%s) — reintentando con rescate...", e)

    # ── Rescate ───────────────────────────────────────────────────────────────
    try:
        req_cortos = requisitos[:300] if len(requisitos) > 300 else requisitos
        cv_corto   = texto_cv[:500]   if len(texto_cv)   > 500  else texto_cv

        prompt_rescate = PROMPT_RESCATE.format(
            nombre_puesto=nombre_puesto,
            requisitos_cortos=req_cortos,
            cv_corto=cv_corto,
        )

        ctx_rescate  = min(len(prompt_rescate) // 3 + 1200 + 128, max_ctx)
        opts_rescate = _get_opciones(max_ctx=ctx_rescate)
        opts_rescate["num_predict"] = 1200

        logger.info("  Rescate: ctx=%s tokens=1200 prompt_chars=%s", ctx_rescate, len(prompt_rescate))

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
        max_tokens=2000,
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

_ALERTA_NIVEL_MAP  = {"alta": "alta", "alto": "alta", "high": "alta",
                      "media": "media", "medio": "media", "medium": "media",
                      "baja": "baja", "bajo": "baja", "low": "baja"}
_ALERTA_TIPO_MAP   = {"inconsistencia": "inconsistencia", "inconsistency": "inconsistencia",
                      "vacio": "vacio", "vacío": "vacio", "missing": "vacio",
                      "riesgo": "riesgo", "risk": "riesgo",
                      "verificar": "verificar", "verify": "verificar", "check": "verificar"}
_PREGUNTA_CAT_MAP  = {"brecha": "brecha", "gap": "brecha",
                      "excedente": "excedente", "surplus": "excedente",
                      "alerta": "alerta", "alert": "alerta",
                      "fit": "fit", "cultura": "fit", "cultural": "fit"}


def _normalizar_cumple(valor: str) -> str:
    return _CUMPLE_MAP.get(str(valor).lower().strip(), "no")


def _normalizar_alertas(raw: list) -> list:
    alertas = []
    for a in (raw or []):
        if not isinstance(a, dict):
            continue
        desc = str(a.get("descripcion") or a.get("description") or "").strip()
        if not desc:
            continue
        alertas.append({
            "tipo":        _ALERTA_TIPO_MAP.get(str(a.get("tipo","")).lower().strip(), "verificar"),
            "nivel":       _ALERTA_NIVEL_MAP.get(str(a.get("nivel","")).lower().strip(), "media"),
            "descripcion": desc[:120],
        })
    return alertas[:5]


def _normalizar_preguntas(raw: list) -> list:
    preguntas = []
    for p in (raw or []):
        if not isinstance(p, dict):
            continue
        texto = str(p.get("pregunta") or p.get("question") or "").strip()
        if not texto:
            continue
        preguntas.append({
            "categoria": _PREGUNTA_CAT_MAP.get(str(p.get("categoria","")).lower().strip(), "brecha"),
            "pregunta":  texto[:200],
            "objetivo":  str(p.get("objetivo") or p.get("objective") or "").strip()[:80],
        })
    return preguntas[:5]


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
            data = json.loads(_reparar_json(texto))
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

    # ── Recalcular puntaje_total desde los criterios (corrige errores aritméticos de la IA) ──
    if data["criterios"]:
        total_peso = sum(float(c.get("peso") or 0) for c in data["criterios"])
        if total_peso > 5:
            # Tiene pesos → calcular promedio ponderado
            recalc = sum(float(c.get("peso") or 0) * float(c["puntaje"]) / 100
                         for c in data["criterios"])
            if abs(total_peso - 100) > 2:
                # Los pesos no suman 100 → normalizar
                recalc = recalc * 100 / total_peso
        else:
            # Sin pesos → promedio simple
            recalc = sum(float(c["puntaje"]) for c in data["criterios"]) / len(data["criterios"])
        data["puntaje_total"] = max(0.0, min(100.0, round(recalc, 1)))

    for c in data["criterios"]:
        c["puntaje"] = max(0.0, min(100.0, float(c.get("puntaje", 0))))
        c["cumple"]  = _normalizar_cumple(c.get("cumple", "no"))

    for campo in ("nombre", "email", "telefono"):
        v = data.get(campo)
        if not v or str(v).lower() in ("null", "none", "n/a", "no encontrado", ""):
            data[campo] = None
        else:
            data[campo] = str(v).strip()

    # Normalizar alertas y preguntas (tolerante a ausencia)
    data["alertas"]   = _normalizar_alertas(data.get("alertas", []))
    data["preguntas"] = _normalizar_preguntas(data.get("preguntas", []))

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