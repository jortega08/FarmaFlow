"""DTOs de farmacias y tipos de farmacia."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TipoFarmaciaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    descripcion: str | None


class FarmaciaCrearDTO(BaseModel):
    codigo: str
    nombre_original: str
    tipo_farmacia_id: int
    puede_prestar: bool = True
    es_interna: bool = False
    es_externa: bool = False
    activa: bool = True


class FarmaciaActualizarDTO(BaseModel):
    codigo: str | None = None
    nombre_original: str | None = None
    tipo_farmacia_id: int | None = None
    puede_prestar: bool | None = None
    es_interna: bool | None = None
    es_externa: bool | None = None
    activa: bool | None = None


class FarmaciaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre_original: str
    nombre_normalizado: str
    tipo_farmacia_id: int
    puede_prestar: bool
    es_interna: bool
    es_externa: bool
    activa: bool
    fecha_creacion: datetime
    fecha_modificacion: datetime
