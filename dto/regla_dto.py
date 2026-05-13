"""DTOs de reglas de clasificacion."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CondicionReglaCrearDTO(BaseModel):
    campo: str
    operador: str
    valor_texto: str | None = None
    lista_id: int | None = None
    atributo_farmacia: str | None = None
    orden: int = 0
    activa: bool = True


class CondicionReglaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    regla_id: int
    campo: str
    operador: str
    valor_texto: str | None
    lista_id: int | None
    atributo_farmacia: str | None
    orden: int
    activa: bool


class ReglaClasificacionCrearDTO(BaseModel):
    nombre: str
    tipologia_resultado: str
    descripcion: str | None = None
    prioridad: int = 100
    activa: bool = True
    origen: str = "SISTEMA"
    version: int = 1
    condiciones: list[CondicionReglaCrearDTO] = Field(default_factory=list)


class ReglaClasificacionActualizarDTO(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    tipologia_resultado: str | None = None
    prioridad: int | None = None
    activa: bool | None = None
    origen: str | None = None
    version: int | None = None


class ReglaClasificacionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    tipologia_resultado: str
    prioridad: int
    activa: bool
    origen: str
    version: int
    fecha_creacion: datetime
    fecha_modificacion: datetime
    condiciones: list[CondicionReglaDTO] = Field(default_factory=list)
