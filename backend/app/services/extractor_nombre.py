# -*- coding: utf-8 -*-
"""
Extractor de nombre de candidato — v2 (5 capas de validación).

Capas:
  1. Posición   – primeras líneas del documento (≈ 20% inicial, máx 20 líneas)
  2. Patrón     – regex estrictos para MAYÚSCULAS o Title Case (3-20 chars/palabra)
  3. Filtro     – stopwords que identifican encabezados, cargos e instituciones
  4. Semántica  – rechazo de frases con conectores o estructura de cargo/sección
  5. Scoring    – puntuación de confianza para elegir el mejor candidato

Retorna None cuando no encuentra nombre con suficiente confianza, para que
la IA pueda intentar la extracción en el paso siguiente del pipeline.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Layer 3 — Stopwords: ninguna palabra de un nombre real debe aparecer aquí
# ---------------------------------------------------------------------------
_STOPWORDS: frozenset[str] = frozenset({
    # Encabezados / secciones de CV
    "curriculum", "vitae", "cv", "resume", "hoja",
    "perfil", "profile", "summary", "resumen",
    "experiencia", "experience", "laboral", "profesional",
    "educacion", "education", "formacion", "formacion",
    "habilidades", "skills", "competencias", "competences",
    "logros", "achievements", "proyectos", "projects",
    "certificaciones", "certifications", "certificados",
    "idiomas", "languages", "lenguajes",
    "contacto", "contact", "referencias", "references",
    "objetivo", "objective", "sobre", "acerca",
    "estudios", "realizados", "academica", "academico",
    "grado", "postgrado", "posgrado", "maestria",
    "doctorado", "carrera", "titulacion",
    "informacion", "personal", "datos",
    "nacimiento", "sexo", "edad", "civil", "nacionalidad",
    "domicilio", "residente", "presentacion",
    # Artículos / preposiciones (aparecen en cargos: "JEFE DE TI")
    "de", "del", "la", "el", "los", "las",
    "en", "con", "y", "por", "para", "a",
    "un", "una", "mi", "su", "al",
    # Profesiones / cargos
    "ingeniero", "ingeniera", "engineer",
    "desarrollador", "desarrolladora", "developer",
    "programador", "programadora", "programmer",
    "analista", "analyst", "sistemas", "informatica",
    "arquitecto", "arquitecta", "architect",
    "gerente", "manager", "director", "directora",
    "licenciado", "licenciada", "bachelor",
    "tecnico", "tecnica", "technician",
    "consultor", "consultora", "consultant",
    "disenador", "disenadora", "designer",
    "administrador", "administradora", "administrator",
    "especialista", "specialist",
    "coordinador", "coordinadora", "coordinator",
    "supervisor", "supervisora", "jefe", "jefa",
    "asistente", "assistant", "becario", "becaria",
    "ejecutivo", "ejecutiva",
    # Instituciones
    "universidad", "university", "instituto", "institute",
    "colegio", "college", "escuela", "school",
    # Contacto
    "email", "correo", "telefono", "phone", "movil", "mobile",
    "linkedin", "github", "twitter", "portfolio",
    "direccion", "address", "ciudad", "city",
    # Fechas
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    "january", "february", "march", "april", "june", "july",
    "august", "september", "october", "november", "december",
    # Tecnología
    "php", "sql", "java", "python", "javascript", "html", "css",
    "aws", "azure", "docker", "linux", "windows",
})

# ---------------------------------------------------------------------------
# Layer 2 — Patrones estructurales
# Cada palabra: 3-20 caracteres (rechaza "MI", "DE", "TI", "IT", etc.)
# ---------------------------------------------------------------------------

# Nombre en MAYÚSCULAS puras: JOSE VALENCIA, FRAN ELIOT BUSTAMANTE
_RE_CAPS = re.compile(
    r"^[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ]{3,20}"
    r"(?:\s[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ]{3,20}){1,3}$"
)

# Nombre en Title Case: Juan Perez, Maria Fernanda Torres
_RE_TITLE = re.compile(
    r"^[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ][a-záéíóúüñàèìòùâêîôûãõ]{2,19}"
    r"(?:(?:-[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ][a-záéíóúüñàèìòùâêîôûãõ]{1,19})"
    r"|(?:\s[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ][a-záéíóúüñàèìòùâêîôûãõ]{2,19})){1,3}$"
)

# Detectores de ruido
_RE_EMAIL    = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
_RE_TELEFONO = re.compile(r'(\+?\d[\d\s\-().]{5,}\d)')
_RE_URL      = re.compile(r'(https?://|www\.)', re.IGNORECASE)
_RE_NUMEROS  = re.compile(r'\d{2,}')
_RE_SIMBOLOS = re.compile(r'[|/\\@#$%^&*_+=\[\]{}~<>;:()\d]')

# ---------------------------------------------------------------------------
# Dataclass interna
# ---------------------------------------------------------------------------
@dataclass(order=True)
class _Candidato:
    score: float = field(compare=True)
    texto: str   = field(compare=False)
    indice: int  = field(compare=False)


# ---------------------------------------------------------------------------
# Utilidades públicas
# ---------------------------------------------------------------------------

def limpiar_linea(linea: str) -> str:
    """
    Normaliza una línea del CV:
    - Unicode NFC (unifica formas acentuadas)
    - Elimina caracteres de control
    - Colapsa espacios múltiples
    - Quita puntuación final irrelevante
    """
    linea = unicodedata.normalize("NFC", linea)
    linea = "".join(ch for ch in linea if not unicodedata.category(ch).startswith("C"))
    linea = " ".join(linea.split())
    return linea.strip().rstrip(".,;:-")


def _sin_tildes(texto: str) -> str:
    """Minúsculas sin diacríticos para comparación normalizada."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Layers 2 + 3 + 4 — Validación combinada
