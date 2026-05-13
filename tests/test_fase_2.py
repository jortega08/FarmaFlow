"""Pruebas basicas de la Fase 2 para estructura Oracle."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logica.clasificador_tipologia import ClasificadorTipologia
from logica.detector_farmacias import DetectorFarmacias
from logica.normalizador_datos import NormalizadorDatos
from logica.validador_estructura import ValidadorEstructura
from utilidades.texto import es_valor_comodin, normalizar_codigo, normalizar_nombre_columna, normalizar_texto


class PruebasFaseDos(unittest.TestCase):
    """Cobertura funcional minima para la nueva logica de preparacion."""

    def setUp(self) -> None:
        self.validador = ValidadorEstructura()
        self.normalizador = NormalizadorDatos()
        self.detector = DetectorFarmacias()
        self.clasificador = ClasificadorTipologia()

    def test_validacion_con_columnas_correctas(self) -> None:
        columnas = [
            "SUBINVENTARIO",
            "ORG_ORIGEN",
            "ORG_DESTINO",
            "TIPO_TRANSACCION",
            "TIPO_ORIGEN",
            "ORIGEN",
            "MOTIVO",
        ]

        resultado = self.validador.validar(columnas)

        self.assertTrue(resultado.exito)
        self.assertTrue(resultado.estructura_valida)
        self.assertEqual(resultado.columnas_faltantes, [])

    def test_validacion_con_columnas_faltantes(self) -> None:
        columnas = [
            "SUBINVENTARIO",
            "ORG_DESTINO",
            "TIPO_TRANSACCION",
        ]

        resultado = self.validador.validar(columnas)

        self.assertTrue(resultado.exito)
        self.assertFalse(resultado.estructura_valida)
        self.assertIn("ORG_ORIGEN", resultado.columnas_faltantes)

    def test_mapeo_por_alias(self) -> None:
        columnas = [
            "Sub Inventario",
            "ORG DESTINO",
            "ORG ORIGEN",
            "TIPO TRANSACCION",
            "TIPO ORIGEN",
            "ORIGEN",
            "MOTIVO",
        ]

        resultado = self.validador.validar(columnas)

        self.assertTrue(resultado.estructura_valida)
        self.assertEqual(resultado.columnas_mapeadas["SUBINVENTARIO"], "Sub Inventario")
        self.assertEqual(resultado.columnas_mapeadas["ORG_DESTINO"], "ORG DESTINO")

    def test_normalizacion_de_texto_y_columna(self) -> None:
        self.assertEqual(normalizar_texto("  tipología  con   acento "), "TIPOLOGIA CON ACENTO")
        self.assertEqual(normalizar_nombre_columna(" Tipo transacción "), "TIPO_TRANSACCION")
        self.assertEqual(normalizar_codigo("Account alias receipt"), "ACCOUNT_ALIAS_RECEIPT")
        self.assertEqual(normalizar_codigo("ACCOUNT_ALIAS_RECEIPT"), "ACCOUNT_ALIAS_RECEIPT")
        self.assertTrue(es_valor_comodin("*"))

    def test_detector_preliminar_de_farmacia(self) -> None:
        dataframe = pd.DataFrame(
            [
                {"ORG_DESTINO": "16_FARMA_FARMACIA_INTERNA_CRS", "ORG_ORIGEN": ""},
                {"ORG_DESTINO": "", "ORG_ORIGEN": "47_FARM_ALMACEN_CENTRAL"},
                {"ORG_DESTINO": "BODEGA_GENERAL", "ORG_ORIGEN": "DISTRIBUCION"},
            ]
        )

        dataframe_resultado, farmacias = self.detector.detectar(dataframe)

        self.assertEqual(dataframe_resultado.loc[0, "FARMACIA_DETECTADA"], "16_FARMA_FARMACIA_INTERNA_CRS")
        self.assertEqual(dataframe_resultado.loc[1, "FARMACIA_DETECTADA"], "47_FARM_ALMACEN_CENTRAL")
        self.assertEqual(dataframe_resultado.loc[2, "FARMACIA_DETECTADA"], "")
        self.assertEqual(farmacias["16_FARMA_FARMACIA_INTERNA_CRS"], 1)

    def test_preclasificacion_con_reglas_ejemplo(self) -> None:
        dataframe = pd.DataFrame(
            [
                {
                    "SUBINVENTARIO": "DISPONIBLE",
                    "ORG_ORIGEN": "CUALQUIERA",
                    "ORG_DESTINO": "16_FARMA_FARMACIA_INTERNA_CRS",
                    "TIPO_TRANSACCION": "RMA_RECEIPT",
                    "TIPO_ORIGEN": "RMA",
                    "ORIGEN": "ALGO",
                    "MOTIVO": "",
                    "FARMACIA_DETECTADA": "16_FARMA_FARMACIA_INTERNA_CRS",
                },
                {
                    "SUBINVENTARIO": "DISPONIBLE",
                    "ORG_ORIGEN": "CUALQUIERA",
                    "ORG_DESTINO": "16_FARMA_FARMACIA_INTERNA_CRS",
                    "TIPO_TRANSACCION": "SALES_ORDER_ISSUE",
                    "TIPO_ORIGEN": "SALES_ORDER",
                    "ORIGEN": "MASIVO_CONSUMO.ORDER",
                    "MOTIVO": "",
                    "FARMACIA_DETECTADA": "16_FARMA_FARMACIA_INTERNA_CRS",
                },
            ]
        )

        resultado = self.clasificador.clasificar(dataframe)

        self.assertTrue(resultado.exito)
        self.assertEqual(resultado.cantidad_clasificados, 2)
        self.assertEqual(resultado.dataframe_resultado.loc[0, "TIPOLOGIA_PRELIMINAR"], "DEVOLUCIONES")
        self.assertEqual(
            resultado.dataframe_resultado.loc[1, "TIPOLOGIA_PRELIMINAR"],
            "DISPENSACION_AL_PACIENTE",
        )

    def test_regla_con_comodin_personalizada(self) -> None:
        reglas = [
            {
                "nombre_regla": "comodin_general",
                "prioridad": 1,
                "condiciones": {
                    "TIPO_TRANSACCION": ["CYCLE_COUNT_ADJUST"],
                    "MOTIVO": ["*"],
                },
                "resultado": "CONTEO_CICLICO",
            }
        ]

        with tempfile.TemporaryDirectory() as carpeta_temporal:
            ruta_reglas = Path(carpeta_temporal) / "reglas.json"
            ruta_reglas.write_text(json.dumps(reglas, ensure_ascii=False), encoding="utf-8")
            clasificador = ClasificadorTipologia(ruta_reglas=ruta_reglas)

            dataframe = pd.DataFrame(
                [
                    {
                        "TIPO_TRANSACCION": "CYCLE_COUNT_ADJUST",
                        "MOTIVO": "CUALQUIER_VALOR",
                    }
                ]
            )

            resultado = clasificador.clasificar(dataframe)

        self.assertEqual(resultado.cantidad_clasificados, 1)
        self.assertEqual(resultado.dataframe_resultado.loc[0, "TIPOLOGIA_PRELIMINAR"], "CONTEO_CICLICO")

    def test_normalizador_renombra_y_normaliza_campos(self) -> None:
        dataframe = pd.DataFrame(
            [
                {
                    "ORG DESTINO": " 16_farma_farmacia_interna_crs ",
                    "TIPO TRANSACCION": " account alias receipt ",
                    "TIPO ORIGEN": " account alias ",
                    "SUB INVENTARIO": " disponible ",
                    "ORG ORIGEN": None,
                    "ORIGEN": " masivo_consumo.order ",
                    "MOTIVO": None,
                }
            ]
        )
        columnas_mapeadas = {
            "ORG_DESTINO": "ORG DESTINO",
            "TIPO_TRANSACCION": "TIPO TRANSACCION",
            "TIPO_ORIGEN": "TIPO ORIGEN",
            "SUBINVENTARIO": "SUB INVENTARIO",
            "ORG_ORIGEN": "ORG ORIGEN",
            "ORIGEN": "ORIGEN",
            "MOTIVO": "MOTIVO",
        }

        dataframe_resultado = self.normalizador.normalizar(dataframe, columnas_mapeadas)

        self.assertIn("ORG_DESTINO", dataframe_resultado.columns)
        self.assertEqual(dataframe_resultado.loc[0, "ORG_DESTINO"], "16_FARMA_FARMACIA_INTERNA_CRS")
        self.assertEqual(dataframe_resultado.loc[0, "TIPO_TRANSACCION"], "ACCOUNT_ALIAS_RECEIPT")
        self.assertEqual(dataframe_resultado.loc[0, "TIPO_ORIGEN"], "ACCOUNT_ALIAS")
        self.assertEqual(dataframe_resultado.loc[0, "ORG_ORIGEN"], "")


if __name__ == "__main__":
    unittest.main()
