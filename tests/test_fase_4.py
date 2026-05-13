"""Pruebas funcionales de la Fase 4: motor de reglas avanzado."""

from __future__ import annotations

import pandas as pd

from logica.clasificador_tipologia import ClasificadorTipologia
from reglas.evaluador_condiciones import ContextoMotor, EvaluadorCondiciones, FarmaciaAtributos
from reglas.motor_reglas_avanzado import CondicionMotor, MotorReglasAvanzado, ReglaMotor


def _mascara(
    df: pd.DataFrame,
    campo: str,
    operador: str,
    valores: list[str] | None = None,
    *,
    lista_id: int | None = None,
    atributo_farmacia: str | None = None,
    contexto: ContextoMotor | None = None,
) -> list[bool]:
    resultado = EvaluadorCondiciones().generar_mascara(
        df=df,
        campo=campo,
        operador=operador,
        valores=valores or [],
        lista_id=lista_id,
        atributo_farmacia=atributo_farmacia,
        contexto=contexto or ContextoMotor(),
    )
    return [bool(valor) for valor in resultado.tolist()]


def test_operador_igual_exacto() -> None:
    df = pd.DataFrame({"TIPO_TRANSACCION": ["RMA_RECEIPT", "SALES_ORDER_ISSUE", ""]})

    assert _mascara(df, "TIPO_TRANSACCION", "IGUAL", ["RMA_RECEIPT"]) == [True, False, False]
    assert _mascara(df, "TIPO_TRANSACCION", "EN", ["RMA_RECEIPT"]) == [True, False, False]


def test_operador_igual_normaliza_codigos_con_espacios() -> None:
    df = pd.DataFrame({"TIPO_TRANSACCION": ["Account alias receipt", "Sales order issue"]})

    assert _mascara(df, "TIPO_TRANSACCION", "IGUAL", ["ACCOUNT_ALIAS_RECEIPT"]) == [True, False]


def test_operador_igual_comodin() -> None:
    df = pd.DataFrame({"MOTIVO": ["AJUSTE", "", None]})

    assert _mascara(df, "MOTIVO", "EN", ["*"]) == [True, True, True]


def test_operador_distinto() -> None:
    df = pd.DataFrame({"TIPO": ["A", "B", "C"]})

    assert _mascara(df, "TIPO", "DISTINTO", ["B"]) == [True, False, True]


def test_operador_contiene() -> None:
    df = pd.DataFrame({"ORIGEN": ["MASIVO_CONSUMO.ORDER", "AJUSTE", "devolucion order"]})

    assert _mascara(df, "ORIGEN", "CONTIENE", ["ORDER"]) == [True, False, True]


def test_operador_no_contiene() -> None:
    df = pd.DataFrame({"ORIGEN": ["MASIVO_CONSUMO.ORDER", "AJUSTE", ""]})

    assert _mascara(df, "ORIGEN", "NO_CONTIENE", ["ORDER"]) == [False, True, True]


def test_operador_empieza_por() -> None:
    df = pd.DataFrame({"SUBINVENTARIO": ["FARM_DISP", "DISP_FARM", "FARM_AJUSTE"]})

    assert _mascara(df, "SUBINVENTARIO", "EMPIEZA_POR", ["FARM"]) == [True, False, True]


def test_operador_termina_en() -> None:
    df = pd.DataFrame({"SUBINVENTARIO": ["DISP_FARM", "FARM_DISP", "AJUSTE_FARM"]})

    assert _mascara(df, "SUBINVENTARIO", "TERMINA_EN", ["FARM"]) == [True, False, True]


def test_operador_vacio_no_vacio() -> None:
    df = pd.DataFrame({"MOTIVO": ["", None, "  ", "AJUSTE"]})

    assert _mascara(df, "MOTIVO", "VACIO") == [True, True, True, False]
    assert _mascara(df, "MOTIVO", "NO_VACIO") == [False, False, False, True]
    assert _mascara(df, "COLUMNA_AUSENTE", "VACIO") == [True, True, True, True]


def test_operador_en_lista() -> None:
    df = pd.DataFrame({"ARTICULO": ["ITEM_A", "ITEM_B", "ITEM_C"]})
    contexto = ContextoMotor(listas={7: frozenset({"ITEM_A", "ITEM_C"})})

    assert _mascara(df, "ARTICULO", "EN_LISTA", lista_id=7, contexto=contexto) == [True, False, True]


def test_operador_no_en_lista() -> None:
    df = pd.DataFrame({"ARTICULO": ["ITEM_A", "ITEM_B", "ITEM_C"]})
    contexto = ContextoMotor(listas={7: frozenset({"ITEM_A", "ITEM_C"})})

    assert _mascara(df, "ARTICULO", "NO_EN_LISTA", lista_id=7, contexto=contexto) == [False, True, False]


