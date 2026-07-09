"""Diagnostico tecnico para movimientos que quedan sin clasificar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd

from reglas.evaluador_condiciones import ContextoMotor, EvaluadorCondiciones
from utilidades.texto import normalizar_codigo, normalizar_nombre_columna, normalizar_texto

if TYPE_CHECKING:
    from reglas.motor_reglas_avanzado import ReglaMotor
else:
    ReglaMotor = Any


SIN_CLASIFICAR = "SIN_CLASIFICAR"
COLUMNAS_DIAGNOSTICO = (
    "ESTADO_CLASIFICACION",
    "MOTIVO_SIN_CLASIFICAR",
    "SUGERENCIA_ACCION",
    "REGLA_CANDIDATA",
    "CONDICIONES_CUMPLIDAS",
    "CONDICIONES_FALLIDAS",
    "PORCENTAJE_COINCIDENCIA_REGLA",
)


@dataclass(slots=True)
class DiagnosticoFila:
    motivo: str
    sugerencia: str
    regla_candidata: str = ""
    condiciones_cumplidas: str = ""
    condiciones_fallidas: str = ""
    porcentaje: float = 0.0


def aplicar_diagnostico_clasificacion(
    dataframe: pd.DataFrame,
    reglas: list[ReglaMotor],
    evaluador: EvaluadorCondiciones,
    contexto: ContextoMotor,
) -> pd.DataFrame:
    """Completa estado, motivo y sugerencia para todas las filas procesadas."""
    df = dataframe.copy(deep=False)
    _asegurar_columnas_base(df)

    tipologia = df["TIPOLOGIA_FINAL"].fillna(df["TIPOLOGIA_PRELIMINAR"]).astype(str)
    clasificados = tipologia.ne(SIN_CLASIFICAR)
    sin_clasificar = ~clasificados

    df["ESTADO_CLASIFICACION"] = "CLASIFICADO"
    df.loc[sin_clasificar, "ESTADO_CLASIFICACION"] = "SIN_CLASIFICAR_JUSTIFICADO"
    _asegurar_columnas_diagnostico(df)
    df.loc[
        clasificados,
        [
            "MOTIVO_SIN_CLASIFICAR",
            "SUGERENCIA_ACCION",
            "REGLA_CANDIDATA",
            "CONDICIONES_CUMPLIDAS",
            "CONDICIONES_FALLIDAS",
        ],
    ] = ""
    df.loc[clasificados, "PORCENTAJE_COINCIDENCIA_REGLA"] = 0.0

    if not sin_clasificar.any():
        return df

    reglas_base = [regla for regla in reglas if not _es_regla_derivada(regla)]
    parciales = _diagnosticar_reglas_parciales(df, reglas_base, evaluador, contexto, sin_clasificar)

    internas_archivo = _valores_unicos(df, "ORG_DESTINO")
    listas = set().union(*(set(valores) for valores in contexto.listas.values())) if contexto.listas else set()
    transacciones_reglas, origenes_reglas, subinventarios_reglas = _valores_relevantes_reglas(reglas_base)

    for indice in df.index[sin_clasificar]:
        parcial = parciales.get(indice)
        diagnostico = diagnosticar_fila(
            df.loc[indice],
            contexto=contexto,
            internas_archivo=internas_archivo,
            tipos_transaccion_reglas=transacciones_reglas,
            tipos_origen_reglas=origenes_reglas,
            subinventarios_reglas=subinventarios_reglas,
            codigos_listas=listas,
            parcial=parcial,
        )
        df.at[indice, "TIPOLOGIA_PRELIMINAR"] = SIN_CLASIFICAR
        df.at[indice, "TIPOLOGIA_FINAL"] = SIN_CLASIFICAR
        df.at[indice, "MOTIVO_SIN_CLASIFICAR"] = diagnostico.motivo
        df.at[indice, "SUGERENCIA_ACCION"] = diagnostico.sugerencia
        df.at[indice, "REGLA_CANDIDATA"] = diagnostico.regla_candidata
        df.at[indice, "CONDICIONES_CUMPLIDAS"] = diagnostico.condiciones_cumplidas
        df.at[indice, "CONDICIONES_FALLIDAS"] = diagnostico.condiciones_fallidas
        df.at[indice, "PORCENTAJE_COINCIDENCIA_REGLA"] = diagnostico.porcentaje
    return df


def diagnosticar_fila(
    fila: pd.Series,
    *,
    contexto: ContextoMotor | None = None,
    internas_archivo: set[str] | None = None,
    tipos_transaccion_reglas: set[str] | None = None,
    tipos_origen_reglas: set[str] | None = None,
    subinventarios_reglas: set[str] | None = None,
    codigos_listas: set[str] | None = None,
    parcial: DiagnosticoFila | None = None,
) -> DiagnosticoFila:
    """Genera motivo y sugerencia para una fila sin clasificar."""
    contexto = contexto or ContextoMotor()
    internas_archivo = internas_archivo or set()
    conocidas = set(contexto.farmacias.keys())
    origen = normalizar_codigo(_valor(fila, "ORG_ORIGEN"))
    destino = normalizar_codigo(_valor(fila, "ORG_DESTINO"))
    tipo_transaccion = normalizar_texto(_valor(fila, "TIPO_TRANSACCION"))
    tipo_origen = normalizar_texto(_valor(fila, "TIPO_ORIGEN"))
    subinventario = normalizar_codigo(_valor(fila, "SUBINVENTARIO"))
    articulo = normalizar_codigo(_valor(fila, "ARTICULO"))
    descripcion = str(_valor(fila, "DESCRIPCION") or "").strip()

    if not origen:
        return _diag("ORG_ORIGEN vacio.", "Validar calidad del archivo fuente o crear regla especifica si este caso es valido.", parcial)
    if not destino:
        return _diag("ORG_DESTINO vacio.", "Validar calidad del archivo fuente o crear regla especifica si este caso es valido.", parcial)
    if conocidas and origen not in conocidas and origen not in internas_archivo:
        return _diag("ORG_ORIGEN parece farmacia externa nueva.", "Revise si la farmacia debe marcarse como externa, interna, CEDI o no clasificable.", parcial)
    if conocidas and origen not in conocidas:
        return _diag("ORG_ORIGEN no existe en historial de farmacias.", "Revise si la farmacia debe registrarse y definir si puede prestar.", parcial)
    if conocidas and destino not in conocidas:
        return _diag("ORG_DESTINO parece farmacia interna nueva.", "Revise si la farmacia debe registrarse como interna de la clinica.", parcial)
    if tipos_transaccion_reglas and tipo_transaccion and tipo_transaccion not in tipos_transaccion_reglas:
        return _diag("TIPO_TRANSACCION no esta contemplado por reglas activas.", "Revise si debe crearse una nueva regla o ajustar una regla existente.", parcial)
    if tipos_origen_reglas and tipo_origen and tipo_origen not in tipos_origen_reglas:
        return _diag("TIPO_ORIGEN no esta contemplado por reglas activas.", "Revise si debe crearse una nueva regla para este origen.", parcial)
    if subinventarios_reglas and subinventario and subinventario not in subinventarios_reglas:
        return _diag("SUBINVENTARIO no coincide con reglas activas.", "Revise si el subinventario debe agregarse a una regla o lista configurable.", parcial)
    if articulo and codigos_listas and articulo not in codigos_listas:
        return _diag("ARTICULO no existe en listas configurables relevantes.", "Revise si el articulo debe agregarse a LIQUIDOS o MCE_CIRUGIA.", parcial)
    if articulo and not descripcion:
        return _diag("ARTICULO sin descripcion.", "Validar descripcion del articulo en el archivo fuente.", parcial)
    if parcial and parcial.regla_candidata:
        parcial.motivo = (
            f"Coincidencia parcial con regla {parcial.regla_candidata}, "
            f"pero no cumple {parcial.condiciones_fallidas}."
        )
        parcial.sugerencia = "Revise las condiciones fallidas de la regla candidata o ajuste catalogos/reglas."
        return parcial
    return DiagnosticoFila(
        motivo="Movimiento no coincide con ninguna regla activa.",
        sugerencia="Revise si debe crearse una regla nueva o ajustar una regla existente.",
    )


def _diagnosticar_reglas_parciales(
    df: pd.DataFrame,
    reglas: list[ReglaMotor],
    evaluador: EvaluadorCondiciones,
    contexto: ContextoMotor,
    sin_clasificar: pd.Series,
) -> dict[int, DiagnosticoFila]:
    indices = df.index[sin_clasificar]
    if len(indices) == 0 or not reglas:
        return {}

    mejor_score = pd.Series(-1, index=indices, dtype="int64")
    mejor_total = pd.Series(0, index=indices, dtype="int64")
    mejor_regla = pd.Series("", index=indices, dtype="object")
    mejor_ok = pd.Series("", index=indices, dtype="object")
    mejor_fail = pd.Series("", index=indices, dtype="object")

    for regla in reglas:
        if not regla.condiciones:
            continue
        resultados: list[tuple[str, pd.Series]] = []
        for condicion in regla.condiciones:
            mascara = evaluador.generar_mascara(
                df,
                condicion.campo,
                condicion.operador,
                condicion.valores,
                condicion.lista_id,
                condicion.atributo_farmacia,
                contexto,
            ).loc[indices].astype(bool)
            resultados.append((condicion.campo, mascara))
        puntaje = sum(mascara.astype(int) for _campo, mascara in resultados)
        total = len(resultados)
        actualizar = puntaje.gt(mejor_score) & puntaje.gt(0)
        if not actualizar.any():
            continue
        for indice in indices[actualizar]:
            cumplidas = [campo for campo, mascara in resultados if bool(mascara.loc[indice])]
            fallidas = [campo for campo, mascara in resultados if not bool(mascara.loc[indice])]
            mejor_score.loc[indice] = int(puntaje.loc[indice])
            mejor_total.loc[indice] = total
            mejor_regla.loc[indice] = regla.nombre
            mejor_ok.loc[indice] = ", ".join(cumplidas)
            mejor_fail.loc[indice] = ", ".join(fallidas)

    diagnosticos: dict[int, DiagnosticoFila] = {}
    for indice in indices:
        if int(mejor_score.loc[indice]) <= 0:
            continue
        total = max(int(mejor_total.loc[indice]), 1)
        diagnosticos[indice] = DiagnosticoFila(
            motivo="",
            sugerencia="",
            regla_candidata=str(mejor_regla.loc[indice]),
            condiciones_cumplidas=str(mejor_ok.loc[indice]),
            condiciones_fallidas=str(mejor_fail.loc[indice]),
            porcentaje=round((int(mejor_score.loc[indice]) / total) * 100, 2),
        )
    return diagnosticos


def asegurar_diagnostico_basico(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Garantiza columnas diagnosticas aun si el DataFrame no paso por el motor nuevo."""
    df = dataframe.copy()
    _asegurar_columnas_base(df)
    sin = df["TIPOLOGIA_FINAL"].fillna(df["TIPOLOGIA_PRELIMINAR"]).astype(str).eq(SIN_CLASIFICAR)
    df["ESTADO_CLASIFICACION"] = "CLASIFICADO"
    df.loc[sin, "ESTADO_CLASIFICACION"] = "SIN_CLASIFICAR_JUSTIFICADO"
    _asegurar_columnas_diagnostico(df)
    faltantes = sin & df["MOTIVO_SIN_CLASIFICAR"].fillna("").astype(str).eq("")
    for indice in df.index[faltantes]:
        diagnostico = diagnosticar_fila(df.loc[indice])
        df.at[indice, "MOTIVO_SIN_CLASIFICAR"] = diagnostico.motivo
        df.at[indice, "SUGERENCIA_ACCION"] = diagnostico.sugerencia
    return df


