"""Modelo de salida para la exportacion de resultados."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ResultadoExportacion:
    """Representa el resultado de generar un archivo Excel multihoja."""

    exito: bool
    mensaje: str
    ruta_salida: str = ""
    nombre_archivo: str = ""
    hojas_generadas: list[str] = field(default_factory=list)
    cantidad_registros_exportados: int = 0