def test_operador_farmacia_puede_prestar() -> None:
    df = pd.DataFrame({"ORG_DESTINO": ["FARMACIA_A", "FARMACIA_B", "SIN_CATALOGO"]})
    contexto = ContextoMotor(
        farmacias={
            "FARMACIA_A": FarmaciaAtributos("INTERNA", True, True, False),
            "FARMACIA_B": FarmaciaAtributos("EXTERNA", False, False, True),
        }
    )

    assert _mascara(df, "ORG_DESTINO", "FARMACIA_PUEDE_PRESTAR", contexto=contexto) == [True, False, False]
    assert _mascara(df, "ORG_DESTINO", "FARMACIA_NO_PUEDE_PRESTAR", contexto=contexto) == [False, True, True]


def test_operador_farmacia_es_tipo() -> None:
    df = pd.DataFrame({"ORG_DESTINO": ["FARMACIA_A", "FARMACIA_B", "SIN_CATALOGO"]})
    contexto = ContextoMotor(
        farmacias={
            "FARMACIA_A": FarmaciaAtributos("INTERNA", True, True, False),
            "FARMACIA_B": FarmaciaAtributos("EXTERNA", False, False, True),
        }
    )

    assert _mascara(
        df,
        "ORG_DESTINO",
        "FARMACIA_ES_TIPO",
        atributo_farmacia="INTERNA",
        contexto=contexto,
    ) == [True, False, False]
    assert _mascara(
        df,
        "ORG_DESTINO",
        "FARMACIA_NO_ES_TIPO",
        atributo_farmacia="INTERNA",
        contexto=contexto,
    ) == [False, True, True]


def test_motor_clasificacion_vectorizada(monkeypatch) -> None:
    def bloquear_iterrows(*_args, **_kwargs):
        raise AssertionError("El motor avanzado no debe usar iterrows")

    monkeypatch.setattr(pd.DataFrame, "iterrows", bloquear_iterrows)

    df = pd.DataFrame(
        {
            "TIPO_TRANSACCION": ["RMA_RECEIPT"] * 50 + [""] * 50,
            "ORIGEN": [""] * 50 + ["MASIVO_CONSUMO.ORDER"] * 30 + [""] * 20,
            "SUBINVENTARIO": [""] * 80 + ["AJUSTE"] * 20,
        }
    )
    reglas = [
        ReglaMotor(
            id=1,
            nombre="devoluciones",
            prioridad=10,
            tipologia_resultado="DEVOLUCIONES",
            condiciones=[CondicionMotor("TIPO_TRANSACCION", "IGUAL", ["RMA_RECEIPT"])],
        ),
        ReglaMotor(
            id=2,
            nombre="dispensacion",
            prioridad=20,
            tipologia_resultado="DISPENSACION",
            condiciones=[CondicionMotor("ORIGEN", "CONTIENE", ["ORDER"])],
        ),
        ReglaMotor(
            id=3,
            nombre="ajustes",
            prioridad=30,
            tipologia_resultado="AJUSTES",
            condiciones=[CondicionMotor("SUBINVENTARIO", "EN_LISTA", [], lista_id=99)],
        ),
    ]
    contexto = ContextoMotor(listas={99: frozenset({"AJUSTE"})})
    motor = MotorReglasAvanzado(lambda: reglas, lambda: contexto)

    resultado = motor.clasificar(df)

    assert resultado.cantidad_registros == 100
    assert resultado.cantidad_clasificados == 100
    assert resultado.tipologias_detectadas["DEVOLUCIONES"] == 50
    assert resultado.tipologias_detectadas["DISPENSACION"] == 30
    assert resultado.tipologias_detectadas["AJUSTES"] == 20


def test_motor_primera_regla_gana() -> None:
    df = pd.DataFrame({"TIPO_TRANSACCION": ["RMA_RECEIPT"]})
    reglas = [
        ReglaMotor(
            id=1,
            nombre="prioritaria",
            prioridad=1,
            tipologia_resultado="TIPO_A",
            condiciones=[CondicionMotor("TIPO_TRANSACCION", "EN", ["*"])],
        ),
        ReglaMotor(
            id=2,
            nombre="secundaria",
            prioridad=2,
            tipologia_resultado="TIPO_B",
            condiciones=[CondicionMotor("TIPO_TRANSACCION", "IGUAL", ["RMA_RECEIPT"])],
        ),
    ]

    resultado = MotorReglasAvanzado(lambda: reglas).clasificar(df)

    assert resultado.dataframe_resultado.loc[0, "TIPOLOGIA_PRELIMINAR"] == "TIPO_A"
    assert resultado.dataframe_resultado.loc[0, "REGLA_APLICADA"] == "prioritaria"
    assert resultado.dataframe_resultado.loc[0, "REGLA_ID"] == 1


