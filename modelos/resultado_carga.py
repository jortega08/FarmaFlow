"""Modelo de datos para la carga inicial del archivo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modelos.resultado_preclasificacion import ResultadoPreclasificacion
from modelos.resultado_validacion import ResultadoValidacion


@dataclass(slots=True)
class ResultadoCarga:
    """Representa el resultado de la lectura del archivo Excel."""

    exito: bool
    mensaje: str
    ruta_archivo: str = ""
    nombre_archivo: str = ""
    hoja_utilizada: str = ""
    cantidad_filas: int = 0
    cantidad_columnas: int = 0
    columnas: list[str] = field(default_factory=list)
    dataframe: Any | None = field(default=None, repr=False)
    dataframe_procesado: Any | None = field(default=None, repr=False)
    resultado_validacion: ResultadoValidacion | None = None
    resultado_preclasificacion: ResultadoPreclasificacion | None = None
    resumen_validacion: dict[str, Any] = field(default_factory=dict)
    resumen_preclasificacion: dict[str, Any] = field(default_factory=dict)
    estructura_valida: bool = False
