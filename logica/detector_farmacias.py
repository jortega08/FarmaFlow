"""Deteccion preliminar de farmacias a partir de columnas organizacionales."""

from __future__ import annotations

import logging

import pandas as pd

from utilidades.texto import normalizar_texto


class DetectorFarmacias:
    """Identifica candidatos de farmacia usando una heuristica simple."""

    COLUMNAS_CANDIDATAS = ("ORG_DESTINO", "ORG_ORIGEN")

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def detectar(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
        """Agrega la columna de farmacia detectada y devuelve conteos encontrados."""
        self._logger.info("Iniciando deteccion preliminar de farmacias.")

        dataframe_resultado = dataframe.copy(deep=True)
        dataframe_resultado["FARMACIA_DETECTADA"] = dataframe_resultado.apply(
            self._detectar_farmacia_en_fila,
            axis=1,
        )

        conteos = (
            dataframe_resultado["FARMACIA_DETECTADA"]
            .loc[lambda serie: serie != ""]
            .value_counts()
            .to_dict()
        )

        self._logger.info("Deteccion de farmacias finalizada. Candidatas encontradas: %s.", len(conteos))
        return dataframe_resultado, {str(clave): int(valor) for clave, valor in conteos.items()}

    def _detectar_farmacia_en_fila(self, fila: pd.Series) -> str:
        """Busca el primer valor organizacional que parezca una farmacia."""
        for columna in self.COLUMNAS_CANDIDATAS:
            valor = normalizar_texto(fila.get(columna, ""))
            if "FARM" in valor:
                return valor
        return ""