def test_motor_aplica_reglas_derivadas_sobre_tipologia_preliminar() -> None:
    df = pd.DataFrame(
        {
            "TIPO_TRANSACCION": ["Sales order issue", "Intransit Receipt"],
            "TIPO_ORIGEN": ["Sales order", "Inventory"],
            "ORG_DESTINO": ["16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA_ALMACEN_CIRUGIA_CRS"],
            "ORG_ORIGEN": ["", "16_FARMA_FARMACIA_INTERNA_CRS"],
            "ORIGEN": ["CONSUMO", ""],
            "ARTICULO": ["", "21817"],
        }
    )
    reglas = [
        ReglaMotor(
            id=1,
            nombre="dispensacion",
            prioridad=10,
            tipologia_resultado="DISPENSACION_AL_PACIENTE",
            condiciones=[
                CondicionMotor("TIPO_TRANSACCION", "IGUAL", ["SALES_ORDER_ISSUE"]),
                CondicionMotor("TIPO_ORIGEN", "IGUAL", ["SALES_ORDER"]),
            ],
        ),
        ReglaMotor(
            id=2,
            nombre="entradas_prestamos_internos",
            prioridad=10,
            tipologia_resultado="ENTRADAS_PRESTAMOS_INTERNOS",
            condiciones=[
                CondicionMotor("TIPO_TRANSACCION", "IGUAL", ["INTRANSIT_RECEIPT"]),
                CondicionMotor("TIPO_ORIGEN", "IGUAL", ["INVENTORY"]),
            ],
        ),
        ReglaMotor(
            id=3,
            nombre="dispensacion_consumo",
            prioridad=999,
            tipologia_resultado="DISPENSACION_CONSUMO",
            condiciones=[
                CondicionMotor("TIPOLOGIA", "IGUAL", ["DISPENSACION_AL_PACIENTE"]),
                CondicionMotor("ORIGEN", "IGUAL", ["CONSUMO"]),
            ],
        ),
        ReglaMotor(
            id=4,
            nombre="entradas_mce",
            prioridad=999,
            tipologia_resultado="ENTRADAS_MCE",
            condiciones=[
                CondicionMotor("TIPOLOGIA", "IGUAL", ["ENTRADAS_PRESTAMOS_INTERNOS"]),
                CondicionMotor("ARTICULO", "IGUAL", ["21817"]),
                CondicionMotor("ORG_DESTINO", "IGUAL", ["47_FARMA_ALMACEN_CIRUGIA_CRS"]),
            ],
        ),
    ]

    resultado = MotorReglasAvanzado(lambda: reglas).clasificar(df)
    salida = resultado.dataframe_resultado

    assert salida["TIPOLOGIA_PRELIMINAR"].tolist() == [
        "DISPENSACION_AL_PACIENTE",
        "ENTRADAS_PRESTAMOS_INTERNOS",
    ]
    assert salida["TIPOLOGIA_FINAL"].tolist() == ["DISPENSACION_CONSUMO", "ENTRADAS_MCE"]
    assert salida["REGLA_DERIVADA_APLICADA"].tolist() == ["dispensacion_consumo", "entradas_mce"]


def test_motor_columnas_auditoria() -> None:
    df = pd.DataFrame({"TIPO_TRANSACCION": ["RMA_RECEIPT"]})
    reglas = [
        ReglaMotor(
            id=123,
            nombre="devoluciones",
            prioridad=10,
            tipologia_resultado="DEVOLUCIONES",
            condiciones=[CondicionMotor("TIPO_TRANSACCION", "IGUAL", ["RMA_RECEIPT"])],
        )
    ]

    resultado = MotorReglasAvanzado(lambda: reglas).clasificar(df)
    columnas = set(resultado.dataframe_resultado.columns)

    assert {"TIPOLOGIA_PRELIMINAR", "REGLA_APLICADA", "REGLA_ID", "EXPLICACION_REGLA"} <= columnas
    assert resultado.dataframe_resultado.loc[0, "REGLA_ID"] == 123
    assert "devoluciones" in resultado.dataframe_resultado.loc[0, "EXPLICACION_REGLA"]


def test_motor_compatibilidad_legado() -> None:
    reglas_legacy = [
        {
            "nombre_regla": "devolucion_general",
            "prioridad": 1,
            "condiciones": {"TIPO_TRANSACCION": ["RMA_RECEIPT"], "MOTIVO": ["*"]},
            "resultado": "DEVOLUCIONES",
        },
        {
            "nombre_regla": "dispensacion",
            "prioridad": 2,
            "condiciones": {"TIPO_TRANSACCION": ["SALES_ORDER_ISSUE"]},
            "resultado": "DISPENSACION",
        },
    ]
    df = pd.DataFrame(
        {
            "TIPO_TRANSACCION": ["RMA_RECEIPT", "SALES_ORDER_ISSUE", "AJUSTE"],
            "MOTIVO": ["CUALQUIERA", "", "REVISION"],
        }
    )

    legacy = ClasificadorTipologia(proveedor_reglas=lambda: reglas_legacy).clasificar(df)
    avanzado = MotorReglasAvanzado.desde_proveedor_simple(lambda: reglas_legacy).clasificar(df)

    assert avanzado.dataframe_resultado["TIPOLOGIA_PRELIMINAR"].tolist() == legacy.dataframe_resultado[
        "TIPOLOGIA_PRELIMINAR"
    ].tolist()
    assert avanzado.dataframe_resultado["REGLA_APLICADA"].tolist() == legacy.dataframe_resultado[
        "REGLA_APLICADA"
    ].tolist()
