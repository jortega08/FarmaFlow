"""Normalizacion de columnas y valores para archivos Oracle."""

from __future__ import annotations

import logging

import pandas as pd

from utilidades.texto import CAMPOS_CODIGO, normalizar_codigo, normalizar_texto


class NormalizadorDatos:
    """Renombra columnas canonicas y normaliza campos de texto clave."""

    COLUMNAS_CODIGO = tuple(CAMPOS_CODIGO)
    COLUMNAS_TEXTO_CLAVE = (
        "SUBINVENTARIO",
        "ORG_ORIGEN",
        "ORG_DESTINO",
        "TIPO_TRANSACCION",
        "TIPO_ORIGEN",
        "ORIGEN",
        "MOTIVO",
        "TIPOLOGIA",
    )

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def normalizar(self, dataframe: pd.DataFrame, columnas_mapeadas: dict[str, str]) -> pd.DataFrame:
        """Devuelve una copia del dataframe con columnas canonicas y texto normalizado."""
        self._logger.info("Iniciando normalizacion de datos.")

        dataframe_normalizado = dataframe.copy(deep=True)
        renombre_columnas = {
            columna_original: columna_canonica
            for columna_canonica, columna_original in columnas_mapeadas.items()
            if columna_original in dataframe_normalizado.columns
        }
        dataframe_normalizado = dataframe_normalizado.rename(columns=renombre_columnas)

        for columna in self.COLUMNAS_TEXTO_CLAVE:
            if columna not in dataframe_normalizado.columns:
                continue

            normalizador = normalizar_codigo if columna in self.COLUMNAS_CODIGO else normalizar_texto
            dataframe_normalizado[columna] = dataframe_normalizado[columna].map(normalizador)

        self._logger.info("Normalizacion completada sobre %s columnas canonicas.", len(renombre_columnas))
        return dataframe_normalizado
