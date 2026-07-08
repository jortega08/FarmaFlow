from __future__ import annotations

import pandas as pd

from reglas.evaluador_condiciones import ContextoMotor, EvaluadorCondiciones


def test_no_en_columna_identifica_org_origen_externa_frente_a_org_destino() -> None:
    df = pd.DataFrame(
        {
            "ORG_ORIGEN": [
                "16_FARMA_FARMACIA_INTERNA_CRS",
                "20_FARMA_CLINICA_COUNTRY",
                "47_FARMA_ALMACEN_CIRUGIA_CRS",
                "",
            ],
            "ORG_DESTINO": [
                "16_FARMA_FARMACIA_INTERNA_CRS",
                "16_FARMA_FARMACIA_INTERNA_CRS",
                "47_FARMA_ALMACEN_CIRUGIA_CRS",
                "16_FARMA_FARMACIA_INTERNA_CRS",
            ],
        }
    )

    mascara = EvaluadorCondiciones().generar_mascara(
        df=df,
        campo="ORG_ORIGEN",
        operador="NO_EN_COLUMNA",
        valores=["ORG_DESTINO"],
        lista_id=None,
        atributo_farmacia=None,
        contexto=ContextoMotor(),
    )

    assert mascara.tolist() == [False, True, False, False]


def test_en_columna_identifica_org_origen_interna_frente_a_org_destino() -> None:
    df = pd.DataFrame(
        {
            "ORG_ORIGEN": [
                "16_FARMA_FARMACIA_INTERNA_CRS",
                "20_FARMA_CLINICA_COUNTRY",
                "47_FARMA_ALMACEN_CIRUGIA_CRS",
            ],
            "ORG_DESTINO": [
                "16_FARMA_FARMACIA_INTERNA_CRS",
                "16_FARMA_FARMACIA_INTERNA_CRS",
                "47_FARMA_ALMACEN_CIRUGIA_CRS",
            ],
        }
    )

    mascara = EvaluadorCondiciones().generar_mascara(
        df=df,
        campo="ORG_ORIGEN",
        operador="EN_COLUMNA",
        valores=["ORG_DESTINO"],
        lista_id=None,
        atributo_farmacia=None,
        contexto=ContextoMotor(),
    )

    assert mascara.tolist() == [True, False, True]
