"""
Extracción de texto de archivos PDF usando pdfplumber.
"""

import re
from pathlib import Path
import pdfplumber

from app.utils.logger import get_logger

logger = get_logger(__name__)


def extraer_texto(pdf_path: Path) -> str:
    """Extrae todo el texto de un PDF. Retorna string vacío si falla."""
    try:
        texto = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                contenido = page.extract_text()
                if contenido:
                    texto.append(contenido)
        return "\n".join(texto).strip()
    except Exception as e:
        logger.error(f"Error extrayendo texto de {pdf_path}: {e}")
        return ""


def extraer_email(texto: str) -> str | None:
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", texto)
    return match.group(0) if match else None


def extraer_telefono(texto: str) -> str | None:
    match = re.search(r"(\+?\d[\d\s\-().]{7,15}\d)", texto)
    return match.group(0).strip() if match else None


def extraer_nombre(texto: str) -> str | None:
    """
    Heurística simple: el nombre suele estar en las primeras 3 líneas
    como texto en mayúsculas o con formato nombre-apellido.
    La IA complementará esta extracción.
    """
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    for linea in lineas[:5]:
        palabras = linea.split()
        if 2 <= len(palabras) <= 5 and all(p[0].isupper() for p in palabras if p.isalpha()):
            return linea
    return None


def extraer_datos_basicos(pdf_path: Path) -> dict:
    """Extrae texto + datos de contacto básicos del CV."""
    texto = extraer_texto(pdf_path)
    return {
        "texto": texto,
        "nombre": extraer_nombre(texto),
        "email": extraer_email(texto),
        "telefono": extraer_telefono(texto),
    }
