"""Modelo de salida para la preclasificacion tipologica."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ResultadoPreclasificacion:
    """Representa el resultado de la clasificacion preliminar por reglas."""

    exito: bool
    mensaje: str
    cantidad_registros: int = 0
    cantidad_clasificados: int = 0
    cantidad_sin_clasificar: int = 0
    tipologias_detectadas: dict[str, int] = field(default_factory=dict)
    farmacias_detectadas: dict[str, int] = field(default_factory=dict)
    dataframe_resultado: Any | None = field(default=None, repr=False)
