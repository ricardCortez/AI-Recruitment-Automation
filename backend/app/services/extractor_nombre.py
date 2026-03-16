# -*- coding: utf-8 -*-
"""
Extractor de nombre de candidato — v3 (7 capas de validación).

Capas heurísticas (texto del CV):
  1. Posición   – primeras líneas del documento (≈ 20% inicial, máx 20 líneas)
  2. Patrón     – regex para MAYÚSCULAS o Title Case; acepta partículas (de, del, la…)
  3. Filtro     – stopwords que identifican encabezados, cargos e instituciones
                  (los conectores/artículos NO se tratan como stopwords duras)
  4. Semántica  – rechaza líneas con > 4 palabras o ruido técnico
  5. Scoring    – puntuación de confianza (posición, patrón, palabras, contexto)

Capas adicionales (cuando el texto falla):
  6. Metadata   – lee el campo Author / Creator del PDF (via dict de metadatos)
  7. Filename   – intenta extraer el nombre desde el nombre del archivo PDF

Retorna NOMBRE_NO_IDENTIFICADO si ninguna capa supera el umbral de confianza,
para que la IA lo corrija en el siguiente paso del pipeline.
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
    "educacion", "education", "formacion",
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
    # Artículos / preposiciones
    "de", "del", "la", "el", "los", "las",
    "en", "con", "y", "por", "para", "a",
    "un", "una", "mi", "su", "al",
    # Profesiones / cargos
    "ingeniero", "ingeniera", "ingenieria", "engineer",
    "desarrollador", "desarrolladora", "developer",
    "programador", "programadora", "programmer",
    "analista", "analyst", "sistemas", "informatica",
    "arquitecto", "arquitecta", "architect",
    "gerente", "manager", "director", "directora",
    "licenciado", "licenciada", "bachelor",
    "tecnico", "tecnica", "technician",
    "consultor", "consultora", "consultant",
    "disenador", "disenadora", "designer", "diseno",
    "administrador", "administradora", "administrator", "administracion",
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
    # ── Campos de estudio y carreras (falsos positivos frecuentes) ──────────
    "ciencias", "computacion", "computacional", "computacionales",
    "grafico", "grafica", "graficos", "graficas",
    "comunicacion", "comunicaciones",
    "contabilidad", "finanzas", "marketing", "ventas",
    "produccion", "logistica", "calidad",
    "electronica", "electronico", "electronica",
    "mecanica", "mecanico", "mecatronica",
    "industrial", "civil", "quimica", "quimico",
    "biologia", "biologico", "medicina", "medico",
    "derecho", "juridico", "juridica", "legal",
    "psicologia", "psicologo", "psicologa",
    "economia", "economico", "economista",
    "sociologia", "periodismo", "turismo",
    "gastronomia", "gastronomico",
    "farmacia", "enfermeria", "veterinaria",
    "topografia", "agronomia", "ambiental",
    "empresarial", "comercial", "bancaria", "bancario",
    "tributaria", "tributario", "fiscal",
    "multimedia", "audiovisual", "fotografica",
    "electromecanica", "telematica", "informatico",
    "sistemas", "redes", "telecomunicaciones",
    # Roles tech modernos
    "senior", "junior", "lead", "staff", "principal",
    "fullstack", "frontend", "backend", "devops",
    "cloud", "data", "science", "machine", "learning",
    "scrum", "agile", "product", "owner",
    # Documentos
    "carta", "solicitud", "postulacion", "candidatura",
    # Ubicaciones comunes (evitar "Lima Peru" como nombre)
    "peru", "chile", "mexico", "colombia", "argentina",
    "lima", "bogota", "santiago", "buenos", "aires",
    "caracas", "quito", "guayaquil", "cochabamba",
})

# ---------------------------------------------------------------------------
# Conectores/artículos que SÍ pueden aparecer en apellidos compuestos:
# "Juan de la Cruz", "CARLOS DEL VALLE", "Ana van der Berg"
# No se tratan como stopwords duras porque la regex ya evita que sean
# la primera palabra de un nombre.
# ---------------------------------------------------------------------------
_CONECTORES_NOMBRE: frozenset[str] = frozenset({
    "de", "del", "la", "el", "los", "las",
    "y", "e", "al", "van", "von", "der", "den",
})

# ---------------------------------------------------------------------------
# Prefijos de título profesional que a veces preceden al nombre en el CV.
# Los eliminamos antes de aplicar las validaciones.
# Ejemplos: "Lic. Juan Pérez", "Dr. Carlos Ramos", "Ing. María Flores"
# ---------------------------------------------------------------------------
_RE_TITULO_PROF = re.compile(
    r'^(?:lic\.?|dr\.?|dra\.?|ing\.?|mg\.?|msc\.?|mba\.?|prof\.?|abg\.?|arq\.?'
    r'|cpc\.?|tec\.?|sr\.?|sra\.?|ph\.?d\.?|m\.?d\.?)\s+',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Layer 2 — Patrones estructurales
# Primer bloque: palabra de 2-20 chars (permite "De", "Al" en el resto).
# Acepta partículas en minúscula entre palabras: "Juan de la Cruz".
# ---------------------------------------------------------------------------

# Nombre en MAYÚSCULAS puras: JOSE VALENCIA, FRAN ELIOT BUSTAMANTE
# Permite palabras cortas intermedias (DE, LA, DEL) de 2+ chars
_RE_CAPS = re.compile(
    r"^[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ]{2,20}"
    r"(?:\s[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ]{2,20}){1,4}$"
)

# Nombre en Title Case: Juan Perez, Maria Fernanda Torres, Juan de la Cruz
# Primer palabra: 2-20 chars; siguientes: capitalizadas O partículas en minúscula
_RE_TITLE = re.compile(
    r"^[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ][a-záéíóúüñàèìòùâêîôûãõ]{1,19}"
    r"(?:"
    r"(?:\s(?:de\s(?:(?:la|los|las|le)\s)?|del\s|van\s(?:der?\s)?|von\s)?)"
    r"[A-ZÁÉÍÓÚÜÑÀÈÌÒÙÂÊÎÔÛÃÕ][a-záéíóúüñàèìòùâêîôûãõ]{1,19}"
    r"){1,4}$"
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

    Layer 2 — Patrón: debe coincidir con CAPS o Title Case.
              Acepta partículas españolas (de, del, la…) entre palabras.
    Layer 3 — Stopwords: ninguna palabra SIGNIFICATIVA puede ser encabezado.
              Los conectores (_CONECTORES_NOMBRE) están exentos.
    Layer 4 — Semántica: rechaza líneas con > 5 palabras.
    """
    linea = limpiar_linea(linea)

    # Eliminar prefijo de título profesional si existe: "Lic. Juan Perez" → "Juan Perez"
    linea = _RE_TITULO_PROF.sub("", linea).strip()

    if not linea or len(linea) < 5 or len(linea) > 70:
        return False

    # Ruido técnico
    if _RE_EMAIL.search(linea) or _RE_URL.search(linea):
        return False
    if _RE_NUMEROS.search(linea) or _RE_SIMBOLOS.search(linea):
        return False

    # Layer 2: debe coincidir con patrón CAPS o Title Case
    if not _RE_CAPS.match(linea) and not _RE_TITLE.match(linea):
        return False

    # Layer 3: solo las palabras SIGNIFICATIVAS (no conectores) se chequean
    # contra stopwords. Esto permite "Juan de la Cruz" o "CARLOS DEL VALLE".
    palabras_norm = [_sin_tildes(p.strip("-'")) for p in linea.split()]
    palabras_significativas = [p for p in palabras_norm if p not in _CONECTORES_NOMBRE]
    if any(p in _STOPWORDS for p in palabras_significativas):
        return False

    # Layer 4: máximo 5 palabras (incluye partículas: "María de la Paz Torres")
    if len(palabras_norm) > 5:
        return False

    # Debe haber al menos 2 palabras significativas (no solo partículas)
    if len(palabras_significativas) < 2:
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
# Layer 6 — Extracción desde metadatos del PDF
# ---------------------------------------------------------------------------

