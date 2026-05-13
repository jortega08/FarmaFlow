"""Repositorio base con operaciones CRUD simples."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session


T = TypeVar("T")


class RepositorioBase(Generic[T]):
    """CRUD generico para modelos SQLAlchemy."""

    modelo: type[T]

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def obtener(self, id: int) -> T | None:
        """Obtiene una entidad por llave primaria."""
        return self.sesion.get(self.modelo, id)

    def listar(self, **filtros: object) -> list[T]:
        """Lista entidades, opcionalmente filtradas por igualdad."""
        consulta = select(self.modelo)
        for campo, valor in filtros.items():
            consulta = consulta.where(getattr(self.modelo, campo) == valor)
        return list(self.sesion.scalars(consulta).all())

    def crear(self, **campos: object) -> T:
        """Crea y persiste una entidad."""
        entidad = self.modelo(**campos)
        self.sesion.add(entidad)
        self.sesion.flush()
        self.sesion.refresh(entidad)
        return entidad

    def actualizar(self, id: int, **campos: object) -> T | None:
        """Actualiza una entidad existente."""
        entidad = self.obtener(id)
        if entidad is None:
            return None

        for campo, valor in campos.items():
            setattr(entidad, campo, valor)

        self.sesion.flush()
        self.sesion.refresh(entidad)
        return entidad

    def eliminar(self, id: int) -> bool:
        """Elimina una entidad por id."""
        entidad = self.obtener(id)
        if entidad is None:
            return False

        self.sesion.delete(entidad)
        self.sesion.flush()
        return True

