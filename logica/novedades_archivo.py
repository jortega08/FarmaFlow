"""Analisis operativo del archivo mensual cargado."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from utilidades.texto import normalizar_codigo, normalizar_nombre_columna, normalizar_texto


@dataclass(slots=True)
class FarmaciaArchivo:
    """Farmacia u organizacion detectada en el archivo actual."""

    codigo: str
    origenes: tuple[str, ...]
    tipo_sugerido: str
    conocida: bool
    nueva: bool
    pendiente_revision: bool
    puede_prestar: bool | None = None
    farmacia_id: int | None = None


@dataclass(slots=True)
class NovedadesArchivo:
    """Resumen de revision mensual para guiar al usuario."""

    internas_detectadas: list[str] = field(default_factory=list)
    externas_detectadas: list[str] = field(default_factory=list)
    farmacias_nuevas: list[str] = field(default_factory=list)
    farmacias_conocidas: list[str] = field(default_factory=list)
    farmacias_pendientes: list[FarmaciaArchivo] = field(default_factory=list)
    farmacias: list[FarmaciaArchivo] = field(default_factory=list)
    articulos_candidatos: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def total_pendientes(self) -> int:
        return len(self.farmacias_pendientes)


def analizar_novedades_archivo(
    dataframe: pd.DataFrame | None,
    farmacias_conocidas: Sequence[Any] | Mapping[str, Any] | None = None,
) -> NovedadesArchivo:
    """Detecta novedades relevantes para el flujo mensual."""
    if dataframe is None or dataframe.empty:
        return NovedadesArchivo()

    conocidas = _mapear_farmacias_conocidas(farmacias_conocidas)
    internas = _valores_unicos_columna(dataframe, "ORG_DESTINO")
    origen = _valores_unicos_columna(dataframe, "ORG_ORIGEN")
    externas = sorted(valor for valor in origen if valor not in set(internas))

    farmacias: list[FarmaciaArchivo] = []
    for codigo in sorted(set(internas) | set(origen)):
        conocida = conocidas.get(codigo)
        origenes = tuple(
            origen_columna
            for origen_columna, valores in (("ORG_DESTINO", internas), ("ORG_ORIGEN", origen))
            if codigo in valores
        )
        tipo = _tipo_sugerido(codigo, en_destino=codigo in internas, conocida=conocida)
        puede_prestar = getattr(conocida, "puede_prestar", None) if conocida is not None else None
        pendiente = (
            conocida is None and codigo in externas
        ) or tipo == "NO_CLASIFICABLE" or puede_prestar is None
        farmacias.append(
            FarmaciaArchivo(
                codigo=codigo,
                origenes=origenes,
                tipo_sugerido=tipo,
                conocida=conocida is not None,
                nueva=conocida is None,
                pendiente_revision=pendiente,
                puede_prestar=puede_prestar,
                farmacia_id=getattr(conocida, "id", None) if conocida is not None else None,
            )
        )

    return NovedadesArchivo(
        internas_detectadas=internas,
        externas_detectadas=externas,
        farmacias_nuevas=[farmacia.codigo for farmacia in farmacias if farmacia.nueva],
        farmacias_conocidas=[farmacia.codigo for farmacia in farmacias if farmacia.conocida],
        farmacias_pendientes=[farmacia for farmacia in farmacias if farmacia.pendiente_revision],
        farmacias=farmacias,
        articulos_candidatos=detectar_articulos_candidatos_revision(dataframe),
    )


def agregar_motivo_probable_sin_clasificar(
    dataframe: pd.DataFrame,
    *,
    farmacias_conocidas: Iterable[str] | None = None,
    reglas_activas: Sequence[Any] | None = None,
    codigos_listas: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Agrega una columna MOTIVO_PROBABLE para registros sin clasificar."""
    if dataframe is None or dataframe.empty:
        return dataframe.copy()

    df = dataframe.copy()
    if "MOTIVO_PROBABLE" in df.columns:
        return df

    conocidas = {normalizar_codigo(valor) for valor in (farmacias_conocidas or []) if normalizar_codigo(valor)}
    tipos_transaccion, tipos_origen = _valores_contemplados_por_reglas(reglas_activas or [])
    listas = {normalizar_codigo(valor) for valor in (codigos_listas or []) if normalizar_codigo(valor)}

    df["MOTIVO_PROBABLE"] = [
        motivo_probable_sin_clasificar(
            fila,
            farmacias_conocidas=conocidas,
            tipos_transaccion=tipos_transaccion,
            tipos_origen=tipos_origen,
            codigos_listas=listas,
        )
        for _, fila in df.iterrows()
    ]
    return df