def extraer_nombre_de_metadata(metadata: dict) -> Optional[str]:
    """
    Intenta extraer el nombre del candidato de los metadatos del PDF.

    Los campos más útiles son 'Author' y 'Creator'. Muchas personas
    guardan el CV con su nombre como autor del documento.

    Args:
        metadata: Diccionario con los metadatos del PDF
                  (pdfplumber: pdf.metadata, PyMuPDF: doc.metadata).

    Returns:
        Nombre si se detecta uno válido, None en caso contrario.
    """
    if not metadata:
        return None

    # Campos candidatos en orden de probabilidad
    for campo in ("Author", "author", "Creator", "creator", "Title", "title"):
        valor = metadata.get(campo)
        if not valor or not isinstance(valor, str):
            continue
        candidato = limpiar_linea(valor)
        # Filtrar valores genéricos de herramientas
        HERRAMIENTAS = {"microsoft word", "word", "acrobat", "adobe", "libreoffice",
                        "writer", "openoffice", "canva", "wps", "google docs",
                        "unknown", "desconocido", ""}
        if candidato.lower() in HERRAMIENTAS:
            continue
        if parece_nombre(candidato):
            return candidato
    return None


# ---------------------------------------------------------------------------
# Layer 7 — Extracción desde nombre de archivo
# ---------------------------------------------------------------------------

