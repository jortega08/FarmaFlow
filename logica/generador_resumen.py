"""Funciones auxiliares para resumir y preparar informacion exportable."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

from modelos.resultado_preclasificacion import ResultadoPreclasificacion
from modelos.resultado_validacion import ResultadoValidacion
from utilidades.texto import normalizar_codigo, normalizar_nombre_columna


COLUMNAS_AUXILIARES_EXPORTACION = (
    "FARMACIA_DETECTADA",
    "TIPOLOGIA_PRELIMINAR",
    "TIPOLOGIA_FINAL",
    "REGLA_APLICADA",
    "REGLA_DERIVADA_APLICADA",
)
COLUMNAS_AUXILIARES_REQUERIDAS = (
    "FARMACIA_DETECTADA",
    "TIPOLOGIA_PRELIMINAR",
    "REGLA_APLICADA",
)


def generar_resumen_dataframe(dataframe: pd.DataFrame) -> tuple[int, int, list[str]]:
    """Extrae un resumen simple del contenido leido."""
    cantidad_filas = int(dataframe.shape[0])
    cantidad_columnas = int(dataframe.shape[1])
    columnas = [str(columna) for columna in dataframe.columns.tolist()]
    return cantidad_filas, cantidad_columnas, columnas


def generar_resumen_validacion(resultado: ResultadoValidacion) -> dict[str, object]:
    """Construye un resumen compacto para consumo de interfaz."""
    columnas_mapeadas_por_alias = {
        columna_canonica: columna_original
        for columna_canonica, columna_original in resultado.columnas_mapeadas.items()
        if columna_original != columna_canonica
    }

    return {
        "estructura_valida": resultado.estructura_valida,
        "columnas_encontradas": list(resultado.columnas_encontradas),
        "columnas_faltantes": list(resultado.columnas_faltantes),
        "columnas_mapeadas_por_alias": columnas_mapeadas_por_alias,
        "columnas_desconocidas": list(resultado.columnas_desconocidas),
    }


def generar_resumen_preclasificacion(resultado: ResultadoPreclasificacion) -> dict[str, object]:
    """Genera totales y una tabla cruzada simple para fases posteriores."""
    dataframe_resultado = resultado.dataframe_resultado
    tabla_cruzada = generar_cruce_tipologia_farmacia(dataframe_resultado)

    return {
        "cantidad_registros": resultado.cantidad_registros,
        "cantidad_clasificados": resultado.cantidad_clasificados,
        "cantidad_sin_clasificar": resultado.cantidad_sin_clasificar,
        "cantidad_tipologias_detectadas": len(resultado.tipologias_detectadas),
        "cantidad_farmacias_detectadas": len(resultado.farmacias_detectadas),
        "tipologias_detectadas": dict(resultado.tipologias_detectadas),
        "farmacias_detectadas": dict(resultado.farmacias_detectadas),
        "tabla_cruzada": tabla_cruzada,
    }


def generar_estructuras_exportacion(
    dataframe_original: pd.DataFrame,
    dataframe_procesado: pd.DataFrame,
    listas_articulos: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, pd.DataFrame]:
    """Construye los dataframes necesarios para la exportacion operativa."""
    detalle_clasificado = generar_detalle_clasificado(dataframe_original, dataframe_procesado)
    cruce_tipologia_farmacia = generar_cruce_tipologia_farmacia(detalle_clasificado)
    estructuras = {
        "detalle_clasificado": detalle_clasificado,
        "sin_clasificar": generar_sin_clasificar(detalle_clasificado),
        "resumen_tipologia": generar_resumen_tipologia(detalle_clasificado),
        "resumen_farmacia": generar_resumen_farmacia(detalle_clasificado),
        "cruce_tipologia_farmacia": cruce_tipologia_farmacia,
        "cruce_farmacia_tipologia": cruce_tipologia_farmacia,
    }
    for codigo_lista in ("LIQUIDOS", "MCE_CIRUGIA"):
        codigos = list((listas_articulos or {}).get(codigo_lista, []))
        filtrado = generar_articulos_unicos_por_lista(detalle_clasificado, codigos)
        if not filtrado.empty:
            estructuras[codigo_lista.lower()] = filtrado
    return estructuras


def generar_detalle_clasificado(
    dataframe_original: pd.DataFrame,
    dataframe_procesado: pd.DataFrame,
) -> pd.DataFrame:
    """Genera un detalle exportable manteniendo columnas originales y anexando clasificacion.

    Construye un nuevo DataFrame mediante ``assign`` (sin deep copy del original)
    para evitar duplicar memoria con archivos grandes. ``assign`` retorna una
    instancia nueva sin mutar el dataframe de entrada.
    """
    if dataframe_procesado is None:
        return dataframe_original.copy(deep=False)

    columnas_extra: dict[str, object] = {}
    for columna in COLUMNAS_AUXILIARES_EXPORTACION:
        if columna in dataframe_procesado.columns:
            columnas_extra[columna] = (
                dataframe_procesado[columna]
                .reindex(dataframe_original.index, fill_value="")
                .values
            )
        elif columna in COLUMNAS_AUXILIARES_REQUERIDAS and columna not in dataframe_original.columns:
            columnas_extra[columna] = ""

    if not columnas_extra:
        return dataframe_original.copy(deep=False)
    return dataframe_original.assign(**columnas_extra)


def generar_sin_clasificar(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Filtra registros cuya tipologia permanece sin clasificar."""
    columna_tipologia = _columna_tipologia_exportacion(dataframe)
    if columna_tipologia is None:
        return dataframe.iloc[0:0].copy()

    mascara_sin_clasificar = dataframe[columna_tipologia].fillna("") == "SIN_CLASIFICAR"
    return dataframe.loc[mascara_sin_clasificar].copy()


