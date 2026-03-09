# -*- coding: utf-8 -*-
"""
Enums compartidos del dominio.
Centraliza strings mágicos que aparecían dispersos por el código.
"""

import enum


class ProcesoEstado(str, enum.Enum):
    """Estado calculado de un proceso de selección (no persiste en BD)."""
    SIN_ANALISIS = "sin_analisis"
    PENDIENTE    = "pendiente"
    EN_PROCESO   = "en_proceso"
    PARCIAL      = "parcial"
    FINALIZADO   = "finalizado"


class Dispositivo(str, enum.Enum):
    """Dispositivo de inferencia para Ollama."""
    CPU = "cpu"
    GPU = "gpu"
