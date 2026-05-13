"""Repositorio de listas configurables."""

from __future__ import annotations

from sqlalchemy import select

from persistencia.modelos_orm import ListaConfigurable
from repositorios.repositorio_base import RepositorioBase


class RepositorioListas(RepositorioBase[ListaConfigurable]):
    """Operaciones especificas para listas configurables."""

    modelo = ListaConfigurable

    def buscar_por_codigo(self, codigo: str) -> ListaConfigurable | None:
        consulta = select(ListaConfigurable).where(ListaConfigurable.codigo == codigo)
        return self.sesion.scalars(consulta).first()

    def listar_activas(self) -> list[ListaConfigurable]:
        consulta = select(ListaConfigurable).where(ListaConfigurable.activa.is_(True))
        return list(self.sesion.scalars(consulta).all())