# ---------------------------------------------------------------------------

def parece_nombre(linea: str) -> bool:
    """
    Retorna True si la línea tiene estructura válida de nombre de persona.

    Layer 2 — Patrón: debe coincidir con CAPS o Title Case (3-20 chars/palabra).
    Layer 3 — Stopwords: ninguna palabra puede ser encabezado o cargo.
    Layer 4 — Semántica: rechaza frases con conectores o > 4 palabras.
    """
    linea = limpiar_linea(linea)

    # Longitud mínima y máxima de la línea completa
    if not linea or len(linea) < 5 or len(linea) > 60:
        return False

    # Ruido técnico (email, URL, números de 2+ dígitos, símbolos problemáticos)
    if _RE_EMAIL.search(linea) or _RE_URL.search(linea):
        return False
    if _RE_NUMEROS.search(linea) or _RE_SIMBOLOS.search(linea):
        return False

    # Layer 2: debe coincidir con patrón CAPS o Title Case
    if not _RE_CAPS.match(linea) and not _RE_TITLE.match(linea):
        return False

    # Layer 3: ninguna palabra puede ser stopword
    palabras_norm = [_sin_tildes(p.strip("-'")) for p in linea.split()]
    if any(p in _STOPWORDS for p in palabras_norm):
        return False

    # Layer 4: máximo 4 palabras (5+ indica sección o descripción)
    if len(palabras_norm) > 4:
        return False

    return True


# ---------------------------------------------------------------------------
# Layer 5 — Scoring de confianza (0–100)
# ---------------------------------------------------------------------------

def _calcular_score(
    indice: int,
    linea: str,
    indices_email: list[int],
    indices_telefono: list[int],
    total_lineas: int,
) -> float:
    """
    Asigna un puntaje de confianza basado en cinco señales:

      Posición    max 40  – líneas más arriba reciben más puntos
      Patrón      max 20  – ALL CAPS ligeramente superior a Title Case
      Palabras    max 20  – 2 o 3 palabras = óptimo para un nombre
      Cerca email max 15  – email en las 4 líneas siguientes
      Cerca tel   max  5  – teléfono en las 4 líneas siguientes
    """
    score = 0.0
    palabras = linea.split()
    n = len(palabras)

    # 1. Posición: línea 0 → 40 pts, línea N-1 → ~0 pts
    score += max(0.0, 1.0 - indice / max(total_lineas, 1)) * 40.0

    # 2. Patrón de capitalización
    if _RE_CAPS.match(linea):
        score += 20.0   # ALL CAPS es frecuente para destacar el nombre en CVs latinos
    else:
        score += 15.0   # Title Case también válido

    # 3. Cantidad de palabras
    if n == 3:
        score += 20.0
    elif n == 2:
        score += 18.0
    elif n == 4:
        score += 12.0

    # 4. Proximidad a email (contexto de datos de contacto)
    for idx_e in indices_email:
        if 0 < idx_e - indice <= 4:
            score += 15.0
            break

    # 5. Proximidad a teléfono
    for idx_t in indices_telefono:
        if 0 < idx_t - indice <= 4:
            score += 5.0
            break

    return score


# ---------------------------------------------------------------------------
# Fallback opcional: spaCy NER (no requerido, no rompe si no está instalado)
# ---------------------------------------------------------------------------

