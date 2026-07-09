"""Motor de preclasificacion por tipologia basado en reglas externas."""

from __future__ import annotations

import logging
from pathlib import Path
from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd

from logica.diagnostico_sin_clasificar import asegurar_diagnostico_basico
from modelos.resultado_preclasificacion import ResultadoPreclasificacion
from utilidades.rutas import cargar_json, resolver_ruta_proyecto
from utilidades.texto import es_valor_comodin, normalizar_nombre_columna, normalizar_texto, normalizar_valor_por_campo


REGLAS_FALLBACK = [
    {
        "nombre_regla": "conteo_ciclico_fallback",
        "prioridad": 999,
        "condiciones": {
            "TIPO_TRANSACCION": ["CYCLE_COUNT_ADJUST"],
            "TIPO_ORIGEN": ["CYCLE_COUNT"],
        },
        "resultado": "CONTEO_CICLICO",
    }
]


class ClasificadorTipologia:
    """Evalua reglas configurables y asigna una tipologia preliminar."""

    def __init__(
        self,
        ruta_reglas: Path | None = None,
        proveedor_reglas: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._ruta_reglas = ruta_reglas or resolver_ruta_proyecto(
            "configuracion",
            "reglas_tipologia.json",
        )
        self._proveedor_reglas = proveedor_reglas

    def clasificar(self, dataframe: pd.DataFrame) -> ResultadoPreclasificacion:
        """Aplica reglas ordenadas por prioridad sobre cada fila del dataframe."""
        reglas = self._cargar_reglas()
        self._logger.info("Iniciando preclasificacion con %s reglas.", len(reglas))

        dataframe_resultado = dataframe.copy(deep=True)
        contexto_columnas = self._construir_contexto_columnas(dataframe_resultado, reglas)
        tipologias: list[str] = []
        reglas_aplicadas: list[str] = []

        for _, fila in dataframe_resultado.iterrows():
            tipologia, nombre_regla = self._clasificar_fila(fila, reglas, contexto_columnas)
            tipologias.append(tipologia)
            reglas_aplicadas.append(nombre_regla)

        dataframe_resultado["TIPOLOGIA_PRELIMINAR"] = tipologias
        dataframe_resultado["TIPOLOGIA_FINAL"] = tipologias
        dataframe_resultado["REGLA_APLICADA"] = reglas_aplicadas
        dataframe_resultado["REGLA_DERIVADA_APLICADA"] = ""
        dataframe_resultado = asegurar_diagnostico_basico(dataframe_resultado)

        cantidad_registros = int(len(dataframe_resultado))
        cantidad_sin_clasificar = int((dataframe_resultado["TIPOLOGIA_PRELIMINAR"] == "SIN_CLASIFICAR").sum())
        cantidad_clasificados = cantidad_registros - cantidad_sin_clasificar
        tipologias_detectadas = (
            dataframe_resultado["TIPOLOGIA_PRELIMINAR"].value_counts().to_dict()
            if "TIPOLOGIA_PRELIMINAR" in dataframe_resultado
            else {}
        )
        farmacias_detectadas = (
            dataframe_resultado["FARMACIA_DETECTADA"]
            .loc[lambda serie: serie != ""]
            .value_counts()
            .to_dict()
            if "FARMACIA_DETECTADA" in dataframe_resultado
            else {}
        )

        self._logger.info(
            "Preclasificacion finalizada. Clasificados: %s. Sin clasificar: %s.",
            cantidad_clasificados,
            cantidad_sin_clasificar,
        )

        return ResultadoPreclasificacion(
            exito=True,
            mensaje="Preclasificacion completada correctamente.",
            cantidad_registros=cantidad_registros,
            cantidad_clasificados=cantidad_clasificados,
            cantidad_sin_clasificar=cantidad_sin_clasificar,
            tipologias_detectadas={str(clave): int(valor) for clave, valor in tipologias_detectadas.items()},
            farmacias_detectadas={str(clave): int(valor) for clave, valor in farmacias_detectadas.items()},
            dataframe_resultado=dataframe_resultado,
        )

    def _cargar_reglas(self) -> list[dict[str, Any]]:
        """Carga, valida y ordena las reglas externas."""
        if self._proveedor_reglas is not None:
            reglas_bd = self._cargar_reglas_desde_proveedor()
            if reglas_bd:
                return reglas_bd

        try:
            reglas = cargar_json(self._ruta_reglas)
        except Exception as error:  # noqa: BLE001
            self._logger.exception(
                "No fue posible cargar las reglas externas. Se utilizara el fallback minimo."
            )
            self._logger.warning("Detalle del error de reglas: %s", error)
            reglas = REGLAS_FALLBACK

        reglas_validas: list[dict[str, Any]] = []
        for regla in reglas:
            regla_validada = self._validar_regla(regla)
            if regla_validada:
                reglas_validas.append(regla_validada)

        return sorted(reglas_validas, key=lambda regla: int(regla["prioridad"]))

    def _cargar_reglas_desde_proveedor(self) -> list[dict[str, Any]]:
        """Carga reglas desde el proveedor inyectado, normalmente respaldado por BD."""
        try:
            reglas = self._proveedor_reglas() if self._proveedor_reglas is not None else []
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar reglas persistidas: %s", error)
            return []

        reglas_validas: list[dict[str, Any]] = []
        for regla in reglas:
            regla_validada = self._validar_regla(regla)
            if regla_validada:
                reglas_validas.append(regla_validada)

        if not reglas_validas:
            self._logger.warning("No hay reglas persistidas validas. Se usara la configuracion legacy si existe.")
        return sorted(reglas_validas, key=lambda regla: int(regla["prioridad"]))

    def _validar_regla(self, regla: dict[str, Any]) -> dict[str, Any] | None:
        """Normaliza una regla y descarta configuraciones mal formadas."""
        nombre_regla = str(regla.get("nombre_regla", "")).strip() or "regla_sin_nombre"
        resultado = normalizar_texto(regla.get("resultado", ""))
        condiciones = regla.get("condiciones", {})

        if not resultado or not isinstance(condiciones, dict) or not condiciones:
            self._logger.warning("La regla %s es invalida y sera ignorada.", nombre_regla)
            return None

        condiciones_normalizadas: dict[str, dict[str, Any]] = {}
        for campo, definicion in condiciones.items():
            campo_normalizado = normalizar_nombre_columna(campo)
            operador = "EN"
            valores = definicion
            if isinstance(definicion, Mapping):
                operador = normalizar_nombre_columna(definicion.get("operador", "EN"))
                valores = definicion.get("valores", definicion.get("valor", definicion.get("valor_texto", [])))

            if isinstance(valores, list):
                valores_normalizados = [normalizar_valor_por_campo(campo_normalizado, valor) for valor in valores]
            else:
                valores_normalizados = [normalizar_valor_por_campo(campo_normalizado, valores)]

            if not valores_normalizados and operador not in {"VACIO", "NO_VACIO"}:
                self._logger.warning(
                    "La regla %s tiene una condicion vacia en %s y sera ignorada.",
                    nombre_regla,
                    campo,
                )
                return None

            condiciones_normalizadas[campo_normalizado] = {
                "operador": operador,
                "valores": valores_normalizados,
            }

        return {
            "nombre_regla": nombre_regla,
            "prioridad": int(regla.get("prioridad", 999)),
            "condiciones": condiciones_normalizadas,
            "resultado": resultado,
        }

    def _clasificar_fila(
        self,
        fila: pd.Series,
        reglas: list[dict[str, Any]],
        contexto_columnas: dict[tuple[str, str], frozenset[str]],
    ) -> tuple[str, str]:
        """Retorna la tipologia preliminar y la regla aplicada para una fila."""
        for regla in reglas:
            if self._coincide_regla(fila, regla["condiciones"], contexto_columnas):
                return str(regla["resultado"]), str(regla["nombre_regla"])
        return "SIN_CLASIFICAR", ""

    def _coincide_regla(
        self,
        fila: pd.Series,
        condiciones: dict[str, Any],
        contexto_columnas: dict[tuple[str, str], frozenset[str]],
    ) -> bool:
        """Verifica si la fila satisface todas las condiciones de la regla."""
        for campo, definicion in condiciones.items():
            if isinstance(definicion, Mapping):
                operador = normalizar_nombre_columna(definicion.get("operador", "EN"))
                valores_esperados = list(definicion.get("valores", []))
            else:
                operador = "EN"
                valores_esperados = list(definicion)

            valor_fila = normalizar_valor_por_campo(campo, fila.get(campo, ""))
            if operador == "VACIO":
                if valor_fila != "":
                    return False
                continue
            if operador == "NO_VACIO":
                if valor_fila == "":
                    return False
                continue
            if any(es_valor_comodin(valor) for valor in valores_esperados):
                continue
            if operador == "CONTIENE":
                if not any(valor in valor_fila for valor in valores_esperados):
                    return False
                continue
            if operador in {"EN_COLUMNA", "NO_EN_COLUMNA"}:
                columna_referencia = normalizar_nombre_columna(valores_esperados[0]) if valores_esperados else ""
                valores_columna = contexto_columnas.get((campo, columna_referencia))
                if valores_columna is None or not valor_fila:
                    return False
                esta_en_columna = valor_fila in valores_columna
                if operador == "EN_COLUMNA" and not esta_en_columna:
                    return False
                if operador == "NO_EN_COLUMNA" and esta_en_columna:
                    return False
                continue
            if valor_fila not in valores_esperados:
                return False
        return True

    def _construir_contexto_columnas(
        self,
        dataframe: pd.DataFrame,
        reglas: list[dict[str, Any]],
    ) -> dict[tuple[str, str], frozenset[str]]:
        """Precalcula valores unicos para condiciones EN_COLUMNA/NO_EN_COLUMNA."""
        contexto: dict[tuple[str, str], frozenset[str]] = {}
        columnas_reales = {normalizar_nombre_columna(columna): str(columna) for columna in dataframe.columns}
        for regla in reglas:
            for campo, definicion in regla["condiciones"].items():
                if not isinstance(definicion, Mapping):
                    continue
                operador = normalizar_nombre_columna(definicion.get("operador", "EN"))
                if operador not in {"EN_COLUMNA", "NO_EN_COLUMNA"}:
                    continue
                valores = list(definicion.get("valores", []))
                columna_referencia = normalizar_nombre_columna(valores[0]) if valores else ""
                columna_real = columnas_reales.get(columna_referencia)
                if not columna_real:
                    continue
                valores_columna = {
                    normalizar_valor_por_campo(campo, valor)
                    for valor in dataframe[columna_real].tolist()
                    if normalizar_valor_por_campo(campo, valor)
                }
                contexto[(campo, columna_referencia)] = frozenset(valores_columna)
        return contexto
