"""Casos de uso para tipos de farmacia."""

from __future__ import annotations

from sqlalchemy.orm import Session

from dto.farmacia_dto import TipoFarmaciaDTO
from repositorios.repositorio_tipos_farmacia import RepositorioTiposFarmacia
from servicios.excepciones import EntidadNoEncontradaError


class ServicioTiposFarmacia:
    """Consulta catalogos seed de tipos de farmacia."""

    def __init__(self, sesion: Session) -> None:
        self._repo = RepositorioTiposFarmacia(sesion)

    def listar_tipos(self) -> list[TipoFarmaciaDTO]:
        return [TipoFarmaciaDTO.model_validate(tipo) for tipo in self._repo.listar()]

    def obtener_tipo(self, tipo_id: int) -> TipoFarmaciaDTO:
        tipo = self._repo.obtener(tipo_id)
        if tipo is None:
            raise EntidadNoEncontradaError(f"No existe el tipo de farmacia con id {tipo_id}.")
        return TipoFarmaciaDTO.model_validate(tipo)

    def obtener_por_codigo(self, codigo: str) -> TipoFarmaciaDTO:
        tipo = self._repo.buscar_por_codigo(codigo)
        if tipo is None:
            raise EntidadNoEncontradaError(f"No existe el tipo de farmacia {codigo}.")
        return TipoFarmaciaDTO.model_validate(tipo)