def motivo_probable_sin_clasificar(
    fila: Mapping[str, Any] | pd.Series,
    *,
    farmacias_conocidas: Iterable[str] | None = None,
    tipos_transaccion: Iterable[str] | None = None,
    tipos_origen: Iterable[str] | None = None,
    codigos_listas: Iterable[str] | None = None,
) -> str:
    """Sugiere una causa legible para un registro sin clasificar."""
    origen = normalizar_codigo(_valor(fila, "ORG_ORIGEN"))
    destino = normalizar_codigo(_valor(fila, "ORG_DESTINO"))
    tipo_transaccion = normalizar_texto(_valor(fila, "TIPO_TRANSACCION"))
    tipo_origen = normalizar_texto(_valor(fila, "TIPO_ORIGEN"))
    articulo = normalizar_codigo(_valor(fila, "ARTICULO"))

    if not origen:
        return "ORG_ORIGEN vacio."
    if not destino:
        return "ORG_DESTINO vacio."

    conocidas = {normalizar_codigo(valor) for valor in (farmacias_conocidas or []) if normalizar_codigo(valor)}
    if conocidas and origen not in conocidas:
        return "ORG_ORIGEN no existe en historial."
    if conocidas and destino not in conocidas:
        return "ORG_DESTINO no existe en historial."

    transacciones = {normalizar_texto(valor) for valor in (tipos_transaccion or []) if normalizar_texto(valor)}
    if transacciones and tipo_transaccion and tipo_transaccion not in transacciones:
        return "TIPO_TRANSACCION no contemplado por reglas activas."

    origenes = {normalizar_texto(valor) for valor in (tipos_origen or []) if normalizar_texto(valor)}
    if origenes and tipo_origen and tipo_origen not in origenes:
        return "TIPO_ORIGEN no contemplado por reglas activas."

    listas = {normalizar_codigo(valor) for valor in (codigos_listas or []) if normalizar_codigo(valor)}
    if listas and articulo and articulo not in listas:
        return "Articulo no existe en listas configurables."

    return "No coincide con ninguna regla activa."


def detectar_articulos_candidatos_revision(dataframe: pd.DataFrame | None, limite: int = 25) -> pd.DataFrame:
    """Sugiere articulos que podrian revisarse para LIQUIDOS o MCE_CIRUGIA."""
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(columns=["CODIGO", "DESCRIPCION", "CONTEO", "MOTIVO"])

    columna_codigo = _resolver_columna(dataframe, "ARTICULO")
    if columna_codigo is None:
        return pd.DataFrame(columns=["CODIGO", "DESCRIPCION", "CONTEO", "MOTIVO"])
    columna_descripcion = _resolver_columna(dataframe, "DESCRIPCION")

    trabajo = dataframe[[columna_codigo]].copy()
    trabajo["CODIGO"] = trabajo[columna_codigo].map(normalizar_codigo)
    if columna_descripcion is not None:
        trabajo["DESCRIPCION"] = dataframe[columna_descripcion].fillna("").astype(str).str.strip()
    else:
        trabajo["DESCRIPCION"] = ""
    trabajo = trabajo[trabajo["CODIGO"] != ""]
    if trabajo.empty:
        return pd.DataFrame(columns=["CODIGO", "DESCRIPCION", "CONTEO", "MOTIVO"])

    texto = trabajo["DESCRIPCION"].map(normalizar_texto)
    mascara_liquidos = texto.str.contains("LIQUID|SOLUCION|AGUA|SUERO|LACTATO|DEXTROSA", regex=True, na=False)
    mascara_mce = texto.str.contains("MCE|CIRUG|SUTURA|CATETER|CANULA|GUANTE|SONDA", regex=True, na=False)
    candidatos = trabajo[mascara_liquidos | mascara_mce].copy()
    if candidatos.empty:
        return pd.DataFrame(columns=["CODIGO", "DESCRIPCION", "CONTEO", "MOTIVO"])
    candidatos["MOTIVO"] = [
        "Posible liquido" if es_liquido else "Posible MCE/CIRUGIA"
        for es_liquido in mascara_liquidos.loc[candidatos.index].tolist()
    ]
    resumen = (
        candidatos.groupby(["CODIGO", "DESCRIPCION", "MOTIVO"], dropna=False)
        .size()
        .reset_index(name="CONTEO")
        .sort_values(["CONTEO", "CODIGO"], ascending=[False, True])
        .head(limite)
    )
    return resumen.loc[:, ["CODIGO", "DESCRIPCION", "CONTEO", "MOTIVO"]].reset_index(drop=True)


