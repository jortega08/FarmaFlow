"""Casos de uso para farmacias."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from dto.farmacia_dto import FarmaciaActualizarDTO, FarmaciaCrearDTO, FarmaciaDTO
from persistencia.modelos_orm import ClinicaFarmacia
from repositorios.repositorio_clinicas import RepositorioClinicas
from repositorios.repositorio_farmacias import RepositorioFarmacias
from repositorios.repositorio_tipos_farmacia import RepositorioTiposFarmacia
from servicios.excepciones import DatoDuplicadoError, EntidadNoEncontradaError, ValidacionDominioError
from servicios.paginacion import contiene_texto, paginar
from utilidades.texto import normalizar_texto


class ServicioFarmacias:
    """Orquesta operaciones de farmacias sin exponer modelos ORM."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion
        self._repo = RepositorioFarmacias(sesion)
        self._repo_clinicas = RepositorioClinicas(sesion)
        self._repo_tipos = RepositorioTiposFarmacia(sesion)

    def crear_farmacia(self, datos: FarmaciaCrearDTO) -> FarmaciaDTO:
        self._validar_campos_creacion(datos)
        self._validar_tipo_existente(datos.tipo_farmacia_id)
        self._validar_unicidad(datos.codigo, datos.nombre_original)

        farmacia = self._repo.crear(**datos.model_dump())
        return FarmaciaDTO.model_validate(farmacia)

    def listar_farmacias(self, activa: bool | None = None) -> list[FarmaciaDTO]:
        filtros = {} if activa is None else {"activa": activa}
        return [FarmaciaDTO.model_validate(farmacia) for farmacia in self._repo.listar(**filtros)]

    def buscar(self, texto: str, pagina: int = 1, filas_por_pagina: int = 20) -> list[FarmaciaDTO]:
        """Busca farmacias por codigo o nombre y retorna una pagina 1-indexed."""
        farmacias = sorted(
            self._repo.listar(),
            key=lambda farmacia: (farmacia.nombre_normalizado, farmacia.id),
        )
        filtradas = [
            FarmaciaDTO.model_validate(farmacia)
            for farmacia in farmacias
            if contiene_texto(
                texto,
                (farmacia.codigo, farmacia.nombre_original, farmacia.nombre_normalizado),
            )
        ]
        return paginar(filtradas, pagina, filas_por_pagina)

    def listar_por_tipo(self, tipo_codigo: str) -> list[FarmaciaDTO]:
        return [FarmaciaDTO.model_validate(farmacia) for farmacia in self._repo.listar_por_tipo(tipo_codigo)]

    def buscar_por_codigo_o_nombre(
        self,
        codigo: str | None = None,
        nombre: str | None = None,
    ) -> list[FarmaciaDTO]:
        farmacias = self._repo.buscar_por_codigo_o_nombre(codigo, nombre)
        return [FarmaciaDTO.model_validate(farmacia) for farmacia in farmacias]

    def obtener_farmacia(self, farmacia_id: int) -> FarmaciaDTO:
        farmacia = self._repo.obtener(farmacia_id)
        if farmacia is None:
            raise EntidadNoEncontradaError(f"No existe la farmacia con id {farmacia_id}.")
        return FarmaciaDTO.model_validate(farmacia)

    def actualizar_farmacia(self, farmacia_id: int, datos: FarmaciaActualizarDTO) -> FarmaciaDTO:
        farmacia_actual = self._repo.obtener(farmacia_id)
        if farmacia_actual is None:
            raise EntidadNoEncontradaError(f"No existe la farmacia con id {farmacia_id}.")

        campos = datos.model_dump(exclude_none=True)
        if not campos:
            return FarmaciaDTO.model_validate(farmacia_actual)

        if "codigo" in campos and not str(campos["codigo"]).strip():
            raise ValidacionDominioError("El codigo de la farmacia es obligatorio.")
        if "nombre_original" in campos and not str(campos["nombre_original"]).strip():
            raise ValidacionDominioError("El nombre de la farmacia es obligatorio.")
        if "tipo_farmacia_id" in campos:
            self._validar_tipo_existente(int(campos["tipo_farmacia_id"]))

        codigo = str(campos.get("codigo", farmacia_actual.codigo))
        nombre = str(campos.get("nombre_original", farmacia_actual.nombre_original))
        self._validar_unicidad(codigo, nombre, farmacia_id=farmacia_id)

        farmacia = self._repo.actualizar(farmacia_id, **campos)
        assert farmacia is not None
        return FarmaciaDTO.model_validate(farmacia)

    def desactivar_farmacia(self, farmacia_id: int) -> FarmaciaDTO:
        return self.actualizar_farmacia(farmacia_id, FarmaciaActualizarDTO(activa=False))

    def registrar_detectada(
        self,
        *,
        codigo: str,
        nombre_original: str,
        tipo_codigo: str = "NO_CLASIFICABLE",
    ) -> FarmaciaDTO:
        """Crea una farmacia detectada si no existe y retorna el DTO resultante."""
        farmacia = self._repo.obtener_por_codigo(codigo)
        if farmacia is not None:
            return FarmaciaDTO.model_validate(farmacia)

        tipo = self._repo_tipos.buscar_por_codigo(tipo_codigo)
        if tipo is None:
            raise EntidadNoEncontradaError(f"No existe el tipo de farmacia {tipo_codigo}.")

        return self.crear_farmacia(
            FarmaciaCrearDTO(
                codigo=codigo,
                nombre_original=nombre_original,
                tipo_farmacia_id=tipo.id,
            )
        )

    def crear_desde_deteccion(
        self,
        *,
        codigo_detectado: str | None,
        nombre_detectado: str,
        tipo_codigo: str = "NO_CLASIFICABLE",
        puede_prestar: bool | None = None,
        es_interna: bool | None = None,
        es_externa: bool | None = None,
    ) -> FarmaciaDTO:
        """Crea o retorna una farmacia detectada por ORG_ORIGEN/ORG_DESTINO."""
        codigo = (codigo_detectado or normalizar_texto(nombre_detectado) or "SIN_CODIGO").strip()
        nombre = nombre_detectado.strip()
        if not nombre:
            raise ValidacionDominioError("El nombre detectado de la farmacia es obligatorio.")

        tipo = self._repo_tipos.buscar_por_codigo(tipo_codigo)
        if tipo is None:
            raise EntidadNoEncontradaError(f"No existe el tipo de farmacia {tipo_codigo}.")

        existente = self._repo.obtener_por_codigo(codigo)
        if existente is not None:
            campos: dict[str, object] = {}
            nombre_normalizado = normalizar_texto(nombre)
            if existente.nombre_original != nombre or existente.nombre_normalizado != nombre_normalizado:
                campos["nombre_original"] = nombre
            tipo_actual = existente.tipo_farmacia.codigo if existente.tipo_farmacia is not None else ""
            if tipo_codigo != "NO_CLASIFICABLE" or tipo_actual == "NO_CLASIFICABLE":
                campos["tipo_farmacia_id"] = tipo.id
            if puede_prestar is not None:
                campos["puede_prestar"] = bool(puede_prestar)
            if es_interna is not None:
                campos["es_interna"] = bool(es_interna)
            if es_externa is not None:
                campos["es_externa"] = bool(es_externa)
            if not existente.activa:
                campos["activa"] = True
            if campos:
                actualizado = self._repo.actualizar(existente.id, **campos)
                assert actualizado is not None
                return FarmaciaDTO.model_validate(actualizado)
            return FarmaciaDTO.model_validate(existente)

        return self.crear_farmacia(
            FarmaciaCrearDTO(
                codigo=codigo,
                nombre_original=nombre,
                tipo_farmacia_id=tipo.id,
                puede_prestar=bool(puede_prestar) if puede_prestar is not None else True,
                es_interna=bool(es_interna) if es_interna is not None else tipo_codigo == "INTERNA",
                es_externa=bool(es_externa) if es_externa is not None else tipo_codigo == "EXTERNA",
            )
        )

    def asociar_a_clinica(
        self,
        farmacia_id: int,
        clinica_id: int,
        relacion: str | None = None,
    ) -> FarmaciaDTO:
        farmacia = self._repo.obtener(farmacia_id)
        if farmacia is None:
            raise EntidadNoEncontradaError(f"No existe la farmacia con id {farmacia_id}.")
        if self._repo_clinicas.obtener(clinica_id) is None:
            raise EntidadNoEncontradaError(f"No existe la clinica con id {clinica_id}.")

        consulta = select(ClinicaFarmacia).where(
            ClinicaFarmacia.clinica_id == clinica_id,
            ClinicaFarmacia.farmacia_id == farmacia_id,
        )
        asociacion = self._sesion.scalars(consulta).first()
        if asociacion is None:
            asociacion = ClinicaFarmacia(
                clinica_id=clinica_id,
                farmacia_id=farmacia_id,
                relacion=relacion,
                activa=True,
            )
            self._sesion.add(asociacion)
        else:
            asociacion.activa = True
            if relacion is not None:
                asociacion.relacion = relacion

        self._sesion.flush()
        self._sesion.refresh(farmacia)
        return FarmaciaDTO.model_validate(farmacia)

    def desasociar_de_clinica(self, farmacia_id: int, clinica_id: int) -> FarmaciaDTO:
        """Marca como inactiva la relacion entre una farmacia y una clinica."""
        farmacia = self._repo.obtener(farmacia_id)
        if farmacia is None:
            raise EntidadNoEncontradaError(f"No existe la farmacia con id {farmacia_id}.")
        if self._repo_clinicas.obtener(clinica_id) is None:
            raise EntidadNoEncontradaError(f"No existe la clinica con id {clinica_id}.")

        consulta = select(ClinicaFarmacia).where(
            ClinicaFarmacia.clinica_id == clinica_id,
            ClinicaFarmacia.farmacia_id == farmacia_id,
        )
        asociacion = self._sesion.scalars(consulta).first()
        if asociacion is not None:
            asociacion.activa = False
            self._sesion.flush()
        self._sesion.refresh(farmacia)
        return FarmaciaDTO.model_validate(farmacia)

    def marcar_como_cedi(self, farmacia_id: int) -> FarmaciaDTO:
        return self._marcar_tipo(farmacia_id, "CEDI")

    def marcar_como_devoluciones(self, farmacia_id: int) -> FarmaciaDTO:
        return self._marcar_tipo(farmacia_id, "DEVOLUCIONES")

    def marcar_puede_prestar(self, farmacia_id: int, puede_prestar: bool = True) -> FarmaciaDTO:
        return self.actualizar_farmacia(farmacia_id, FarmaciaActualizarDTO(puede_prestar=puede_prestar))

    def _validar_campos_creacion(self, datos: FarmaciaCrearDTO) -> None:
        if not datos.codigo.strip():
            raise ValidacionDominioError("El codigo de la farmacia es obligatorio.")
        if not datos.nombre_original.strip():
            raise ValidacionDominioError("El nombre de la farmacia es obligatorio.")

    def _validar_tipo_existente(self, tipo_farmacia_id: int) -> None:
        if self._repo_tipos.obtener(tipo_farmacia_id) is None:
            raise EntidadNoEncontradaError(f"No existe el tipo de farmacia con id {tipo_farmacia_id}.")

    def _validar_unicidad(self, codigo: str, nombre_original: str, farmacia_id: int | None = None) -> None:
        for farmacia in self._repo.buscar_por_codigo(codigo):
            if farmacia.id != farmacia_id:
                raise DatoDuplicadoError(f"Ya existe una farmacia con codigo {codigo}.")

    def _marcar_tipo(self, farmacia_id: int, tipo_codigo: str) -> FarmaciaDTO:
        tipo = self._repo_tipos.buscar_por_codigo(tipo_codigo)
        if tipo is None:
            raise EntidadNoEncontradaError(f"No existe el tipo de farmacia {tipo_codigo}.")
        return self.actualizar_farmacia(farmacia_id, FarmaciaActualizarDTO(tipo_farmacia_id=tipo.id))
