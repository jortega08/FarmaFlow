"""DTOs para importacion de catalogos configurables."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorImportacionDTO(BaseModel):
    fila: int | None = None
    columna: str | None = None
    mensaje: str
    valor: str | None = None


class ItemImportacionDTO(BaseModel):
    fila: int
    codigo: str | None = None
    valor: str
    descripcion: str | None = None
    valor_normalizado: str
    estado: str = "VALIDO"


class PrevisualizacionImportacionDTO(BaseModel):
    ruta_archivo: str
    columnas: list[str]
    total_filas: int
    filas: list[dict[str, Any]]
    errores: list[ErrorImportacionDTO] = []


class ResultadoImportacionCatalogoDTO(BaseModel):
    lista_id: int
    tipo_lista: str
    total_filas: int
    creados: int
    duplicados: int
    ignorados: int
    errores: list[ErrorImportacionDTO] = []
    items_creados: list[ItemImportacionDTO] = []
