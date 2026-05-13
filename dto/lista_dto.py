"""DTOs de listas configurables."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ListaConfigurableCrearDTO(BaseModel):
    codigo: str
    nombre: str
    tipo_lista: str
    descripcion: str | None = None
    activa: bool = True


class ListaConfigurableActualizarDTO(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    tipo_lista: str | None = None
    descripcion: str | None = None
    activa: bool | None = None


class ListaConfigurableDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    tipo_lista: str
    descripcion: str | None
    activa: bool
    fecha_creacion: datetime
    fecha_modificacion: datetime


class ItemListaCrearDTO(BaseModel):
    lista_id: int
    valor: str
    codigo: str | None = None
    descripcion: str | None = None
    activo: bool = True


class ItemListaActualizarDTO(BaseModel):
    valor: str | None = None
    codigo: str | None = None
    descripcion: str | None = None
    activo: bool | None = None


class ItemListaDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lista_id: int
    codigo: str | None
    valor: str
    valor_normalizado: str
    descripcion: str | None
    activo: bool
    fecha_creacion: datetime
