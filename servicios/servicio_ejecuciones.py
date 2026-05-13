"""Casos de uso para ejecuciones de procesamiento."""

from __future__ import annotations

from sqlalchemy.orm import Session

from dto.ejecucion_dto import EjecucionCrearDTO, EjecucionDTO, EjecucionFinalizarDTO
from repositorios.repositorio_clinicas import RepositorioClinicas
from repositorios.repositorio_ejecuciones import RepositorioEjecuciones
from servicios.excepciones import EntidadNoEncontradaError, ValidacionDominioError


ESTADOS_EJECUCION = {"INICIADA", "VALIDADA", "CLASIFICADA", "EXPORTADA", "ERROR", "CANCELADA"}


class ServicioEjecuciones:
    """Registra el ciclo de vida resumido de un procesamiento."""

    def __init__(self, sesion: Session) -> None:
        self._repo = RepositorioEjecuciones(sesion)
        self._repo_clinicas = RepositorioClinicas(sesion)

    def registrar_inicio(self, datos: EjecucionCrearDTO) -> EjecucionDTO:
        if not datos.archivo_nombre.strip():
            raise ValidacionDominioError("El nombre del archivo es obligatorio.")
        if datos.clinica_id is not None and self._repo_clinicas.obtener(datos.clinica_id) is None:
            raise EntidadNoEncontradaError(f"No existe la clinica con id {datos.clinica_id}.")

        ejecucion = self._repo.crear_iniciada(**datos.model_dump())
        return EjecucionDTO.model_validate(ejecucion)

    def finalizar_ejecucion(self, ejecucion_id: int, datos: EjecucionFinalizarDTO) -> EjecucionDTO:
        self._validar_estado(datos.estado)
        totales = {
            campo: valor
            for campo, valor in datos.model_dump(exclude_none=True).items()
            if campo.startswith("total_")
        }
        self._validar_totales(totales)

        ejecucion = self._repo.marcar_finalizada(
            ejecucion_id,
            estado=datos.estado,
            totales=totales,
            mensaje=datos.mensaje,
        )
        if ejecucion is None:
            raise EntidadNoEncontradaError(f"No existe la ejecucion con id {ejecucion_id}.")
        return EjecucionDTO.model_validate(ejecucion)

    def registrar_ejecucion_completa(
        self,
        inicio: EjecucionCrearDTO,
        cierre: EjecucionFinalizarDTO,
    ) -> EjecucionDTO:
        ejecucion = self.registrar_inicio(inicio)
        return self.finalizar_ejecucion(ejecucion.id, cierre)

    def obtener_ejecucion(self, ejecucion_id: int) -> EjecucionDTO:
        ejecucion = self._repo.obtener(ejecucion_id)
        if ejecucion is None:
            raise EntidadNoEncontradaError(f"No existe la ejecucion con id {ejecucion_id}.")
        return EjecucionDTO.model_validate(ejecucion)

    def listar_ejecuciones(self) -> list[EjecucionDTO]:
        ejecuciones = sorted(
            self._repo.listar(),
            key=lambda ejecucion: (ejecucion.fecha_inicio, ejecucion.id),
            reverse=True,
        )
        return [EjecucionDTO.model_validate(ejecucion) for ejecucion in ejecuciones]

    def listar_recientes(self, limite: int = 20) -> list[EjecucionDTO]:
        """Lista las ejecuciones mas recientes, ordenadas de nueva a antigua."""
        if limite < 1:
            raise ValidacionDominioError("El limite debe ser mayor o igual a 1.")
        return self.listar_ejecuciones()[:limite]

    def _validar_estado(self, estado: str) -> None:
        if estado not in ESTADOS_EJECUCION:
            permitidos = ", ".join(sorted(ESTADOS_EJECUCION))
            raise ValidacionDominioError(f"Estado de ejecucion no permitido. Use uno de: {permitidos}.")

    def _validar_totales(self, totales: dict[str, int]) -> None:
        for campo, valor in totales.items():
            if valor < 0:
                raise ValidacionDominioError(f"El campo {campo} no puede ser negativo.")
