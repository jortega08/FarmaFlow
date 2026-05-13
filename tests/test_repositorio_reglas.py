"""Pruebas del repositorio de reglas."""

from __future__ import annotations

from sqlalchemy.orm import Session

from repositorios.repositorio_reglas import RepositorioReglas


def test_crear_regla_con_condiciones_y_listar_activas(sesion_temporal: Session) -> None:
    repo = RepositorioReglas(sesion_temporal)

    regla_baja = repo.crear(nombre="regla_baja", tipologia_resultado="BAJA", prioridad=20)
    regla_alta = repo.crear_con_condiciones(
        nombre="regla_alta",
        tipologia_resultado="ALTA",
        prioridad=5,
        condiciones=[
            {"campo": "Tipo transaccion", "operador": "IGUAL", "valor_texto": "RMA_RECEIPT"},
            {"campo": "Motivo", "operador": "CONTIENE", "valor_texto": "DEVOLUCION"},
        ],
    )
    repo.crear(nombre="regla_inactiva", tipologia_resultado="NO", prioridad=1, activa=False)

    activas = repo.listar_activas_ordenadas_por_prioridad()

    assert activas == [regla_alta, regla_baja]
    assert [condicion.campo for condicion in regla_alta.condiciones] == ["TIPO_TRANSACCION", "MOTIVO"]
    assert [condicion.orden for condicion in regla_alta.condiciones] == [0, 1]

