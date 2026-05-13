"""Pruebas del servicio de farmacias."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from dto.farmacia_dto import FarmaciaActualizarDTO, FarmaciaCrearDTO, FarmaciaDTO, TipoFarmaciaDTO
from servicios.excepciones import DatoDuplicadoError
from servicios.servicio_farmacias import ServicioFarmacias
from servicios.servicio_tipos_farmacia import ServicioTiposFarmacia


def test_crear_listar_actualizar_farmacia_y_consultar_tipos_seed(sesion_temporal: Session) -> None:
    tipos = ServicioTiposFarmacia(sesion_temporal).listar_tipos()
    tipo_interna = next(tipo for tipo in tipos if tipo.codigo == "INTERNA")
    servicio = ServicioFarmacias(sesion_temporal)

    farmacia = servicio.crear_farmacia(
        FarmaciaCrearDTO(
            codigo="16",
            nombre_original="16_Farma Farmacia Interna CRS",
            tipo_farmacia_id=tipo_interna.id,
            es_interna=True,
        )
    )
    actualizada = servicio.actualizar_farmacia(farmacia.id, FarmaciaActualizarDTO(puede_prestar=True))

    assert all(isinstance(tipo, TipoFarmaciaDTO) for tipo in tipos)
    assert isinstance(farmacia, FarmaciaDTO)
    assert not hasattr(farmacia, "_sa_instance_state")
    assert servicio.listar_farmacias() == [actualizada]
    assert servicio.listar_por_tipo("INTERNA") == [actualizada]
    assert actualizada.puede_prestar is True


def test_no_duplica_codigo_de_farmacia(sesion_temporal: Session) -> None:
    tipo = ServicioTiposFarmacia(sesion_temporal).obtener_por_codigo("INTERNA")
    servicio = ServicioFarmacias(sesion_temporal)

    servicio.crear_farmacia(
        FarmaciaCrearDTO(codigo="16", nombre_original="Farmacia Norte", tipo_farmacia_id=tipo.id)
    )
    with pytest.raises(DatoDuplicadoError):
        servicio.crear_farmacia(
            FarmaciaCrearDTO(codigo="16", nombre_original="Farmacia Sur", tipo_farmacia_id=tipo.id)
        )


def test_crear_desde_deteccion_hace_upsert_por_codigo_y_default_presta(sesion_temporal: Session) -> None:
    servicio = ServicioFarmacias(sesion_temporal)

    primera = servicio.crear_desde_deteccion(codigo_detectado="16", nombre_detectado="Farmacia Norte")
    segunda = servicio.crear_desde_deteccion(codigo_detectado="16", nombre_detectado="Farmacia Norte Actualizada")

    assert primera.id == segunda.id
    assert segunda.nombre_original == "Farmacia Norte Actualizada"
    assert segunda.puede_prestar is True


def test_buscar_farmacias_con_paginacion(sesion_temporal: Session) -> None:
    tipo = ServicioTiposFarmacia(sesion_temporal).obtener_por_codigo("INTERNA")
    servicio = ServicioFarmacias(sesion_temporal)
    servicio.crear_farmacia(FarmaciaCrearDTO(codigo="16", nombre_original="Farmacia Norte", tipo_farmacia_id=tipo.id))
    servicio.crear_farmacia(FarmaciaCrearDTO(codigo="17", nombre_original="Farmacia Sur", tipo_farmacia_id=tipo.id))
    servicio.crear_farmacia(FarmaciaCrearDTO(codigo="18", nombre_original="Bodega Central", tipo_farmacia_id=tipo.id))

    pagina_1 = servicio.buscar("farmacia", pagina=1, filas_por_pagina=1)
    pagina_2 = servicio.buscar("farmacia", pagina=2, filas_por_pagina=1)

    assert [farmacia.codigo for farmacia in pagina_1] == ["16"]
    assert [farmacia.codigo for farmacia in pagina_2] == ["17"]
