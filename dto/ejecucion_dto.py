"""DTOs de ejecuciones de procesamiento."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EjecucionCrearDTO(BaseModel):
    archivo_nombre: str
    archivo_ruta: str | None = None
    hoja: str | None = None
    clinica_id: int | None = None
    mensaje: str | None = None


class EjecucionFinalizarDTO(BaseModel):
    estado: str
    total_registros: int | None = None
    total_columnas: int | None = None
    total_clasificados: int | None = None
    total_sin_clasificar: int | None = None
    mensaje: str | None = None


class EjecucionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_inicio: datetime
    fecha_fin: datetime | None
    clinica_id: int | None
    archivo_nombre: str
    archivo_ruta: str | None
    hoja: str | None
    total_registros: int
    total_columnas: int
    total_clasificados: int
    total_sin_clasificar: int
    duracion_segundos: float | None
    estado: str
    mensaje: str | None
