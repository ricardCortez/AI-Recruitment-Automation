"""
Extracción de texto y datos básicos de PDFs.
Mejoras: nombre más preciso con múltiples heurísticas combinadas.
"""

import re
from pathlib import Path
import pdfplumber
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Palabras que NO son nombres (encabezados comunes de CVs)
PALABRAS_EXCLUIR = {
    'curriculum', 'vitae', 'cv', 'resume', 'perfil', 'profile',
    'datos', 'personales', 'información', 'contacto', 'contact',
    'experiencia', 'experience', 'educación', 'education',
    'habilidades', 'skills', 'objetivo', 'summary', 'sobre',
    'dirección', 'address', 'teléfono', 'phone', 'email', 'correo',
    'linkedin', 'github', 'fecha', 'nacimiento',
}


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
    Heurísticas en orden de confianza para extraer el nombre.
    La IA corregirá si esto falla.
    """
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    lineas_utiles = lineas[:20]  # Solo las primeras 20 líneas

    candidatos = []

    for linea in lineas_utiles:
        # Ignorar líneas demasiado largas o cortas
        if len(linea) < 4 or len(linea) > 60:
            continue

        # Ignorar si contiene @, números solos, o palabras clave
        if '@' in linea or re.search(r'\d{4,}', linea):
            continue

        palabras = linea.split()
        if len(palabras) < 2 or len(palabras) > 5:
            continue

        # Ignorar si alguna palabra está en la lista de exclusión
        palabras_lower = [p.lower().strip('.,:-') for p in palabras]
        if any(p in PALABRAS_EXCLUIR for p in palabras_lower):
            continue

        # Ignorar si tiene caracteres raros
        if re.search(r'[|/\\@#$%^&*()_+=\[\]{}]', linea):
            continue

        # Contar palabras que empiezan con mayúscula
        mayusculas = sum(1 for p in palabras if p and p[0].isupper())

        # Score: más palabras con mayúscula = más probable que sea nombre
        score = mayusculas / len(palabras)
        if score >= 0.6:
            candidatos.append((score, linea))

    if candidatos:
        # Retornar el candidato con mayor score
        candidatos.sort(reverse=True)
        return candidatos[0][1]

    return None


def extraer_datos_basicos(pdf_path: Path) -> dict:
    texto = extraer_texto(pdf_path)
    return {
        "texto":    texto,
        "nombre":   extraer_nombre(texto),
        "email":    extraer_email(texto),
        "telefono": extraer_telefono(texto),
    }
