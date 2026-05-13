"""Pruebas del servicio de listas configurables."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from dto.lista_dto import ItemListaActualizarDTO, ItemListaCrearDTO, ItemListaDTO, ListaConfigurableCrearDTO
from servicios.excepciones import DatoDuplicadoError
from servicios.servicio_listas import ServicioListas


def test_crear_lista_agregar_items_y_desactivar_item(sesion_temporal: Session) -> None:
    servicio = ServicioListas(sesion_temporal)

    lista = servicio.crear_lista(
        ListaConfigurableCrearDTO(codigo="MOTIVOS", nombre="Motivos", tipo_lista="MOTIVOS")
    )
    item = servicio.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor=" Ajuste de inventario "))
    actualizado = servicio.actualizar_item(item.id, ItemListaActualizarDTO(descripcion="Uso operativo"))
    desactivado = servicio.desactivar_item(item.id)

    assert isinstance(item, ItemListaDTO)
    assert not hasattr(item, "_sa_instance_state")
    assert lista in servicio.listar_listas(activa=True)
    assert actualizado.descripcion == "Uso operativo"
    assert desactivado.activo is False
    assert servicio.listar_items(lista.id, activos=True) == []


def test_no_duplica_item_normalizado_en_lista(sesion_temporal: Session) -> None:
    servicio = ServicioListas(sesion_temporal)
    lista = servicio.crear_lista(
        ListaConfigurableCrearDTO(codigo="MOTIVOS", nombre="Motivos", tipo_lista="MOTIVOS")
    )

    servicio.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor="Ajuste de inventario"))

    with pytest.raises(DatoDuplicadoError):
        servicio.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor=" ajuste   de inventario "))


def test_buscar_items_con_paginacion(sesion_temporal: Session) -> None:
    servicio = ServicioListas(sesion_temporal)
    lista = servicio.crear_lista(
        ListaConfigurableCrearDTO(codigo="FARMACIAS", nombre="Farmacias", tipo_lista="FARMACIAS")
    )
    servicio.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor="Farmacia Norte"))
    servicio.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor="Farmacia Sur"))
    servicio.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor="Bodega Central"))

    pagina_1 = servicio.buscar_items(lista.id, "farmacia", pagina=1, filas_por_pagina=1)
    pagina_2 = servicio.buscar_items(lista.id, "farmacia", pagina=2, filas_por_pagina=1)

    assert [item.valor for item in pagina_1] == ["Farmacia Norte"]
    assert [item.valor for item in pagina_2] == ["Farmacia Sur"]


def test_listar_por_codigo_y_eliminar_item(sesion_temporal: Session) -> None:
    servicio = ServicioListas(sesion_temporal)
    lista = servicio.crear_lista(
        ListaConfigurableCrearDTO(codigo="LISTA_LIQUIDOS_TEST", nombre="Liquidos", tipo_lista="ARTICULOS")
    )
    item = servicio.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor="ART_001", codigo="ART_001"))

    assert [i.valor for i in servicio.listar_items_por_codigo("LISTA_LIQUIDOS_TEST", activos=True)] == ["ART_001"]

    servicio.eliminar_item(item.id)

    assert servicio.listar_items(lista.id, activos=True) == []