def _diag(motivo: str, sugerencia: str, parcial: DiagnosticoFila | None) -> DiagnosticoFila:
    if parcial is None:
        return DiagnosticoFila(motivo=motivo, sugerencia=sugerencia)
    parcial.motivo = motivo
    parcial.sugerencia = sugerencia
    return parcial


def _asegurar_columnas_base(df: pd.DataFrame) -> None:
    if "TIPOLOGIA_PRELIMINAR" not in df.columns:
        df["TIPOLOGIA_PRELIMINAR"] = SIN_CLASIFICAR
    if "TIPOLOGIA_FINAL" not in df.columns:
        df["TIPOLOGIA_FINAL"] = df["TIPOLOGIA_PRELIMINAR"]
    for columna in ("REGLA_APLICADA", "REGLA_DERIVADA_APLICADA"):
        if columna not in df.columns:
            df[columna] = ""


def _asegurar_columnas_diagnostico(df: pd.DataFrame) -> None:
    for columna in COLUMNAS_DIAGNOSTICO[1:]:
        if columna == "PORCENTAJE_COINCIDENCIA_REGLA":
            if columna not in df.columns:
                df[columna] = 0.0
            else:
                df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0.0)
            continue
        if columna not in df.columns:
            df[columna] = ""


def _valores_unicos(df: pd.DataFrame, columna: str) -> set[str]:
    columna_real = _resolver_columna(df, columna)
    if columna_real is None:
        return set()
    return {normalizar_codigo(valor) for valor in df[columna_real].dropna().astype(str) if normalizar_codigo(valor)}


