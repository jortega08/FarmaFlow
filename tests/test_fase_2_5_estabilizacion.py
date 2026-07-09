"""Pruebas de estabilizacion tecnica de la Fase 2.5."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dto.ejecucion_dto import EjecucionCrearDTO, EjecucionFinalizarDTO
from dto.regla_dto import ReglaClasificacionActualizarDTO
from logica.clasificador_tipologia import ClasificadorTipologia
from logica.detector_farmacias import DetectorFarmacias
from logica.exportador_excel import ExportadorExcel
from logica.generador_resumen import generar_estructuras_exportacion
from logica.lector_excel import LectorExcel
from logica.normalizador_datos import NormalizadorDatos
from logica.validador_estructura import ValidadorEstructura
from persistencia.modelos_orm import CondicionRegla, ReglaClasificacion
from servicios.servicio_ejecuciones import ServicioEjecuciones
from servicios.servicio_reglas import ServicioReglas
from utilidades.rutas import cargar_json
from utilidades.texto import normalizar_nombre_columna, normalizar_texto, normalizar_valor_por_campo


RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
RUTA_REGLAS_JSON = RAIZ_PROYECTO / "configuracion" / "reglas_tipologia.json"
RUTA_MOVIMIENTOS = RAIZ_PROYECTO / "datos_prueba" / "movimientos_simulados.xlsx"


def _preparar_dataframe_clasificacion() -> pd.DataFrame:
    libro = pd.ExcelFile(RUTA_MOVIMIENTOS)
    hoja = "Movimientos" if "Movimientos" in libro.sheet_names else libro.sheet_names[0]
    dataframe = pd.read_excel(RUTA_MOVIMIENTOS, sheet_name=hoja)

    resultado_validacion = ValidadorEstructura().validar([str(columna) for columna in dataframe.columns])
    assert resultado_validacion.exito
    assert resultado_validacion.estructura_valida

    dataframe_normalizado = NormalizadorDatos().normalizar(dataframe, resultado_validacion.columnas_mapeadas)
    dataframe_con_farmacias, _ = DetectorFarmacias().detectar(dataframe_normalizado)
    return dataframe_con_farmacias


def _contar_reglas(sesion: Session) -> int:
    return sesion.scalar(select(func.count()).select_from(ReglaClasificacion)) or 0


def _contar_condiciones(sesion: Session) -> int:
    return sesion.scalar(select(func.count()).select_from(CondicionRegla)) or 0


def test_equivalencia_clasificacion_json_vs_sqlite(sesion_temporal: Session) -> None:
    dataframe = _preparar_dataframe_clasificacion()
    resultado_json = ClasificadorTipologia(ruta_reglas=RUTA_REGLAS_JSON).clasificar(dataframe)

    servicio_reglas = ServicioReglas(sesion_temporal)
    servicio_reglas.importar_desde_json(RUTA_REGLAS_JSON)
    resultado_sqlite = ClasificadorTipologia(
        proveedor_reglas=servicio_reglas.obtener_reglas_para_motor,
    ).clasificar(dataframe)

    columnas = ["TIPOLOGIA_PRELIMINAR", "REGLA_APLICADA"]
    diferencias: list[dict[str, object]] = []
    for indice in resultado_json.dataframe_resultado.index:
        fila_json = resultado_json.dataframe_resultado.loc[indice, columnas]
        fila_sqlite = resultado_sqlite.dataframe_resultado.loc[indice, columnas]
        if fila_json.to_dict() != fila_sqlite.to_dict():
            diferencias.append(
                {
                    "fila": int(indice),
                    "json": fila_json.to_dict(),
                    "sqlite": fila_sqlite.to_dict(),
                }
            )

    assert not diferencias, f"Primeras discrepancias JSON vs SQLite: {diferencias[:10]}"


def test_seed_reglas_idempotente_no_duplica_ni_modifica(sesion_temporal: Session) -> None:
    servicio = ServicioReglas(sesion_temporal)

    creadas_primera_vez = servicio.importar_desde_json(RUTA_REGLAS_JSON)
    reglas_primera_vez = _contar_reglas(sesion_temporal)
    condiciones_primera_vez = _contar_condiciones(sesion_temporal)

    regla_modificada = servicio.actualizar_regla(
        creadas_primera_vez[0].id,
        ReglaClasificacionActualizarDTO(descripcion="Descripcion preservada por idempotencia."),
    )
    creadas_segunda_vez = servicio.importar_desde_json(RUTA_REGLAS_JSON)
    regla_luego_de_seed = servicio.obtener_regla(regla_modificada.id)

    assert len(creadas_primera_vez) == len(cargar_json(RUTA_REGLAS_JSON))
    assert creadas_segunda_vez == []
    assert _contar_reglas(sesion_temporal) == reglas_primera_vez
    assert _contar_condiciones(sesion_temporal) == condiciones_primera_vez
    assert regla_luego_de_seed.descripcion == "Descripcion preservada por idempotencia."


def test_integridad_de_reglas_migradas_y_comodin(sesion_temporal: Session) -> None:
    reglas_json = cargar_json(RUTA_REGLAS_JSON)
    servicio = ServicioReglas(sesion_temporal)
    servicio.importar_desde_json(RUTA_REGLAS_JSON)

    reglas_persistidas = {regla.nombre: regla for regla in servicio.listar_reglas()}
    reglas_motor = {regla["nombre_regla"]: regla for regla in servicio.obtener_reglas_para_motor()}

    assert len(reglas_persistidas) == len(reglas_json)
    for regla_json in reglas_json:
        nombre = str(regla_json["nombre_regla"])
        assert nombre in reglas_persistidas
        assert nombre in reglas_motor
        assert len(reglas_persistidas[nombre].condiciones) == len(regla_json["condiciones"])

        for campo, valores in regla_json["condiciones"].items():
            campo_normalizado = normalizar_nombre_columna(campo)
            if isinstance(valores, dict):
                operador = normalizar_nombre_columna(valores.get("operador", "EN"))
                valor_json = valores.get("valores", valores.get("valor", valores.get("valor_texto", [])))
                valor_lista = valor_json if isinstance(valor_json, list) else [valor_json]
                valores_esperados = [
                    normalizar_valor_por_campo(campo_normalizado, valor)
                    for valor in valor_lista
                    if normalizar_valor_por_campo(campo_normalizado, valor)
                ]
                if operador in {"VACIO", "NO_VACIO"}:
                    assert reglas_motor[nombre]["condiciones"][campo_normalizado] == {
                        "operador": operador,
                        "valores": [],
                    }
                elif operador in {"EN", "IGUAL"}:
                    assert reglas_motor[nombre]["condiciones"][campo_normalizado] == valores_esperados
                else:
                    assert reglas_motor[nombre]["condiciones"][campo_normalizado] == {
                        "operador": operador,
                        "valores": valores_esperados,
                    }
                continue

            valores_esperados = [normalizar_valor_por_campo(campo_normalizado, valor) for valor in valores]
            assert reglas_motor[nombre]["condiciones"][campo_normalizado] == valores_esperados

    servicio.importar_reglas_json(
        [
            {
                "nombre_regla": "comodin_fase_2_5",
                "prioridad": 1,
                "condiciones": {
                    "TIPO_TRANSACCION": ["CYCLE_COUNT_ADJUST"],
                    "MOTIVO": ["*"],
                },
                "resultado": "CONTEO_CICLICO",
            }
        ]
    )
    regla_comodin = {
        regla["nombre_regla"]: regla
        for regla in servicio.obtener_reglas_para_motor()
    }["comodin_fase_2_5"]
    assert regla_comodin["condiciones"]["MOTIVO"] == ["*"]

    resultado = ClasificadorTipologia(
        proveedor_reglas=servicio.obtener_reglas_para_motor,
    ).clasificar(pd.DataFrame([{"TIPO_TRANSACCION": "CYCLE_COUNT_ADJUST", "MOTIVO": "CUALQUIER"}]))
    assert resultado.dataframe_resultado.loc[0, "TIPOLOGIA_PRELIMINAR"] == "CONTEO_CICLICO"
    assert resultado.dataframe_resultado.loc[0, "REGLA_APLICADA"] == "comodin_fase_2_5"


def test_end_to_end_procesa_exporta_y_actualiza_ejecucion(sesion_temporal: Session) -> None:
    servicio_reglas = ServicioReglas(sesion_temporal)
    servicio_reglas.importar_desde_json(RUTA_REGLAS_JSON)
    lector = LectorExcel(
        configuracion={"hoja_por_defecto": "Movimientos"},
        proveedor_reglas=servicio_reglas.obtener_reglas_para_motor,
    )
    servicio_ejecuciones = ServicioEjecuciones(sesion_temporal)

    ejecucion_iniciada = servicio_ejecuciones.registrar_inicio(
        EjecucionCrearDTO(
            archivo_nombre=RUTA_MOVIMIENTOS.name,
            archivo_ruta=str(RUTA_MOVIMIENTOS),
            hoja="Movimientos",
        )
    )
    resultado_carga = lector.cargar_archivo(RUTA_MOVIMIENTOS)
    assert resultado_carga.exito
    assert resultado_carga.estructura_valida

    ejecucion_clasificada = servicio_ejecuciones.finalizar_ejecucion(
        ejecucion_iniciada.id,
        EjecucionFinalizarDTO(
            estado="CLASIFICADA",
            total_registros=resultado_carga.cantidad_filas,
            total_columnas=resultado_carga.cantidad_columnas,
            total_clasificados=resultado_carga.resultado_preclasificacion.cantidad_clasificados,
            total_sin_clasificar=resultado_carga.resultado_preclasificacion.cantidad_sin_clasificar,
            mensaje=resultado_carga.mensaje,
        ),
    )
    assert servicio_ejecuciones.listar_recientes(limite=1) == [ejecucion_clasificada]

    estructuras = generar_estructuras_exportacion(
        dataframe_original=resultado_carga.dataframe,
        dataframe_procesado=resultado_carga.dataframe_procesado,
    )
    with tempfile.TemporaryDirectory() as carpeta_temporal:
        resultado_exportacion = ExportadorExcel().exportar(
            dataframe_original=resultado_carga.dataframe,
            detalle_clasificado=estructuras["detalle_clasificado"],
            resumen_tipologia=estructuras["resumen_tipologia"],
            resumen_farmacia=estructuras["resumen_farmacia"],
            cruce_tipologia_farmacia=estructuras["cruce_tipologia_farmacia"],
            sin_clasificar=estructuras["sin_clasificar"],
            ruta_salida=Path(carpeta_temporal),
            nombre_base_archivo=RUTA_MOVIMIENTOS.name,
        )
        assert resultado_exportacion.exito
        assert Path(resultado_exportacion.ruta_salida).exists()

    ejecucion_exportada = servicio_ejecuciones.finalizar_ejecucion(
        ejecucion_iniciada.id,
        EjecucionFinalizarDTO(
            estado="EXPORTADA",
            total_registros=resultado_carga.cantidad_filas,
            total_columnas=resultado_carga.cantidad_columnas,
            total_clasificados=resultado_carga.resultado_preclasificacion.cantidad_clasificados,
            total_sin_clasificar=resultado_carga.resultado_preclasificacion.cantidad_sin_clasificar,
            mensaje=resultado_exportacion.mensaje,
        ),
    )

    assert ejecucion_exportada.id == ejecucion_iniciada.id
    assert ejecucion_exportada.estado == "EXPORTADA"
    assert servicio_ejecuciones.listar_recientes(limite=1) == [ejecucion_exportada]
