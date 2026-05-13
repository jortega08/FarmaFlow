"""Utilidades para normalizacion de texto y nombres de columnas."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


CAMPOS_CODIGO = frozenset(
    {
        "TIPO_TRANSACCION",
        "TIPO_ORIGEN",
        "ORG_ORIGEN",
        "ORG_DESTINO",
        "SUBINVENTARIO",
        "ARTICULO",
        "COD_ARTICULO",
        "CODIGO_ARTICULO",
    }
)


def quitar_espacios_repetidos(texto: str) -> str:
    """Colapsa espacios consecutivos y recorta extremos."""
    return re.sub(r"\s+", " ", texto).strip()


def reemplazar_tildes(texto: str) -> str:
    """Elimina tildes y signos diacriticos."""
    texto_normalizado = unicodedata.normalize("NFD", texto)
    return "".join(caracter for caracter in texto_normalizado if unicodedata.category(caracter) != "Mn")


def normalizar_texto(valor: Any) -> str:
    """Normaliza valores de texto para comparaciones funcionales."""
    if valor is None:
        return ""

    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return ""

    texto = reemplazar_tildes(texto)
    texto = quitar_espacios_repetidos(texto)
    return texto.upper()


def normalizar_nombre_columna(valor: Any) -> str:
    """Normaliza encabezados para facilitar deteccion por alias."""
    texto = normalizar_texto(valor)
    texto = re.sub(r"[^A-Z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def normalizar_codigo(valor: Any) -> str:
    """Normaliza codigos catalogados usando guion bajo como separador canonico."""
    texto = normalizar_texto(valor)
    if texto == "*":
        return texto
    texto = re.sub(r"[^A-Z0-9]+", "_", texto)
    texto = re.sub(r"_+", "_", texto).strip("_")
    return texto


def campo_usa_codigo(campo: Any) -> bool:
    """Indica si un campo se compara como codigo catalogado."""
    return normalizar_nombre_columna(campo) in CAMPOS_CODIGO


def normalizar_valor_por_campo(campo: Any, valor: Any) -> str:
    """Normaliza un valor segun el tipo de campo al que pertenece."""
    if campo_usa_codigo(campo):
        return normalizar_codigo(valor)
    return normalizar_texto(valor)


def es_valor_comodin(valor: Any) -> bool:
    """Indica si el valor corresponde al comodin de coincidencia."""
    return normalizar_texto(valor) == "*"
