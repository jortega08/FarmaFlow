"""Pruebas de repositorios de listas."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from repositorios.repositorio_lista_items import RepositorioListaItems
from repositorios.repositorio_listas import RepositorioListas


def test_crear_lista_items_y_buscar_normalizado(sesion_temporal: Session) -> None:
    repo_listas = RepositorioListas(sesion_temporal)
    repo_items = RepositorioListaItems(sesion_temporal)

    lista = repo_listas.crear(codigo="MOTIVOS", nombre="Motivos", tipo_lista="MOTIVOS")
    item = repo_items.crear(lista_id=lista.id, valor=" Ajuste de inventario ")

    assert repo_listas.buscar_por_codigo("MOTIVOS") == lista
    assert item.valor_normalizado == "AJUSTE DE INVENTARIO"
    assert repo_items.buscar_en_lista(lista.id, "ajuste   de inventario") == item
    assert repo_items.listar_activos_por_lista(lista.id) == [item]

    with pytest.raises(IntegrityError):
        repo_items.crear(lista_id=lista.id, valor="AJUSTE DE INVENTARIO")