def _extraer_con_spacy(texto: str) -> Optional[str]:
    """
    Fallback con spaCy NER buscando entidades PERSON / PER.
    Silencioso si spaCy o sus modelos no están instalados.
    """
    try:
        import spacy  # type: ignore
    except ImportError:
        return None

    for modelo in ("es_core_news_lg", "es_core_news_md", "es_core_news_sm", "en_core_web_sm"):
        try:
            nlp = spacy.load(modelo)
            break
        except OSError:
            continue
    else:
        return None

    doc = nlp(texto[:600])
    for ent in doc.ents:
        if ent.label_ in ("PER", "PERSON"):
            candidato = limpiar_linea(ent.text)
            if parece_nombre(candidato):
                return candidato
    return None


# ---------------------------------------------------------------------------
# Sentinel público: valor devuelto cuando no se detecta nombre con confianza
# El pipeline en analisis_service.py reconoce este valor y permite que la IA
# lo sobrescriba con el nombre real que encuentre en el CV.
# ---------------------------------------------------------------------------
NOMBRE_NO_IDENTIFICADO = "Nombre no identificado"

# Regex para detectar nombre precedido de etiqueta: "Nombre: Juan Perez"
_RE_ETIQUETA_NOMBRE = re.compile(
    r'^(?:nombre|name)\s*[:\-]\s*(.+)$',
    re.IGNORECASE,
)


def _extraer_de_etiqueta(lineas: list[str]) -> Optional[str]:
    """
    Detecta patrones del tipo 'Nombre: Ricardo Cortez' en las primeras líneas
    y extrae el valor si pasa las validaciones de parece_nombre().
    """
    for linea in lineas:
        m = _RE_ETIQUETA_NOMBRE.match(linea)
        if m:
            valor = limpiar_linea(m.group(1))
            if parece_nombre(valor):
                return valor
    return None


# ---------------------------------------------------------------------------
# Función pública principal
# ---------------------------------------------------------------------------

def extraer_nombre_cv(texto_cv: str) -> str:
    """
    Extrae el nombre del candidato a partir del texto completo del CV.

    Estrategia:
      0. Detección por etiqueta ('Nombre: Ricardo Cortez')
      1-5. Cinco capas de validación con sistema de scoring.
      F. Fallback spaCy NER (si está instalado).

    Args:
        texto_cv: Texto plano extraído del PDF.

    Returns:
        Nombre completo del candidato.
        Si no se puede determinar, devuelve NOMBRE_NO_IDENTIFICADO
        ('Nombre no identificado') para que la IA lo corrija en el
        siguiente paso del pipeline.
    """
    if not texto_cv or not texto_cv.strip():
        return NOMBRE_NO_IDENTIFICADO

    # Preparar líneas no vacías
    lineas = [limpiar_linea(l) for l in texto_cv.splitlines()]
    lineas = [l for l in lineas if l]
    if not lineas:
        return NOMBRE_NO_IDENTIFICADO

    # Layer 1: ventana dinámica = 20% del documento, mínimo 10, máximo 20 líneas
    total_lineas = len(lineas)
    ventana = min(20, max(10, total_lineas // 5))
    lineas_utiles = lineas[:ventana]

    # Paso 0: formato etiquetado ("Nombre: Ricardo Cortez")
    nombre_etiqueta = _extraer_de_etiqueta(lineas_utiles)
    if nombre_etiqueta:
        return nombre_etiqueta

    # Pre-detectar posiciones de email y teléfono para el scoring contextual
    indices_email: list[int] = [
        i for i, l in enumerate(lineas_utiles) if _RE_EMAIL.search(l)
    ]
    indices_telefono: list[int] = [
        i for i, l in enumerate(lineas_utiles) if _RE_TELEFONO.search(l)
    ]

    # Evaluar cada línea: layers 2-4 via parece_nombre(), layer 5 via scoring
    candidatos: list[_Candidato] = []
    for i, linea in enumerate(lineas_utiles):
        if not parece_nombre(linea):
            continue
        score = _calcular_score(
            indice=i,
            linea=linea,
            indices_email=indices_email,
            indices_telefono=indices_telefono,
            total_lineas=len(lineas_utiles),
        )
        candidatos.append(_Candidato(score=score, texto=linea, indice=i))

    if candidatos:
        return max(candidatos).texto

    # Fallback: spaCy NER (solo si está instalado)
    nombre_spacy = _extraer_con_spacy(texto_cv)
    if nombre_spacy:
        return nombre_spacy

    return NOMBRE_NO_IDENTIFICADO