def generar_resumen_tipologia(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Agrupa el detalle por la tipologia final cuando existe."""
    columna_tipologia = _columna_tipologia_exportacion(dataframe)
    if columna_tipologia is None:
        return pd.DataFrame(columns=["TIPOLOGIA_PRELIMINAR", "CANTIDAD"])

    resumen = (
        dataframe[columna_tipologia]
        .fillna("")
        .value_counts(dropna=False)
        .rename_axis("TIPOLOGIA_PRELIMINAR")
        .reset_index(name="CANTIDAD")
    )
    return resumen


def generar_resumen_farmacia(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Agrupa el detalle por farmacia detectada, excluyendo valores vacios."""
    if "FARMACIA_DETECTADA" not in dataframe.columns:
        return pd.DataFrame(columns=["FARMACIA_DETECTADA", "CANTIDAD"])

    serie_farmacias = dataframe["FARMACIA_DETECTADA"].fillna("").loc[lambda serie: serie != ""]
    if serie_farmacias.empty:
        return pd.DataFrame(columns=["FARMACIA_DETECTADA", "CANTIDAD"])

    resumen = (
        serie_farmacias.value_counts(dropna=False)
        .rename_axis("FARMACIA_DETECTADA")
        .reset_index(name="CANTIDAD")
    )
    return resumen


def generar_cruce_tipologia_farmacia(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    """Construye un cruce entre tipologia final y farmacia detectada."""
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(columns=["TIPOLOGIA_PRELIMINAR"])

    columna_tipologia = _columna_tipologia_exportacion(dataframe)
    if "FARMACIA_DETECTADA" not in dataframe.columns or columna_tipologia is None:
        return pd.DataFrame(columns=["TIPOLOGIA_PRELIMINAR"])

    # pivot_table no muta el dataframe de entrada -> evitar deep copy redundante
    # que duplicaba la memoria con archivos grandes.
    tabla = pd.pivot_table(
        dataframe,
        index=columna_tipologia,
        columns="FARMACIA_DETECTADA",
        values="REGLA_APLICADA" if "REGLA_APLICADA" in dataframe.columns else "FARMACIA_DETECTADA",
        aggfunc="count",
        fill_value=0,
        dropna=False,
    )

    tabla = tabla.loc[tabla.index.fillna("") != ""]
    if "" in tabla.columns:
        tabla = tabla.drop(columns=[""])
    if tabla.empty:
        return pd.DataFrame(columns=["TIPOLOGIA_PRELIMINAR"])

    tabla = tabla.reset_index()
    tabla.columns.name = None
    tabla = tabla.rename(columns={columna_tipologia: "TIPOLOGIA_PRELIMINAR"})
    return tabla


def generar_cruce_farmacia_tipologia(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    """Alias de compatibilidad: ahora retorna tipologias en filas y farmacias en columnas."""
    return generar_cruce_tipologia_farmacia(dataframe)


def generar_detalle_filtrado_por_lista(
    dataframe: pd.DataFrame,
    codigos_articulo: Iterable[str],
    columna_articulo: str = "ARTICULO",
) -> pd.DataFrame:
    """Filtra el detalle por codigos de articulo normalizados."""
    columna_real = _resolver_columna_articulo(dataframe, columna_articulo)
    if columna_real is None:
        return dataframe.iloc[0:0].copy()

    codigos = {normalizar_codigo(codigo) for codigo in codigos_articulo if normalizar_codigo(codigo)}
    if not codigos:
        return dataframe.iloc[0:0].copy()

    serie = dataframe[columna_real].map(normalizar_codigo)
    return dataframe.loc[serie.isin(codigos)].copy()


def generar_articulos_unicos_por_lista(
    dataframe: pd.DataFrame,
    codigos_articulo: Iterable[str],
    columna_articulo: str = "ARTICULO",
) -> pd.DataFrame:
    """Lista articulos unicos de una categoria con codigo, descripcion y conteo."""
    columna_codigo = _resolver_columna_articulo(dataframe, columna_articulo)
    if columna_codigo is None:
        return _dataframe_resumen_articulos_vacio()

    codigos = {normalizar_codigo(codigo) for codigo in codigos_articulo if normalizar_codigo(codigo)}
    if not codigos:
        return _dataframe_resumen_articulos_vacio()

    detalle = generar_detalle_filtrado_por_lista(dataframe, codigos, columna_articulo=columna_articulo)
    return generar_resumen_articulos(detalle, columna_articulo=columna_articulo)


def generar_resumen_articulos(
    dataframe: pd.DataFrame | None,
    columna_articulo: str = "ARTICULO",
) -> pd.DataFrame:
    """Agrupa movimientos por articulo y conserva un conteo total por codigo."""
    if dataframe is None or dataframe.empty:
        return _dataframe_resumen_articulos_vacio()

    columna_codigo = _resolver_columna_articulo(dataframe, columna_articulo)
    if columna_codigo is None:
        return _dataframe_resumen_articulos_vacio()

    columna_descripcion = _resolver_columna_descripcion(dataframe)
    trabajo = dataframe[[columna_codigo]].copy()
    trabajo["CODIGO_NORMALIZADO"] = trabajo[columna_codigo].map(normalizar_codigo)
    trabajo["CODIGO"] = trabajo[columna_codigo].fillna("").astype(str).str.strip()
    if columna_descripcion is not None:
        trabajo["DESCRIPCION"] = dataframe.loc[trabajo.index, columna_descripcion].fillna("").astype(str).str.strip()
    else:
        trabajo["DESCRIPCION"] = ""
    trabajo["CONTEO"] = 1

    trabajo = trabajo[trabajo["CODIGO"] != ""]
    if trabajo.empty:
        return _dataframe_resumen_articulos_vacio()

    trabajo["DESCRIPCION_VACIA"] = trabajo["DESCRIPCION"].eq("")
    trabajo = trabajo.sort_values(["CODIGO_NORMALIZADO", "DESCRIPCION_VACIA", "DESCRIPCION"])
    resumen = (
        trabajo.groupby("CODIGO_NORMALIZADO", as_index=False)
        .agg({"CODIGO": "first", "DESCRIPCION": "first", "CONTEO": "sum"})
        .sort_values("CODIGO_NORMALIZADO")
        .loc[:, ["CODIGO", "DESCRIPCION", "CONTEO"]]
        .reset_index(drop=True)
    )
    resumen["CONTEO"] = resumen["CONTEO"].astype("int64")
    return resumen


def _resolver_columna_articulo(dataframe: pd.DataFrame, preferida: str) -> str | None:
    columnas = {normalizar_nombre_columna(columna): str(columna) for columna in dataframe.columns}
    candidatos = (
        normalizar_nombre_columna(preferida),
        "ARTICULO",
        "CODIGO",
        "COD_ARTICULO",
        "CODIGO_ARTICULO",
        "ITEM",
        "ITEM_CODE",
    )
    for candidato in candidatos:
        if candidato in columnas:
            return columnas[candidato]
    return None


def _resolver_columna_descripcion(dataframe: pd.DataFrame) -> str | None:
    columnas = {normalizar_nombre_columna(columna): str(columna) for columna in dataframe.columns}
    for candidato in ("DESCRIPCION", "DESCRIPCION_ARTICULO", "ITEM_DESCRIPTION"):
        if candidato in columnas:
            return columnas[candidato]
    return None


def _columna_tipologia_exportacion(dataframe: pd.DataFrame) -> str | None:
    if "TIPOLOGIA_FINAL" in dataframe.columns:
        return "TIPOLOGIA_FINAL"
    if "TIPOLOGIA_PRELIMINAR" in dataframe.columns:
        return "TIPOLOGIA_PRELIMINAR"
    return None


def _dataframe_resumen_articulos_vacio() -> pd.DataFrame:
    return pd.DataFrame(columns=["CODIGO", "DESCRIPCION", "CONTEO"])