# Patrones de ruido comunes en nombres de archivo de CVs
_RE_RUIDO_FILENAME = re.compile(
    r'\b(cv|curriculum|vitae|resume|hoja|vida|postulacion|postulante|'
    r'solicitud|candidato|aplicacion|application|perfil|profile)\b',
    re.IGNORECASE,
)
# Separadores usados en nombres de archivo
_RE_SEPARADOR_FILENAME = re.compile(r'[-_. ]+')


# Separa CamelCase: "MariaFernandaTorres" → "Maria Fernanda Torres"
_RE_CAMEL_SPLIT = re.compile(r'(?<=[a-záéíóúüñ])(?=[A-ZÁÉÍÓÚÜÑ])')


def extraer_nombre_de_archivo(filename: str) -> Optional[str]:
    """
    Intenta extraer el nombre del candidato desde el nombre del archivo PDF.

    Maneja patrones comunes como:
      - "Ricardo_Cortez_CV.pdf"           → "Ricardo Cortez"
      - "CV_Juan_Carlos_Lopez.pdf"        → "Juan Carlos Lopez"
      - "MariaFernandaTorres_CV.pdf"      → "Maria Fernanda Torres"
      - "JuanPerez_PostulacionDev.pdf"    → "Juan Perez"

    Args:
        filename: Nombre del archivo (con o sin extensión, con o sin ruta).

    Returns:
        Nombre si se detecta uno válido, None en caso contrario.
    """
    if not filename:
        return None

    # Tomar solo el nombre de archivo sin ruta ni extensión
    stem = filename.replace("\\", "/").split("/")[-1]
    for ext in (".pdf", ".PDF", ".Pdf"):
        if stem.endswith(ext):
            stem = stem[:-len(ext)]
            break

    # 1. Separar CamelCase ANTES de reemplazar separadores
    #    "MariaFernandaTorres" → "Maria Fernanda Torres"
    stem = _RE_CAMEL_SPLIT.sub(" ", stem)

    # 2. Reemplazar separadores por espacios
    stem = _RE_SEPARADOR_FILENAME.sub(" ", stem).strip()

    # 3. Eliminar palabras de ruido (ahora con espacios, \b funciona bien)
    limpio = _RE_RUIDO_FILENAME.sub(" ", stem)
    limpio = " ".join(limpio.split())  # colapsar espacios

    if not limpio:
        return None

    # 4. Filtrar tokens inútiles (números, siglas, palabras muy cortas)
    palabras = [
        p for p in limpio.split()
        if p.isalpha() and len(p) >= 2 and p.lower() not in _STOPWORDS
    ]

    # 5. Intentar con 4, 3 o 2 palabras consecutivas en Title Case
    for n in (4, 3, 2):
        if len(palabras) >= n:
            intento = " ".join(palabras[:n]).title()
            if parece_nombre(intento):
                return intento

    return None


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

    # Umbral mínimo de confianza: evita aceptar candidatos muy débiles
    # Un nombre real en línea 0 con 2 palabras obtiene ~73 pts mínimo.
    # Reducimos a 30 para ser permisivos con CVs con poco contexto.
    _SCORE_MINIMO = 30.0
    candidatos_validos = [c for c in candidatos if c.score >= _SCORE_MINIMO]

    if candidatos_validos:
        return max(candidatos_validos).texto

    # Fallback: spaCy NER (solo si está instalado)
    nombre_spacy = _extraer_con_spacy(texto_cv)
    if nombre_spacy:
        return nombre_spacy

    return NOMBRE_NO_IDENTIFICADO
