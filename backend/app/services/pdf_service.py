"""
Extracción de texto y datos básicos de PDFs.
La extracción del nombre se delega a extractor_nombre.extraer_nombre_cv().
"""

import re
from pathlib import Path
import pdfplumber
from app.utils.logger import get_logger
from app.services.extractor_nombre import extraer_nombre_cv

logger = get_logger(__name__)

# Secciones relevantes para el análisis de compatibilidad, en orden de prioridad.
# Cada entrada: (regex de detección del header, nombre interno de sección)
_PRIORIDAD_SECCIONES = [
    (r'resumen|summary|perfil\s*prof|profile|objetivo|objective|sobre\s+m[ií]|acerca', 'resumen'),
    (r'experiencia|experience|trabajo|empleo|employment|work\s*hist|trayectoria|cargo', 'experiencia'),
    (r'habilidades|skills|competencias|conocimientos|tecnolog|herramientas|tools|stack', 'habilidades'),
    (r'educaci[oó]n|education|formaci[oó]n|estudio|acad[eé]m|t[ií]tulo|grado', 'educacion'),
    (r'certificaci[oó]n|certif|cursos?|courses?|capacitaci|training', 'certificaciones'),
    (r'idioma|language|lenguaje', 'idiomas'),
    (r'proyectos?|projects?|logros?|achievements?|portfolio', 'proyectos'),
]

# Palabras que, si aparecen solas en una línea corta, NO son headers de sección
_NO_ES_HEADER = re.compile(
    r'@|https?://|www\.|linkedin|github|\d{4}|\bde\b|\bthe\b|\band\b|\by\s+\b',
    re.IGNORECASE,
)


def extraer_secciones_relevantes(texto: str, max_chars: int = 2800) -> str:
    """
    Divide el CV en secciones por headers y retorna sólo el contenido
    relevante para el análisis LLM, priorizando experiencia y habilidades.

    Si no detecta secciones, retorna el texto hasta max_chars.
    Reduce el prompt entre un 20-40% respecto al truncado ciego.
    """
    lineas = texto.splitlines()
    secciones: dict[str, str] = {}
    seccion_actual: str | None = None
    buffer: list[str] = []

    def _flush():
        nonlocal seccion_actual, buffer
        if seccion_actual and buffer:
            contenido = "\n".join(buffer).strip()
            if contenido:
                # Si ya existe la sección, concatenar (puede aparecer varias veces)
                secciones[seccion_actual] = (
                    secciones.get(seccion_actual, "") + "\n" + contenido
                ).strip()
        buffer = []

    for linea in lineas:
        limpia = linea.strip()
        if not limpia:
            if buffer:
                buffer.append("")
            continue

        # Un header de sección es una línea corta que coincide con una categoría conocida
        # y no parece ser un dato de contacto ni una fecha
        es_header = (
            len(limpia) <= 55
            and not _NO_ES_HEADER.search(limpia)
            and any(re.search(pat, limpia, re.IGNORECASE) for pat, _ in _PRIORIDAD_SECCIONES)
        )

        if es_header:
            _flush()
            for pat, nombre in _PRIORIDAD_SECCIONES:
                if re.search(pat, limpia, re.IGNORECASE):
                    seccion_actual = nombre
                    break
        else:
            if seccion_actual is not None:
                buffer.append(limpia)

    _flush()

    if not secciones:
        # Sin secciones detectadas: truncado simple
        return texto[:max_chars]

    # Construir texto compacto en orden de prioridad
    orden = ['resumen', 'experiencia', 'habilidades', 'educacion',
             'certificaciones', 'idiomas', 'proyectos']
    partes: list[str] = []
    chars_usados = 0

    for nombre in orden:
        if nombre not in secciones:
            continue
        disponible = max_chars - chars_usados
        if disponible < 80:
            break
        contenido = secciones[nombre]
        if len(contenido) > disponible:
            # Cortar en límite de línea para no partir palabras
            contenido = contenido[:disponible].rsplit('\n', 1)[0]
        header = nombre.upper()
        bloque = f"{header}\n{contenido}"
        partes.append(bloque)
        chars_usados += len(bloque) + 2  # +2 para el separador \n\n

    resultado = "\n\n".join(partes)
    return resultado if resultado.strip() else texto[:max_chars]


def extraer_texto(pdf_path: Path) -> str:
    try:
        partes = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                texto = page.extract_text(layout=True)
                if texto:
                    partes.append(texto)
        return "\n".join(partes).strip()
    except Exception as e:
        logger.error(f"Error extrayendo texto de {pdf_path}: {e}")
        return ""


def extraer_email(texto: str) -> str | None:
    match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', texto)
    return match.group(0) if match else None


def extraer_telefono(texto: str) -> str | None:
    match = re.search(r'(\+?\d[\d\s\-().]{6,15}\d)', texto)
    return match.group(0).strip() if match else None


def extraer_nombre(texto: str) -> str | None:
    """
    Extrae el nombre del candidato delegando al módulo extractor_nombre.
    La IA puede completar o corregir el resultado si este falla.
    """
    return extraer_nombre_cv(texto)


def extraer_datos_basicos(pdf_path: Path) -> dict:
    texto = extraer_texto(pdf_path)
    return {
        "texto":    texto,
        "nombre":   extraer_nombre(texto),
        "email":    extraer_email(texto),
        "telefono": extraer_telefono(texto),
    }