def _valores_relevantes_reglas(reglas: list[ReglaMotor]) -> tuple[set[str], set[str], set[str]]:
    transacciones: set[str] = set()
    origenes: set[str] = set()
    subinventarios: set[str] = set()
    for regla in reglas:
        for condicion in regla.condiciones:
            campo = normalizar_nombre_columna(condicion.campo)
            if campo == "TIPO_TRANSACCION":
                transacciones.update(normalizar_texto(valor) for valor in condicion.valores if normalizar_texto(valor))
            elif campo == "TIPO_ORIGEN":
                origenes.update(normalizar_texto(valor) for valor in condicion.valores if normalizar_texto(valor))
            elif campo == "SUBINVENTARIO":
                subinventarios.update(normalizar_codigo(valor) for valor in condicion.valores if normalizar_codigo(valor))
    return transacciones, origenes, subinventarios


def _resolver_columna(df: pd.DataFrame, columna: str) -> str | None:
    columnas = {normalizar_nombre_columna(col): str(col) for col in df.columns}
    return columnas.get(normalizar_nombre_columna(columna))


def _valor(fila: pd.Series, columna: str) -> object:
    for col in fila.index:
        if normalizar_nombre_columna(col) == columna:
            valor = fila[col]
            if pd.isna(valor):
                return ""
            return valor
    return ""


def _es_regla_derivada(regla: ReglaMotor) -> bool:
    return any(condicion.campo in {"TIPOLOGIA", "TIPOLOGIA_PRELIMINAR"} for condicion in regla.condiciones)
