"""Pruebas del repositorio de farmacias."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from persistencia.modelos_orm import TipoFarmacia
from repositorios.repositorio_farmacias import RepositorioFarmacias


def test_crud_busqueda_codigo_y_filtro_tipo(sesion_temporal: Session) -> None:
    tipo = sesion_temporal.scalar(select(TipoFarmacia).where(TipoFarmacia.codigo == "INTERNA"))
    assert tipo is not None
    repo = RepositorioFarmacias(sesion_temporal)

    farmacia = repo.crear(
        codigo="16",
        nombre_original="16_Farma Farmacia Interna CRS",
        tipo_farmacia_id=tipo.id,
        es_interna=True,
    )

    assert farmacia.nombre_normalizado == "16_FARMA FARMACIA INTERNA CRS"
    assert repo.obtener_por_codigo("16") == farmacia
    assert repo.buscar_por_codigo("16") == [farmacia]
    assert repo.listar_por_tipo("INTERNA") == [farmacia]

    repo.actualizar(farmacia.id, puede_prestar=True)
    assert farmacia.puede_prestar is True


def test_restriccion_unica_por_codigo(sesion_temporal: Session) -> None:
    tipo = sesion_temporal.scalar(select(TipoFarmacia).where(TipoFarmacia.codigo == "INTERNA"))
    assert tipo is not None
    repo = RepositorioFarmacias(sesion_temporal)

    repo.crear(codigo="16", nombre_original="Farmacia Norte", tipo_farmacia_id=tipo.id)

    with pytest.raises(IntegrityError):
        repo.crear(codigo="16", nombre_original="Farmacia Sur", tipo_farmacia_id=tipo.id)
