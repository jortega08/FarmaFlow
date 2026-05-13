"""Pruebas de modelos ORM y restricciones principales."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from persistencia.modelos_orm import (
    Clinica,
    ClinicaFarmacia,
    CondicionRegla,
    EjecucionProceso,
    Farmacia,
    ItemLista,
    ListaConfigurable,
    ReglaClasificacion,
    TipoFarmacia,
)


def test_modelos_guardan_entidades_relacionadas(sesion_temporal: Session) -> None:
    tipo = sesion_temporal.scalar(select(TipoFarmacia).where(TipoFarmacia.codigo == "INTERNA"))
    assert tipo is not None

    clinica = Clinica(nombre="Cruz Roja", nombre_normalizado="CRUZ ROJA")
    farmacia = Farmacia(
        codigo="16",
        nombre_original="16_Farma Interna CRS",
        nombre_normalizado="16_FARMA INTERNA CRS",
        tipo_farmacia=tipo,
        puede_prestar=True,
        es_interna=True,
    )
    relacion = ClinicaFarmacia(clinica=clinica, farmacia=farmacia, relacion="PRINCIPAL")
    lista = ListaConfigurable(codigo="MOTIVOS", nombre="Motivos", tipo_lista="MOTIVOS")
    item = ItemLista(lista=lista, valor="Ajuste", valor_normalizado="AJUSTE")
    regla = ReglaClasificacion(
        nombre="regla_ajustes",
        tipologia_resultado="AJUSTES",
        prioridad=10,
        origen="SISTEMA",
    )
    condicion = CondicionRegla(regla=regla, campo="MOTIVO", operador="IGUAL", valor_texto="AJUSTE", orden=1)
    ejecucion = EjecucionProceso(
        clinica=clinica,
        archivo_nombre="movimientos.xlsx",
        estado="INICIADA",
    )

    sesion_temporal.add_all([relacion, item, condicion, ejecucion])
    sesion_temporal.flush()

    assert clinica.id is not None
    assert farmacia.id is not None
    assert relacion.id is not None
    assert lista.items[0].valor_normalizado == "AJUSTE"
    assert regla.condiciones[0].campo == "MOTIVO"
    assert ejecucion.clinica.nombre == "Cruz Roja"


def test_restricciones_unique_y_fk(sesion_temporal: Session) -> None:
    sesion_temporal.add(TipoFarmacia(codigo="INTERNA", nombre="Duplicado"))
    with pytest.raises(IntegrityError):
        sesion_temporal.flush()
    sesion_temporal.rollback()

    sesion_temporal.add(
        Farmacia(
            codigo="SIN_TIPO",
            nombre_original="Farmacia sin tipo",
            nombre_normalizado="FARMACIA SIN TIPO",
            tipo_farmacia_id=999999,
        )
    )
    with pytest.raises(IntegrityError):
        sesion_temporal.flush()

