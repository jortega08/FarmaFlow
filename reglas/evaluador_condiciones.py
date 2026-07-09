"""Evaluacion vectorizada de condiciones sobre DataFrames de pandas."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from reglas.operadores import OperadorCondicion, operador_desde_texto
from utilidades.texto import CAMPOS_CODIGO, es_valor_comodin, normalizar_codigo, normalizar_nombre_columna, normalizar_texto


COLUMNAS_CODIGO = tuple(CAMPOS_CODIGO)


def _normalizador_para_campo(campo: str):
    campo_normalizado = normalizar_nombre_columna(campo)
    return normalizar_codigo if campo_normalizado in COLUMNAS_CODIGO else normalizar_texto


@dataclass(slots=True)
class FarmaciaAtributos:
    """Atributos de una farmacia relevantes para la evaluacion de condiciones."""

    tipo_codigo: str
    puede_prestar: bool
    es_interna: bool
    es_externa: bool


@dataclass(slots=True)
class ContextoMotor:
    """Datos de referencia pre-cargados que el motor necesita para operar.

    Se construye una sola vez antes de clasificar un lote y se pasa a cada
    evaluacion de condicion.  Los dicts se indexan por la forma normalizada
    del valor tal como aparece en el DataFrame.
    """

    farmacias: dict[str, FarmaciaAtributos] = field(default_factory=dict)
    listas: dict[int, frozenset[str]] = field(default_factory=dict)


class EvaluadorCondiciones:
    """Genera mascaras booleanas de pandas para cada condicion atomica."""

    def generar_mascara(
        self,
        df: pd.DataFrame,
        campo: str,
        operador: str,
        valores: list[str],
        lista_id: int | None,
        atributo_farmacia: str | None,
        contexto: ContextoMotor,
    ) -> pd.Series:
        """Devuelve una Series booleana con True donde la condicion se cumple."""
        campo_dataframe = self._resolver_campo_dataframe(df, campo)
        normalizador = _normalizador_para_campo(campo)
        if campo_dataframe is not None:
            serie: pd.Series = df[campo_dataframe].map(normalizador)
        else:
            serie = pd.Series("", index=df.index)

        op = operador_desde_texto(operador)
        valores_normalizados = [normalizador(valor) for valor in valores if normalizador(valor)]
        atributo_normalizado = normalizar_texto(atributo_farmacia)

        match op:
            # --- igualdad / legado EN ---
            case OperadorCondicion.IGUAL | OperadorCondicion.EN:
                if any(es_valor_comodin(v) for v in valores_normalizados):
                    return pd.Series(True, index=df.index)
                return serie.isin(valores_normalizados)

            case OperadorCondicion.DISTINTO:
                return ~serie.isin(valores_normalizados)

            # --- substring ---
            case OperadorCondicion.CONTIENE:
                mask = pd.Series(False, index=df.index)
                for v in valores_normalizados:
                    if es_valor_comodin(v):
                        return pd.Series(True, index=df.index)
                    mask |= serie.str.contains(v, regex=False, na=False)
                return mask

            case OperadorCondicion.NO_CONTIENE:
                mask = pd.Series(True, index=df.index)
                for v in valores_normalizados:
                    mask &= ~serie.str.contains(v, regex=False, na=False)
                return mask

            # --- prefijo / sufijo ---
            case OperadorCondicion.EMPIEZA_POR:
                mask = pd.Series(False, index=df.index)
                for v in valores_normalizados:
                    mask |= serie.str.startswith(v, na=False)
                return mask

            case OperadorCondicion.TERMINA_EN:
                mask = pd.Series(False, index=df.index)
                for v in valores_normalizados:
                    mask |= serie.str.endswith(v, na=False)
                return mask

            # --- listas configurables ---
            case OperadorCondicion.EN_LISTA:
                valores_lista = contexto.listas.get(lista_id, frozenset()) if lista_id is not None else frozenset()
                vals = frozenset(normalizador(valor) for valor in valores_lista)
                return serie.isin(vals)

            case OperadorCondicion.NO_EN_LISTA:
                valores_lista = contexto.listas.get(lista_id, frozenset()) if lista_id is not None else frozenset()
                vals = frozenset(normalizador(valor) for valor in valores_lista)
                return ~serie.isin(vals)

            # --- comparacion contra otra columna del DataFrame ---
            case OperadorCondicion.EN_COLUMNA:
                valores_columna = self._valores_columna_referencia(df, valores, normalizador)
                if valores_columna is None:
                    return pd.Series(False, index=df.index)
                return serie.ne("") & serie.isin(valores_columna)

            case OperadorCondicion.NO_EN_COLUMNA:
                valores_columna = self._valores_columna_referencia(df, valores, normalizador)
                if valores_columna is None:
                    return pd.Series(False, index=df.index)
                return serie.ne("") & ~serie.isin(valores_columna)

            # --- presencia ---
            case OperadorCondicion.VACIO:
                return serie.eq("")

            case OperadorCondicion.NO_VACIO:
                return serie.ne("")

            # --- atributos de farmacia ---
            case OperadorCondicion.FARMACIA_ES_TIPO:
                tipo_buscado = atributo_normalizado or (valores_normalizados[0] if valores_normalizados else "")
                tipo_map = {normalizador(k): normalizar_texto(v.tipo_codigo) for k, v in contexto.farmacias.items()}
                return serie.map(tipo_map).fillna("").eq(tipo_buscado)

            case OperadorCondicion.FARMACIA_NO_ES_TIPO:
                tipo_buscado = atributo_normalizado or (valores_normalizados[0] if valores_normalizados else "")
                tipo_map = {normalizador(k): normalizar_texto(v.tipo_codigo) for k, v in contexto.farmacias.items()}
                return ~serie.map(tipo_map).fillna("").eq(tipo_buscado)

            case OperadorCondicion.FARMACIA_PUEDE_PRESTAR:
                presta_map = {normalizador(k): v.puede_prestar for k, v in contexto.farmacias.items()}
                return serie.map(presta_map).fillna(False).astype(bool)

            case OperadorCondicion.FARMACIA_NO_PUEDE_PRESTAR:
                presta_map = {normalizador(k): v.puede_prestar for k, v in contexto.farmacias.items()}
                return ~serie.map(presta_map).fillna(False).astype(bool)

        return pd.Series(False, index=df.index)

    @staticmethod
    def _resolver_campo_dataframe(df: pd.DataFrame, campo: str) -> str | None:
        if campo in df.columns:
            return campo
        if campo == "TIPOLOGIA" and "TIPOLOGIA_PRELIMINAR" in df.columns:
            return "TIPOLOGIA_PRELIMINAR"
        return None

    def _valores_columna_referencia(
        self,
        df: pd.DataFrame,
        valores: list[str],
        normalizador,
    ) -> frozenset[str] | None:
        """Devuelve valores unicos normalizados de la columna referenciada."""
        if not valores:
            return None
        columna_referencia = self._resolver_campo_dataframe(df, normalizar_nombre_columna(valores[0]))
        if columna_referencia is None:
            return None
        serie_referencia = df[columna_referencia].map(normalizador)
        return frozenset(valor for valor in serie_referencia.unique().tolist() if valor)
