"""Pruebas del asistente operativo de novedades del archivo."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from logica.novedades_archivo import (
    agregar_motivo_probable_sin_clasificar,
    analizar_novedades_archivo,
    motivo_probable_sin_clasificar,
)


@dataclass
class FarmaciaConocida:
    id: int
    codigo: str
    puede_prestar: bool
    es_interna: bool = False
    es_externa: bool = False


def test_detecta_internas_externas_nuevas_y_conocidas() -> None:
    dataframe = pd.DataFrame(
        {
            "ORG_DESTINO": ["16_FARMA_INTERNA", "47_FARMA_CIRUGIA", "16_FARMA_INTERNA"],
            "ORG_ORIGEN": ["999_FARMA_EXTERNA_NUEVA", "16_FARMA_INTERNA", "47_FARMA_CIRUGIA"],
        }
    )
    conocidas = [FarmaciaConocida(1, "16_FARMA_INTERNA", True, es_interna=True)]

    novedades = analizar_novedades_archivo(dataframe, conocidas)

    assert novedades.internas_detectadas == ["16_FARMA_INTERNA", "47_FARMA_CIRUGIA"]
    assert novedades.externas_detectadas == ["999_FARMA_EXTERNA_NUEVA"]
    assert "999_FARMA_EXTERNA_NUEVA" in novedades.farmacias_nuevas
    assert "16_FARMA_INTERNA" in novedades.farmacias_conocidas
    assert [f.codigo for f in novedades.farmacias_pendientes] == ["47_FARMA_CIRUGIA", "999_FARMA_EXTERNA_NUEVA"]


def test_motivo_probable_org_origen_vacio() -> None:
    motivo = motivo_probable_sin_clasificar({"ORG_ORIGEN": "", "ORG_DESTINO": "16_FARMA"})

    assert motivo == "ORG_ORIGEN vacio."


def test_motivo_probable_org_destino_vacio() -> None:
    motivo = motivo_probable_sin_clasificar({"ORG_ORIGEN": "999_FARMA", "ORG_DESTINO": ""})

    assert motivo == "ORG_DESTINO vacio."


def test_motivo_probable_tipo_transaccion_no_contemplado() -> None:
    motivo = motivo_probable_sin_clasificar(
        {
            "ORG_ORIGEN": "16_FARMA",
            "ORG_DESTINO": "47_FARMA",
            "TIPO_TRANSACCION": "TRANSACCION_NUEVA",
        },
        farmacias_conocidas={"16_FARMA", "47_FARMA"},
        tipos_transaccion={"MISCELLANEOUS_RECEIPT"},
    )

    assert motivo == "TIPO_TRANSACCION no contemplado por reglas activas."


def test_agrega_motivo_probable_no_coincide() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "TIPOLOGIA_PRELIMINAR": "SIN_CLASIFICAR",
                "ORG_ORIGEN": "16_FARMA",
                "ORG_DESTINO": "47_FARMA",
                "TIPO_TRANSACCION": "MISCELLANEOUS_RECEIPT",
            }
        ]
    )

    resultado = agregar_motivo_probable_sin_clasificar(
        dataframe,
        farmacias_conocidas={"16_FARMA", "47_FARMA"},
        reglas_activas=[
            {"condiciones": {"TIPO_TRANSACCION": ["MISCELLANEOUS_RECEIPT"]}},
        ],
    )

    assert resultado.loc[0, "MOTIVO_PROBABLE"] == "No coincide con ninguna regla activa."
