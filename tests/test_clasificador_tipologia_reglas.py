"""Pruebas funcionales para reglas_tipologia.json generado del cuadro de filtros."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logica.clasificador_tipologia import ClasificadorTipologia


def fila_base(**campos):
    base = {
        "SUBINVENTARIO": "",
        "ORG_ORIGEN": "",
        "ORG_DESTINO": "",
        "TIPO_TRANSACCION": "",
        "TIPO_ORIGEN": "",
        "ORIGEN": "",
        "MOTIVO": "",
        "FARMACIA_DETECTADA": "",
    }
    base.update(campos)
    return base


class PruebasReglasTipologia(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.clasificador = ClasificadorTipologia()

    def _clasificar(self, filas: list[dict]) -> pd.DataFrame:
        dataframe = pd.DataFrame(filas)
        return self.clasificador.clasificar(dataframe).dataframe_resultado

    def test_dispensacion_al_paciente(self) -> None:
        filas = [
            fila_base(ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                     TIPO_TRANSACCION="SALES_ORDER_ISSUE", TIPO_ORIGEN="SALES_ORDER"),
            fila_base(ORG_DESTINO="256_FARMA_URGENCIAS_CRS",
                     TIPO_TRANSACCION="SALES_ORDER_ISSUE", TIPO_ORIGEN="SALES_ORDER"),
        ]
        resultado = self._clasificar(filas)
        self.assertTrue((resultado["TIPOLOGIA_PRELIMINAR"] == "DISPENSACION_AL_PACIENTE").all())

    def test_devoluciones(self) -> None:
        filas = [fila_base(ORG_DESTINO="47_FARMA_ALMACEN_CIRUGIA_CRS",
                           TIPO_TRANSACCION="RMA_RECEIPT", TIPO_ORIGEN="RMA")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "DEVOLUCIONES")

    def test_entradas_prestamos_internos(self) -> None:
        filas = [fila_base(ORG_ORIGEN="256_FARMA_URGENCIAS_CRS",
                           ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                           TIPO_TRANSACCION="INTRANSIT_RECEIPT", TIPO_ORIGEN="INVENTORY")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "ENTRADAS_PRESTAMOS_INTERNOS")

    def test_salidas_prestamos_internos(self) -> None:
        filas = [fila_base(ORG_ORIGEN="16_FARMA_FARMACIA_INTERNA_CRS",
                           ORG_DESTINO="47_FARMA_ALMACEN_CIRUGIA_CRS",
                           TIPO_TRANSACCION="INTRANSIT_SHIPMENT", TIPO_ORIGEN="INVENTORY")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "SALIDAS_PRESTAMOS_INTERNOS")

    def test_entradas_cedi(self) -> None:
        filas = [fila_base(ORG_ORIGEN="1058_CRUZ_VERDE_CEDI_COTA_ALMACEN_PRINCIPAL",
                           ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                           TIPO_TRANSACCION="ACCOUNT_ALIAS_RECEIPT", TIPO_ORIGEN="ACCOUNT_ALIAS")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "ENTRADAS_CEDI")

    def test_ordenes_de_compra(self) -> None:
        filas = [fila_base(ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                           TIPO_TRANSACCION="PO_RECEIPT", TIPO_ORIGEN="PURCHASE_ORDER")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "ORDENES_DE_COMPRA")

    def test_salidas_prestamos_externos_dos_patrones(self) -> None:
        filas = [
            fila_base(ORG_ORIGEN="20_FARMA_CLINICA_COUNTRY",
                     ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                     TIPO_TRANSACCION="INTRANSIT_SHIPMENT", TIPO_ORIGEN="INVENTORY"),
            fila_base(ORG_ORIGEN="20_FARMA_CLINICA_COUNTRY",
                     ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                     TIPO_TRANSACCION="INT_ORDER_INTR_SHIP", TIPO_ORIGEN="INTERNAL_ORDER"),
        ]
        resultado = self._clasificar(filas)
        self.assertTrue((resultado["TIPOLOGIA_PRELIMINAR"] == "SALIDAS_PRESTAMOS_EXTERNOS").all())

    def test_entradas_consignacion(self) -> None:
        filas = [fila_base(ORG_ORIGEN="102_FARMA_CONSIGN_PROV_CRS",
                           ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                           TIPO_TRANSACCION="INTRANSIT_RECEIPT", TIPO_ORIGEN="INVENTORY")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "ENTRADAS_CONSIGNACION")

    def test_entradas_central_prep(self) -> None:
        filas = [fila_base(ORG_ORIGEN="104_FARMA_CENTRAL_PREP_BOG",
                           ORG_DESTINO="47_FARMA_ALMACEN_CIRUGIA_CRS",
                           TIPO_TRANSACCION="INT_REQ_INTR_RCPT", TIPO_ORIGEN="INTERNAL_REQUISITION")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "ENTRADAS_CENTRAL_PREP")

    def test_entradas_central_rere(self) -> None:
        filas = [fila_base(ORG_ORIGEN="702_CRUZ_VERDE_CENTRAL_REEMPAQUE_REENVASE",
                           ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                           TIPO_TRANSACCION="INTRANSIT_RECEIPT", TIPO_ORIGEN="INVENTORY")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "ENTRADAS_CENTRAL_RERE")

    def test_prestamos_bopos(self) -> None:
        filas = [fila_base(ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                           TIPO_TRANSACCION="ACCOUNT_ALIAS_ISSUE", TIPO_ORIGEN="ACCOUNT_ALIAS",
                           ORIGEN="MOVIMIENTOS BOPOS-EBS")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "PRESTAMOS_BOPOS")

    def test_prestamos_bopos_con_valores_crudos_oracle(self) -> None:
        filas = [fila_base(
            ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
            TIPO_TRANSACCION="Account alias receipt",
            TIPO_ORIGEN="Account alias",
            ORIGEN="MOVIMIENTOS BOPOS-EBS",
        )]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "PRESTAMOS_BOPOS")

    def test_ajustes_base_captura(self) -> None:
        filas = [fila_base(ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                           TIPO_TRANSACCION="ACCOUNT_ALIAS_ISSUE", TIPO_ORIGEN="ACCOUNT_ALIAS",
                           ORIGEN="AA PRODUCTOS AVERIADOS DE PUNTOS")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "AJUSTES_BASE_CAPTURA")

    def test_ajustes_inconsistencias_receipt_e_issue(self) -> None:
        filas = [
            fila_base(ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                     TIPO_TRANSACCION="ACCOUNT_ALIAS_ISSUE", TIPO_ORIGEN="ACCOUNT_ALIAS",
                     ORIGEN="LEGALIZACION INCONSISTENCIAS DESPACHO"),
            fila_base(ORG_DESTINO="47_FARMA_ALMACEN_CIRUGIA_CRS",
                     TIPO_TRANSACCION="ACCOUNT_ALIAS_RECEIPT", TIPO_ORIGEN="ACCOUNT_ALIAS",
                     ORIGEN="LEGALIZACION INCONSIST DEVOLUCIONES PTO"),
        ]
        resultado = self._clasificar(filas)
        self.assertTrue((resultado["TIPOLOGIA_PRELIMINAR"] == "AJUSTES_INCONSISTENCIAS").all())

    def test_otros_ajustes_requiere_org_origen_vacio(self) -> None:
        filas = [
            fila_base(ORG_ORIGEN="", ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                     TIPO_TRANSACCION="Account alias issue", TIPO_ORIGEN="Account alias"),
            fila_base(ORG_ORIGEN="   ", ORG_DESTINO="47_FARMA_ALMACEN_CIRUGIA_CRS",
                     TIPO_TRANSACCION="Account alias receipt", TIPO_ORIGEN="Account alias"),
            fila_base(ORG_ORIGEN="1058_CRUZ_VERDE_CEDI_COTA_ALMACEN_PRINCIPAL",
                     ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                     TIPO_TRANSACCION="Account alias receipt", TIPO_ORIGEN="Account alias"),
        ]

        resultado = self._clasificar(filas)

        self.assertEqual(resultado.iloc[0]["TIPOLOGIA_PRELIMINAR"], "OTROS_AJUSTES")
        self.assertEqual(resultado.iloc[1]["TIPOLOGIA_PRELIMINAR"], "OTROS_AJUSTES")
        self.assertNotEqual(resultado.iloc[2]["TIPOLOGIA_PRELIMINAR"], "OTROS_AJUSTES")

    def test_traslados_hacia_cedi(self) -> None:
        filas = [fila_base(ORG_ORIGEN="800_CRUZ_VERDE_RETIRO",
                           ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
                           TIPO_TRANSACCION="INTRANSIT_SHIPMENT", TIPO_ORIGEN="INVENTORY")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "TRASLADOS_HACIA_CEDI")

    def test_conteo_ciclico_fallback(self) -> None:
        filas = [fila_base(TIPO_TRANSACCION="CYCLE_COUNT_ADJUST", TIPO_ORIGEN="CYCLE_COUNT")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "CONTEO_CICLICO")

    def test_movimiento_no_clasificable(self) -> None:
        filas = [fila_base(ORG_DESTINO="999_FAKE", TIPO_TRANSACCION="UNKNOWN", TIPO_ORIGEN="UNKNOWN")]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "SIN_CLASIFICAR")

    def test_origen_especifico_gana_sobre_cedi(self) -> None:
        """Una fila con ORIGEN especifico debe ir a AJUSTES_INCONSISTENCIAS aunque también encaje con ENTRADAS_CEDI."""
        filas = [fila_base(
            ORG_ORIGEN="1058_CRUZ_VERDE_CEDI_COTA_ALMACEN_PRINCIPAL",
            ORG_DESTINO="16_FARMA_FARMACIA_INTERNA_CRS",
            TIPO_TRANSACCION="ACCOUNT_ALIAS_RECEIPT", TIPO_ORIGEN="ACCOUNT_ALIAS",
            ORIGEN="LEGALIZACION INCONSISTENCIAS DESPACHO",
        )]
        self.assertEqual(self._clasificar(filas).iloc[0]["TIPOLOGIA_PRELIMINAR"], "AJUSTES_INCONSISTENCIAS")


if __name__ == "__main__":
    unittest.main()
