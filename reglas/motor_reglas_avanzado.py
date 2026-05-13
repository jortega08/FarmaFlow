"""Motor de clasificacion avanzado con evaluacion vectorizada por mascaras pandas."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from modelos.resultado_preclasificacion import ResultadoPreclasificacion
from reglas.evaluador_condiciones import ContextoMotor, EvaluadorCondiciones
from utilidades.texto import normalizar_nombre_columna, normalizar_texto, normalizar_valor_por_campo


@dataclass(slots=True)
class CondicionMotor:
    """Condicion atomica lista para evaluacion vectorizada."""

    campo: str
    operador: str
    valores: list[str]
    lista_id: int | None = None
    atributo_farmacia: str | None = None


@dataclass(slots=True)
class ReglaMotor:
    """Regla de clasificacion con condiciones ricas (operador explícito)."""

    nombre: str
    prioridad: int
    tipologia_resultado: str
    condiciones: list[CondicionMotor] = field(default_factory=list)
    id: int | None = None


class MotorReglasAvanzado:
    """Clasifica movimientos aplicando reglas vectorizadas con 14 operadores.

    Reemplaza el enfoque iterrows de ClasificadorTipologia para cargas grandes.
    Compatible con reglas legado (operador 'EN', comodin '*') sin cambios en la BD.
    """

    COLUMNAS_AUDITORIA = (
        "TIPOLOGIA_PRELIMINAR",
        "TIPOLOGIA_FINAL",
        "REGLA_APLICADA",
        "REGLA_ID",
        "REGLA_DERIVADA_APLICADA",
        "REGLA_DERIVADA_ID",
        "EXPLICACION_REGLA",
    )

    def __init__(
        self,
        proveedor_reglas: Callable[[], list[ReglaMotor]],
        proveedor_contexto: Callable[[], ContextoMotor] | None = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._proveedor_reglas = proveedor_reglas
        self._proveedor_contexto = proveedor_contexto

    def clasificar(self, dataframe: pd.DataFrame) -> ResultadoPreclasificacion:
        """Aplica las reglas en orden de prioridad mediante mascaras vectorizadas."""
        reglas = sorted(self._proveedor_reglas(), key=lambda r: (r.prioridad, r.nombre))
        contexto = self._proveedor_contexto() if self._proveedor_contexto is not None else ContextoMotor()
        evaluador = EvaluadorCondiciones()

        self._logger.info("Motor avanzado: %s reglas cargadas.", len(reglas))

        df = dataframe.copy(deep=True)
        df["TIPOLOGIA_PRELIMINAR"] = "SIN_CLASIFICAR"
        df["REGLA_APLICADA"] = ""
        df["REGLA_ID"] = pd.NA
        df["EXPLICACION_REGLA"] = ""

        reglas_base = [regla for regla in reglas if not _es_regla_derivada(regla)]
        reglas_derivadas = [regla for regla in reglas if _es_regla_derivada(regla)]

        self._aplicar_reglas_base(df, reglas_base, evaluador, contexto)

        df["TIPOLOGIA_FINAL"] = df["TIPOLOGIA_PRELIMINAR"]
        df["REGLA_DERIVADA_APLICADA"] = ""
        df["REGLA_DERIVADA_ID"] = pd.NA

        if reglas_derivadas:
            self._aplicar_reglas_derivadas(df, reglas_derivadas, evaluador, contexto)

        cantidad_registros = int(len(df))
        columna_tipologia = "TIPOLOGIA_FINAL" if "TIPOLOGIA_FINAL" in df.columns else "TIPOLOGIA_PRELIMINAR"
        cantidad_sin_clasificar = int(df[columna_tipologia].eq("SIN_CLASIFICAR").sum())
        cantidad_clasificados = cantidad_registros - cantidad_sin_clasificar

        tipologias_detectadas: dict[str, int] = {
            str(k): int(v) for k, v in df[columna_tipologia].value_counts().items()
        }
        farmacias_detectadas: dict[str, int] = {}
        if "FARMACIA_DETECTADA" in df.columns:
            farmacias_detectadas = {
                str(k): int(v)
                for k, v in df["FARMACIA_DETECTADA"].loc[lambda s: s.ne("")].value_counts().items()
            }

        self._logger.info(
            "Motor avanzado finalizado. Clasificados: %s. Sin clasificar: %s.",
            cantidad_clasificados,
            cantidad_sin_clasificar,
        )

        return ResultadoPreclasificacion(
            exito=True,
            mensaje="Preclasificacion avanzada completada correctamente.",
            cantidad_registros=cantidad_registros,
            cantidad_clasificados=cantidad_clasificados,
            cantidad_sin_clasificar=cantidad_sin_clasificar,
            tipologias_detectadas=tipologias_detectadas,
            farmacias_detectadas=farmacias_detectadas,
            dataframe_resultado=df,
        )

    def _aplicar_reglas_base(
        self,
        df: pd.DataFrame,
        reglas: list[ReglaMotor],
        evaluador: EvaluadorCondiciones,
        contexto: ContextoMotor,
    ) -> None:
        for regla in reglas:
            mask = self._generar_mascara_regla(df, regla, evaluador, contexto)
            pendientes = df["TIPOLOGIA_PRELIMINAR"].eq("SIN_CLASIFICAR")
            aplica = mask & pendientes

            if aplica.any():
                df.loc[aplica, "TIPOLOGIA_PRELIMINAR"] = regla.tipologia_resultado
                df.loc[aplica, "REGLA_APLICADA"] = regla.nombre
                df.loc[aplica, "REGLA_ID"] = regla.id
                df.loc[aplica, "EXPLICACION_REGLA"] = (
                    f"Regla '{regla.nombre}' aplicada por prioridad {regla.prioridad}."
                )

    def _aplicar_reglas_derivadas(
        self,
        df: pd.DataFrame,
        reglas: list[ReglaMotor],
        evaluador: EvaluadorCondiciones,
        contexto: ContextoMotor,
    ) -> None:
        for regla in reglas:
            mask = self._generar_mascara_regla(df, regla, evaluador, contexto)
            pendientes = df["REGLA_DERIVADA_APLICADA"].eq("")
            aplica = mask & pendientes

            if aplica.any():
                df.loc[aplica, "TIPOLOGIA_FINAL"] = regla.tipologia_resultado
                df.loc[aplica, "REGLA_DERIVADA_APLICADA"] = regla.nombre
                df.loc[aplica, "REGLA_DERIVADA_ID"] = regla.id
                df.loc[aplica, "EXPLICACION_REGLA"] = (
                    df.loc[aplica, "EXPLICACION_REGLA"].fillna("").astype(str)
                    + f" Regla derivada '{regla.nombre}' aplicada por prioridad {regla.prioridad}."
                )

    @staticmethod
    def _generar_mascara_regla(
        df: pd.DataFrame,
        regla: ReglaMotor,
        evaluador: EvaluadorCondiciones,
        contexto: ContextoMotor,
    ) -> pd.Series:
        mask = pd.Series(True, index=df.index)
        for condicion in regla.condiciones:
            mask = mask & evaluador.generar_mascara(
                df,
                condicion.campo,
                condicion.operador,
                condicion.valores,
                condicion.lista_id,
                condicion.atributo_farmacia,
                contexto,
            )
        return mask

    @classmethod
    def desde_proveedor_simple(
        cls,
        proveedor_reglas: Callable[[], list[dict[str, Any]]],
        proveedor_contexto: Callable[[], ContextoMotor] | None = None,
    ) -> MotorReglasAvanzado:
        """Crea una instancia wrapeando un proveedor de reglas en formato legado.

        El formato legado es {nombre_regla, prioridad, condiciones: {campo: [valores]}, resultado}.
        Util para tests o para migrar gradualmente sin cambiar el proveedor.
        """

        def _convertir() -> list[ReglaMotor]:
            return [_regla_legado_a_motor(r) for r in proveedor_reglas()]

        return cls(proveedor_reglas=_convertir, proveedor_contexto=proveedor_contexto)


def _regla_legado_a_motor(regla: dict[str, Any]) -> ReglaMotor:
    """Convierte el formato dict legado a ReglaMotor."""
    condiciones = [
        CondicionMotor(
            campo=normalizar_nombre_columna(campo),
            operador="EN",
            valores=[normalizar_valor_por_campo(campo, valor) for valor in valores],
        )
        for campo, valores in regla.get("condiciones", {}).items()
    ]
    return ReglaMotor(
        nombre=str(regla.get("nombre_regla", "")),
        prioridad=int(regla.get("prioridad", 999)),
        tipologia_resultado=normalizar_texto(regla.get("resultado", "SIN_CLASIFICAR")),
        condiciones=condiciones,
    )


def _es_regla_derivada(regla: ReglaMotor) -> bool:
    return any(condicion.campo in {"TIPOLOGIA", "TIPOLOGIA_PRELIMINAR"} for condicion in regla.condiciones)