def _valores_unicos_columna(dataframe: pd.DataFrame, columna: str) -> list[str]:
    columna_real = _resolver_columna(dataframe, columna)
    if columna_real is None:
        return []
    serie = dataframe[columna_real].dropna().astype(str).str.strip()
    return sorted({normalizar_codigo(valor) for valor in serie if normalizar_codigo(valor)})


def _resolver_columna(dataframe: pd.DataFrame, columna: str) -> str | None:
    columnas = {normalizar_nombre_columna(col): str(col) for col in dataframe.columns}
    return columnas.get(normalizar_nombre_columna(columna))


def _mapear_farmacias_conocidas(farmacias: Sequence[Any] | Mapping[str, Any] | None) -> dict[str, Any]:
    if farmacias is None:
        return {}
    if isinstance(farmacias, Mapping):
        return {normalizar_codigo(codigo): valor for codigo, valor in farmacias.items() if normalizar_codigo(codigo)}
    resultado: dict[str, Any] = {}
    for farmacia in farmacias:
        codigo = normalizar_codigo(getattr(farmacia, "codigo", ""))
        if codigo:
            resultado[codigo] = farmacia
    return resultado


def _tipo_sugerido(codigo: str, *, en_destino: bool, conocida: Any | None) -> str:
    if conocida is not None:
        if getattr(conocida, "es_interna", False):
            return "INTERNA"
        if getattr(conocida, "es_externa", False):
            return "EXTERNA"
    if en_destino:
        return "INTERNA"
    texto = normalizar_texto(codigo)
    if "CEDI" in texto:
        return "CEDI"
    if "REEMPAQUE" in texto or "REENVASE" in texto:
        return "REEMPAQUE"
    if "DEVOL" in texto:
        return "DEVOLUCIONES"
    if "ALMACEN" in texto:
        return "ALMACEN"
    if "FARM" in texto:
        return "EXTERNA"
    return "NO_CLASIFICABLE"


def _valores_contemplados_por_reglas(reglas: Sequence[Any]) -> tuple[set[str], set[str]]:
    transacciones: set[str] = set()
    origenes: set[str] = set()
    for regla in reglas:
        condiciones = _condiciones_regla(regla)
        for condicion in condiciones:
            campo = normalizar_nombre_columna(_valor_condicion(condicion, "campo"))
            valores = _valores_condicion(condicion)
            if campo == "TIPO_TRANSACCION":
                transacciones.update(normalizar_texto(valor) for valor in valores if normalizar_texto(valor))
            elif campo == "TIPO_ORIGEN":
                origenes.update(normalizar_texto(valor) for valor in valores if normalizar_texto(valor))
    return transacciones, origenes


def _condiciones_regla(regla: Any) -> list[Any]:
    if isinstance(regla, Mapping):
        condiciones = regla.get("condiciones", {})
        if isinstance(condiciones, Mapping):
            return [
                {"campo": campo, "valor": valor}
                for campo, valor in condiciones.items()
            ]
        return list(condiciones or [])
    return list(getattr(regla, "condiciones", []) or [])


def _valor_condicion(condicion: Any, clave: str) -> Any:
    if isinstance(condicion, Mapping):
        return condicion.get(clave, "")
    return getattr(condicion, clave, "")


def _valores_condicion(condicion: Any) -> list[str]:
    valor = _valor_condicion(condicion, "valor")
    if isinstance(valor, Mapping):
        valor = valor.get("valor", "")
    if valor in (None, ""):
        valor = _valor_condicion(condicion, "valor_texto")
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, Iterable):
        return [str(item) for item in valor]
    return []


def _valor(fila: Mapping[str, Any] | pd.Series, columna: str) -> Any:
    if isinstance(fila, pd.Series):
        for col in fila.index:
            if normalizar_nombre_columna(col) == columna:
                return fila[col]
        return ""
    for col, valor in fila.items():
        if normalizar_nombre_columna(col) == columna:
            return valor
    return ""
