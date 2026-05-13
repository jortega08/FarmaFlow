"""Repositorio de items de listas configurables."""

from __future__ import annotations

from sqlalchemy import select

from persistencia.modelos_orm import ItemLista
from repositorios.repositorio_base import RepositorioBase
from utilidades.texto import normalizar_texto


class RepositorioListaItems(RepositorioBase[ItemLista]):
    """Operaciones especificas para items de listas."""

    modelo = ItemLista

    def crear(self, **campos: object) -> ItemLista:
        if "valor" in campos and "valor_normalizado" not in campos:
            campos["valor_normalizado"] = normalizar_texto(campos["valor"])
        return super().crear(**campos)

    def actualizar(self, id: int, **campos: object) -> ItemLista | None:
        if "valor" in campos and "valor_normalizado" not in campos:
            campos["valor_normalizado"] = normalizar_texto(campos["valor"])
        return super().actualizar(id, **campos)

    def buscar_en_lista(self, lista_id: int, valor: object) -> ItemLista | None:
        valor_normalizado = normalizar_texto(valor)
        consulta = select(ItemLista).where(
            ItemLista.lista_id == lista_id,
            ItemLista.valor_normalizado == valor_normalizado,
        )
        return self.sesion.scalars(consulta).first()

    def listar_activos_por_lista(self, lista_id: int) -> list[ItemLista]:
        consulta = select(ItemLista).where(
            ItemLista.lista_id == lista_id,
            ItemLista.activo.is_(True),
        )
        return list(self.sesion.scalars(consulta).all())

