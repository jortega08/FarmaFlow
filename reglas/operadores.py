"""Operadores de condicion para el motor de reglas avanzado."""

from __future__ import annotations

from enum import StrEnum


class OperadorCondicion(StrEnum):
    """Operadores disponibles en condiciones de reglas."""

    # Coincidencia de texto
    IGUAL = "IGUAL"
    DISTINTO = "DISTINTO"
    CONTIENE = "CONTIENE"
    NO_CONTIENE = "NO_CONTIENE"
    EMPIEZA_POR = "EMPIEZA_POR"
    TERMINA_EN = "TERMINA_EN"
    # Listas configurables
    EN_LISTA = "EN_LISTA"
    NO_EN_LISTA = "NO_EN_LISTA"
    # Presencia de valor
    VACIO = "VACIO"
    NO_VACIO = "NO_VACIO"
    # Atributos de farmacia
    FARMACIA_ES_TIPO = "FARMACIA_ES_TIPO"
    FARMACIA_NO_ES_TIPO = "FARMACIA_NO_ES_TIPO"
    FARMACIA_PUEDE_PRESTAR = "FARMACIA_PUEDE_PRESTAR"
    FARMACIA_NO_PUEDE_PRESTAR = "FARMACIA_NO_PUEDE_PRESTAR"
    # Alias legado — reglas migradas desde JSON; equivale a IGUAL multi-valor
    EN = "EN"


OPERADORES_FARMACIA: frozenset[OperadorCondicion] = frozenset(
    {
        OperadorCondicion.FARMACIA_ES_TIPO,
        OperadorCondicion.FARMACIA_NO_ES_TIPO,
        OperadorCondicion.FARMACIA_PUEDE_PRESTAR,
        OperadorCondicion.FARMACIA_NO_PUEDE_PRESTAR,
    }
)

OPERADORES_LISTA: frozenset[OperadorCondicion] = frozenset(
    {
        OperadorCondicion.EN_LISTA,
        OperadorCondicion.NO_EN_LISTA,
    }
)

_VALORES_VALIDOS: frozenset[str] = frozenset(op.value for op in OperadorCondicion)


def operador_desde_texto(texto: str) -> OperadorCondicion:
    """Convierte un string a OperadorCondicion; devuelve IGUAL si no se reconoce."""
    if texto in _VALORES_VALIDOS:
        return OperadorCondicion(texto)
    return OperadorCondicion.IGUAL
