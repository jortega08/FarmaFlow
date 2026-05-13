"""Repositorio de tipos de farmacia."""

from __future__ import annotations

from sqlalchemy import select

from persistencia.modelos_orm import TipoFarmacia
from repositorios.repositorio_base import RepositorioBase


class RepositorioTiposFarmacia(RepositorioBase[TipoFarmacia]):
    """Operaciones especificas para tipos de farmacia."""

    modelo = TipoFarmacia

    def buscar_por_codigo(self, codigo: str) -> TipoFarmacia | None:
        consulta = select(TipoFarmacia).where(TipoFarmacia.codigo == codigo)
        return self.sesion.scalars(consulta).first()

