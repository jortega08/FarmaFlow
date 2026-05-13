"""Helpers simples de busqueda y paginacion para servicios."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TypeVar

from servicios.excepciones import ValidacionDominioError
from utilidades.texto import normalizar_texto


T = TypeVar("T")


def validar_paginacion(pagina: int, filas_por_pagina: int) -> None:
    """Valida parametros 1-indexed de paginacion."""
    if pagina < 1:
        raise ValidacionDominioError("La pagina debe ser mayor o igual a 1.")
    if filas_por_pagina < 1:
        raise ValidacionDominioError("Las filas por pagina deben ser mayores o iguales a 1.")


def paginar(items: Sequence[T], pagina: int, filas_por_pagina: int) -> list[T]:
    """Retorna una pagina 1-indexed de una secuencia."""
    validar_paginacion(pagina, filas_por_pagina)
    inicio = (pagina - 1) * filas_por_pagina
    fin = inicio + filas_por_pagina
    return list(items[inicio:fin])


def contiene_texto(texto: str, valores: Iterable[object]) -> bool:
    """Indica si el texto normalizado aparece en alguno de los valores."""
    texto_normalizado = normalizar_texto(texto)
    if not texto_normalizado:
        return True
    return any(texto_normalizado in normalizar_texto(valor) for valor in valores)
