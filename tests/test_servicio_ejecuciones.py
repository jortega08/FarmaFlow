"""Pruebas del servicio de ejecuciones."""

from __future__ import annotations

from sqlalchemy.orm import Session

from dto.ejecucion_dto import EjecucionCrearDTO, EjecucionDTO, EjecucionFinalizarDTO
from servicios.servicio_ejecuciones import ServicioEjecuciones


def test_registrar_y_finalizar_ejecucion(sesion_temporal: Session) -> None:
    servicio = ServicioEjecuciones(sesion_temporal)

    ejecucion = servicio.registrar_inicio(
        EjecucionCrearDTO(
            archivo_nombre="movimientos.xlsx",
            archivo_ruta="C:/tmp/movimientos.xlsx",
            hoja="Movimientos",
        )
    )
    finalizada = servicio.finalizar_ejecucion(
        ejecucion.id,
        EjecucionFinalizarDTO(
            estado="CLASIFICADA",
            total_registros=10,
            total_columnas=7,
            total_clasificados=8,
            total_sin_clasificar=2,
            mensaje="Clasificacion lista.",
        ),
    )

    assert isinstance(finalizada, EjecucionDTO)
    assert not hasattr(finalizada, "_sa_instance_state")
    assert finalizada.estado == "CLASIFICADA"
    assert finalizada.total_clasificados == 8
    assert finalizada.fecha_fin is not None
    assert servicio.listar_ejecuciones() == [finalizada]


def test_listar_ejecuciones_recientes_con_limite(sesion_temporal: Session) -> None:
    servicio = ServicioEjecuciones(sesion_temporal)
    primera = servicio.registrar_inicio(EjecucionCrearDTO(archivo_nombre="uno.xlsx"))
    segunda = servicio.registrar_inicio(EjecucionCrearDTO(archivo_nombre="dos.xlsx"))
    tercera = servicio.registrar_inicio(EjecucionCrearDTO(archivo_nombre="tres.xlsx"))

    recientes = servicio.listar_recientes(limite=2)

    assert [ejecucion.id for ejecucion in recientes] == [tercera.id, segunda.id]
    assert primera.id not in [ejecucion.id for ejecucion in recientes]
