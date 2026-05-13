"""DTOs de clinicas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClinicaCrearDTO(BaseModel):
    codigo: str | None = None
    nombre: str


class ClinicaActualizarDTO(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    activa: bool | None = None


class ClinicaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str | None
    nombre: str
    nombre_normalizado: str
    activa: bool
    fecha_creacion: datetime
    fecha_modificacion: datetime

