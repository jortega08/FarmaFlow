"""Repositorio de ejecuciones de procesamiento."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from persistencia.modelos_orm import EjecucionProceso
from repositorios.repositorio_base import RepositorioBase


class RepositorioEjecuciones(RepositorioBase[EjecucionProceso]):
    """Operaciones especificas para ejecuciones."""

    modelo = EjecucionProceso

    def crear_iniciada(
        self,
        *,
        archivo_nombre: str,
        archivo_ruta: str | None = None,
        hoja: str | None = None,
        clinica_id: int | None = None,
        mensaje: str | None = None,
    ) -> EjecucionProceso:
        return self.crear(
            archivo_nombre=archivo_nombre,
            archivo_ruta=archivo_ruta,
            hoja=hoja,
            clinica_id=clinica_id,
            estado="INICIADA",
            mensaje=mensaje,
        )

    def marcar_finalizada(
        self,
        id: int,
        *,
        estado: str,
        totales: dict[str, Any] | None = None,
        mensaje: str | None = None,
    ) -> EjecucionProceso | None:
        ejecucion = self.obtener(id)
        if ejecucion is None:
            return None

        ahora = datetime.now()
        ejecucion.fecha_fin = ahora
        ejecucion.estado = estado
        ejecucion.mensaje = mensaje
        ejecucion.duracion_segundos = (ahora - ejecucion.fecha_inicio).total_seconds()

        for campo, valor in (totales or {}).items():
            if hasattr(ejecucion, campo):
                setattr(ejecucion, campo, valor)

        self.sesion.flush()
        self.sesion.refresh(ejecucion)
        return ejecucion
