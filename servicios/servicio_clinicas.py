"""Casos de uso para clinicas."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from dto.clinica_dto import ClinicaActualizarDTO, ClinicaCrearDTO, ClinicaDTO
from dto.farmacia_dto import FarmaciaDTO
from persistencia.modelos_orm import ClinicaFarmacia, Farmacia
from repositorios.repositorio_clinicas import RepositorioClinicas
from servicios.excepciones import DatoDuplicadoError, EntidadNoEncontradaError, ValidacionDominioError
from servicios.paginacion import contiene_texto, paginar


class ServicioClinicas:
    """Orquesta operaciones de clinicas sin exponer ORM a la UI."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion
        self._repo = RepositorioClinicas(sesion)

    def crear_clinica(self, datos: ClinicaCrearDTO) -> ClinicaDTO:
        if not datos.nombre.strip():
            raise ValidacionDominioError("El nombre de la clinica es obligatorio.")

        if datos.codigo and self._repo.buscar_por_codigo(datos.codigo):
            raise DatoDuplicadoError(f"Ya existe una clinica con codigo {datos.codigo}.")

        clinica = self._repo.crear(**datos.model_dump())
        return ClinicaDTO.model_validate(clinica)

    def listar_clinicas(self, activa: bool | None = None) -> list[ClinicaDTO]:
        filtros = {} if activa is None else {"activa": activa}
        return [ClinicaDTO.model_validate(clinica) for clinica in self._repo.listar(**filtros)]

    def buscar(self, texto: str, pagina: int = 1, filas_por_pagina: int = 20) -> list[ClinicaDTO]:
        """Busca clinicas por codigo o nombre y retorna una pagina 1-indexed."""
        clinicas = sorted(
            self._repo.listar(),
            key=lambda clinica: (clinica.nombre_normalizado, clinica.id),
        )
        filtradas = [
            ClinicaDTO.model_validate(clinica)
            for clinica in clinicas
            if contiene_texto(texto, (clinica.codigo, clinica.nombre, clinica.nombre_normalizado))
        ]
        return paginar(filtradas, pagina, filas_por_pagina)

    def obtener_clinica(self, clinica_id: int) -> ClinicaDTO:
        clinica = self._repo.obtener(clinica_id)
        if clinica is None:
            raise EntidadNoEncontradaError(f"No existe la clinica con id {clinica_id}.")
        return ClinicaDTO.model_validate(clinica)

    def obtener_o_error(self, clinica_id: int) -> ClinicaDTO:
        return self.obtener_clinica(clinica_id)

    def listar_farmacias_de_clinica(self, clinica_id: int) -> list[FarmaciaDTO]:
        if self._repo.obtener(clinica_id) is None:
            raise EntidadNoEncontradaError(f"No existe la clinica con id {clinica_id}.")

        consulta = (
            select(Farmacia)
            .join(ClinicaFarmacia, ClinicaFarmacia.farmacia_id == Farmacia.id)
            .where(
                ClinicaFarmacia.clinica_id == clinica_id,
                ClinicaFarmacia.activa.is_(True),
                Farmacia.activa.is_(True),
            )
            .order_by(Farmacia.nombre_normalizado, Farmacia.id)
        )
        return [FarmaciaDTO.model_validate(farmacia) for farmacia in self._sesion.scalars(consulta).all()]

    def actualizar_clinica(self, clinica_id: int, datos: ClinicaActualizarDTO) -> ClinicaDTO:
        campos = datos.model_dump(exclude_none=True)
        if not campos:
            return self.obtener_clinica(clinica_id)

        if "nombre" in campos and not str(campos["nombre"]).strip():
            raise ValidacionDominioError("El nombre de la clinica no puede estar vacio.")

        if "codigo" in campos and campos["codigo"]:
            existente = self._repo.buscar_por_codigo(str(campos["codigo"]))
            if existente is not None and existente.id != clinica_id:
                raise DatoDuplicadoError(f"Ya existe una clinica con codigo {campos['codigo']}.")

        clinica = self._repo.actualizar(clinica_id, **campos)
        if clinica is None:
            raise EntidadNoEncontradaError(f"No existe la clinica con id {clinica_id}.")
        return ClinicaDTO.model_validate(clinica)

    def desactivar_clinica(self, clinica_id: int) -> ClinicaDTO:
        return self.actualizar_clinica(clinica_id, ClinicaActualizarDTO(activa=False))
