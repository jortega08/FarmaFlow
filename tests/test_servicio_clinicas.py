"""Pruebas del servicio de clinicas."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from dto.clinica_dto import ClinicaActualizarDTO, ClinicaCrearDTO, ClinicaDTO
from servicios.excepciones import DatoDuplicadoError
from servicios.servicio_clinicas import ServicioClinicas


def test_crear_listar_actualizar_y_desactivar_clinica(sesion_temporal: Session) -> None:
    servicio = ServicioClinicas(sesion_temporal)

    clinica = servicio.crear_clinica(ClinicaCrearDTO(codigo="CRS", nombre="Clinica del Rosario"))
    listado = servicio.listar_clinicas()
    actualizada = servicio.actualizar_clinica(
        clinica.id,
        ClinicaActualizarDTO(nombre="Clinica Rosario Norte"),
    )
    desactivada = servicio.desactivar_clinica(clinica.id)

    assert isinstance(clinica, ClinicaDTO)
    assert not hasattr(clinica, "_sa_instance_state")
    assert listado == [clinica]
    assert actualizada.nombre_normalizado == "CLINICA ROSARIO NORTE"
    assert desactivada.activa is False


def test_no_duplica_codigo_de_clinica_y_permite_rollback(sesion_temporal: Session) -> None:
    servicio = ServicioClinicas(sesion_temporal)

    servicio.crear_clinica(ClinicaCrearDTO(codigo="CRS", nombre="Clinica del Rosario"))
    with pytest.raises(DatoDuplicadoError):
        servicio.crear_clinica(ClinicaCrearDTO(codigo="CRS", nombre="Clinica repetida"))

    sesion_temporal.rollback()

    assert servicio.listar_clinicas() == []


def test_buscar_clinicas_con_paginacion(sesion_temporal: Session) -> None:
    servicio = ServicioClinicas(sesion_temporal)
    servicio.crear_clinica(ClinicaCrearDTO(codigo="NORTE", nombre="Clinica Norte"))
    servicio.crear_clinica(ClinicaCrearDTO(codigo="SUR", nombre="Clinica Sur"))
    servicio.crear_clinica(ClinicaCrearDTO(codigo="CENTRO", nombre="Centro Medico"))

    pagina_1 = servicio.buscar("clinica", pagina=1, filas_por_pagina=1)
    pagina_2 = servicio.buscar("clinica", pagina=2, filas_por_pagina=1)

    assert [clinica.codigo for clinica in pagina_1] == ["NORTE"]
    assert [clinica.codigo for clinica in pagina_2] == ["SUR"]
