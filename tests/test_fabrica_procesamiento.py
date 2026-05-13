"""Pruebas funcionales para la Fase 4.5 — factory e integracion del motor avanzado."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logica.lector_excel import LectorExcel
from reglas.motor_reglas_avanzado import MotorReglasAvanzado
from servicios.fabrica_procesamiento import (
    crear_lector_excel_con_fallback,
    crear_lector_excel_con_motor_avanzado,
)
from servicios.servicio_reglas import ServicioReglas

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
RUTA_REGLAS_JSON = RAIZ_PROYECTO / "configuracion" / "reglas_tipologia.json"
RUTA_MOVIMIENTOS = RAIZ_PROYECTO / "datos_prueba" / "movimientos_simulados.xlsx"

_CONFIG_BASE = {"hoja_por_defecto": "Movimientos"}


# ---------------------------------------------------------------------------
# Tests de la factory
# ---------------------------------------------------------------------------


def test_fabrica_crea_motor_avanzado_cuando_hay_reglas() -> None:
    """crear_lector_excel_con_motor_avanzado inyecta MotorReglasAvanzado cuando existen reglas."""
    from reglas.motor_reglas_avanzado import CondicionMotor, ReglaMotor

    reglas_stub = [
        ReglaMotor(
            id=1,
            nombre="stub",
            prioridad=10,
            tipologia_resultado="DEVOLUCIONES",
            condiciones=[CondicionMotor("TIPO_TRANSACCION", "IGUAL", ["RMA_RECEIPT"])],
        )
    ]

    with (
        patch("servicios.fabrica_procesamiento.obtener_reglas_motor_avanzado", return_value=reglas_stub),
        patch("servicios.fabrica_procesamiento.obtener_contexto_motor"),
    ):
        lector = crear_lector_excel_con_motor_avanzado(_CONFIG_BASE)

    assert isinstance(lector, LectorExcel)
    assert isinstance(lector._motor, MotorReglasAvanzado)


def test_fabrica_lanza_error_cuando_no_hay_reglas() -> None:
    """crear_lector_excel_con_motor_avanzado lanza RuntimeError si no hay reglas activas."""
    with patch("servicios.fabrica_procesamiento.obtener_reglas_motor_avanzado", return_value=[]):
        with pytest.raises(RuntimeError, match="No hay reglas activas"):
            crear_lector_excel_con_motor_avanzado(_CONFIG_BASE)


def test_fabrica_con_fallback_usa_legacy_si_falla_bd() -> None:
    """crear_lector_excel_con_fallback retorna LectorExcel legacy cuando la BD no esta disponible."""
    with patch(
        "servicios.fabrica_procesamiento.crear_lector_excel_con_motor_avanzado",
        side_effect=RuntimeError("Sin conexion a BD"),
    ):
        lector = crear_lector_excel_con_fallback(_CONFIG_BASE)

    assert isinstance(lector, LectorExcel)
    # Motor legacy es ClasificadorTipologia, no MotorReglasAvanzado
    assert not isinstance(lector._motor, MotorReglasAvanzado)


def test_fabrica_con_fallback_usa_avanzado_cuando_bd_disponible() -> None:
    """crear_lector_excel_con_fallback retorna el motor avanzado cuando todo funciona."""
    from reglas.motor_reglas_avanzado import CondicionMotor, ReglaMotor

    reglas_stub = [
        ReglaMotor(
            id=1,
            nombre="stub",
            prioridad=10,
            tipologia_resultado="DEVOLUCIONES",
            condiciones=[CondicionMotor("TIPO_TRANSACCION", "IGUAL", ["RMA_RECEIPT"])],
        )
    ]

    with (
        patch("servicios.fabrica_procesamiento.obtener_reglas_motor_avanzado", return_value=reglas_stub),
        patch("servicios.fabrica_procesamiento.obtener_contexto_motor"),
    ):
        lector = crear_lector_excel_con_fallback(_CONFIG_BASE)

    assert isinstance(lector._motor, MotorReglasAvanzado)


# ---------------------------------------------------------------------------
# Tests de integracion end-to-end (usando sesion_temporal del conftest)
# ---------------------------------------------------------------------------


def test_lector_avanzado_clasifica_movimientos_simulados(sesion_temporal: Session) -> None:
    """LectorExcel con MotorReglasAvanzado procesa movimientos_simulados.xlsx correctamente."""
    servicio = ServicioReglas(sesion_temporal)
    servicio.importar_desde_json(RUTA_REGLAS_JSON)

    motor = MotorReglasAvanzado(proveedor_reglas=servicio.obtener_reglas_avanzadas)
    lector = LectorExcel(configuracion=_CONFIG_BASE, motor_avanzado=motor)

    resultado = lector.cargar_archivo(RUTA_MOVIMIENTOS)

    assert resultado.exito
    assert resultado.estructura_valida
    assert resultado.resultado_preclasificacion is not None
    assert resultado.resultado_preclasificacion.cantidad_registros > 0
    assert resultado.resultado_preclasificacion.cantidad_clasificados > 0
    # Columnas de auditoria del motor avanzado presentes
    df = resultado.dataframe_procesado
    assert "TIPOLOGIA_PRELIMINAR" in df.columns
    assert "REGLA_APLICADA" in df.columns
    assert "REGLA_ID" in df.columns
    assert "EXPLICACION_REGLA" in df.columns


def test_motor_avanzado_produce_resultados_equivalentes_al_legacy(sesion_temporal: Session) -> None:
    """TIPOLOGIA_PRELIMINAR y REGLA_APLICADA son identicas entre motor avanzado y legado."""
    servicio = ServicioReglas(sesion_temporal)
    servicio.importar_desde_json(RUTA_REGLAS_JSON)

    lector_avanzado = LectorExcel(
        configuracion=_CONFIG_BASE,
        motor_avanzado=MotorReglasAvanzado(proveedor_reglas=servicio.obtener_reglas_avanzadas),
    )
    lector_legacy = LectorExcel(
        configuracion=_CONFIG_BASE,
        proveedor_reglas=servicio.obtener_reglas_para_motor,
    )

    resultado_avanzado = lector_avanzado.cargar_archivo(RUTA_MOVIMIENTOS)
    resultado_legacy = lector_legacy.cargar_archivo(RUTA_MOVIMIENTOS)

    assert resultado_avanzado.exito
    assert resultado_legacy.exito

    df_av = resultado_avanzado.dataframe_procesado
    df_leg = resultado_legacy.dataframe_procesado

    discrepancias_tipologia = (
        df_av["TIPOLOGIA_PRELIMINAR"] != df_leg["TIPOLOGIA_PRELIMINAR"]
    ).sum()
    discrepancias_regla = (
        df_av["REGLA_APLICADA"] != df_leg["REGLA_APLICADA"]
    ).sum()

    assert discrepancias_tipologia == 0, (
        f"El motor avanzado difiere del legacy en {discrepancias_tipologia} tipologias."
    )
    assert discrepancias_regla == 0, (
        f"El motor avanzado difiere del legacy en {discrepancias_regla} reglas aplicadas."
    )


def test_reglas_json_cubren_tipologias_requeridas_en_exportacion(sesion_temporal: Session) -> None:
    """El catalogo JSON clasifica las tipologias derivadas reportadas por negocio."""
    servicio = ServicioReglas(sesion_temporal)
    servicio.importar_reglas_json(json.loads(RUTA_REGLAS_JSON.read_text(encoding="utf-8")))

    dataframe = pd.DataFrame(
        [
            {
                "ORG_DESTINO": "16_FARMA_FARMACIA_INTERNA_CRS",
                "TIPO_TRANSACCION": "Sales order issue",
                "TIPO_ORIGEN": "Sales order",
                "ORIGEN": "PEDIDO MASIVO_CONSUMO.ORDER 123",
                "ARTICULO": "",
            },
            {
                "ORG_ORIGEN": "16_FARMA_FARMACIA_INTERNA_CRS",
                "ORG_DESTINO": "47_FARMA_ALMACEN_CIRUGIA_CRS",
                "TIPO_TRANSACCION": "Intransit Receipt",
                "TIPO_ORIGEN": "Inventory",
                "ARTICULO": "63192",
            },
        ]
    )

    resultado = MotorReglasAvanzado(
        proveedor_reglas=servicio.obtener_reglas_avanzadas,
    ).clasificar(dataframe)
    salida = resultado.dataframe_resultado

    assert salida["TIPOLOGIA_PRELIMINAR"].tolist() == [
        "DISPENSACION_AL_PACIENTE",
        "ENTRADAS_PRESTAMOS_INTERNOS",
    ]
    assert salida["TIPOLOGIA_FINAL"].tolist() == [
        "DISPENSACION_POR_CONSUMO",
        "ABASTECIMIENTO_DE_LIQUIDOS",
    ]
    assert salida["REGLA_DERIVADA_APLICADA"].tolist() == [
        "dispensacion_por_consumo",
        "abastecimiento_liquidos",
    ]
