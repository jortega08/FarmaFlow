"""Modelo de salida para la validacion estructural del archivo."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ResultadoValidacion:
    """Representa el estado de la validacion de columnas del archivo Oracle."""

    exito: bool
    mensaje: str
    columnas_originales: list[str] = field(default_factory=list)
    columnas_normalizadas: list[str] = field(default_factory=list)
    columnas_encontradas: list[str] = field(default_factory=list)
    columnas_faltantes: list[str] = field(default_factory=list)
    columnas_mapeadas: dict[str, str] = field(default_factory=dict)
    columnas_desconocidas: list[str] = field(default_factory=list)
    estructura_valida: bool = False
