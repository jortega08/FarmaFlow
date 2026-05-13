"""Casos de uso para listas configurables e items."""

from __future__ import annotations

from sqlalchemy.orm import Session

from dto.lista_dto import (
    ItemListaActualizarDTO,
    ItemListaCrearDTO,
    ItemListaDTO,
    ListaConfigurableActualizarDTO,
    ListaConfigurableCrearDTO,
    ListaConfigurableDTO,
)
from repositorios.repositorio_lista_items import RepositorioListaItems
from repositorios.repositorio_listas import RepositorioListas
from servicios.excepciones import DatoDuplicadoError, EntidadNoEncontradaError, ValidacionDominioError
from servicios.paginacion import contiene_texto, paginar
from utilidades.texto import normalizar_texto


TIPOS_LISTA_PERMITIDOS = {"ARTICULOS", "FARMACIAS", "MOTIVOS", "SUBINVENTARIOS", "ORGANIZACIONES"}


class ServicioListas:
    """Orquesta listas configurables y sus items."""

    def __init__(self, sesion: Session) -> None:
        self._repo_listas = RepositorioListas(sesion)
        self._repo_items = RepositorioListaItems(sesion)

    def crear_lista(self, datos: ListaConfigurableCrearDTO) -> ListaConfigurableDTO:
        self._validar_lista(datos.codigo, datos.nombre, datos.tipo_lista)
        if self._repo_listas.buscar_por_codigo(datos.codigo):
            raise DatoDuplicadoError(f"Ya existe una lista con codigo {datos.codigo}.")

        lista = self._repo_listas.crear(**datos.model_dump())
        return ListaConfigurableDTO.model_validate(lista)

    def listar_listas(self, activa: bool | None = None) -> list[ListaConfigurableDTO]:
        if activa is True:
            listas = self._repo_listas.listar_activas()
        else:
            filtros = {} if activa is None else {"activa": activa}
            listas = self._repo_listas.listar(**filtros)
        return [ListaConfigurableDTO.model_validate(lista) for lista in listas]

    def obtener_lista(self, lista_id: int) -> ListaConfigurableDTO:
        lista = self._repo_listas.obtener(lista_id)
        if lista is None:
            raise EntidadNoEncontradaError(f"No existe la lista con id {lista_id}.")
        return ListaConfigurableDTO.model_validate(lista)

    def obtener_por_codigo(self, codigo: str) -> ListaConfigurableDTO:
        lista = self._repo_listas.buscar_por_codigo(codigo)
        if lista is None:
            raise EntidadNoEncontradaError(f"No existe la lista con codigo {codigo}.")
        return ListaConfigurableDTO.model_validate(lista)

    def obtener_o_error(self, lista_id: int) -> ListaConfigurableDTO:
        return self.obtener_lista(lista_id)

    def actualizar_lista(self, lista_id: int, datos: ListaConfigurableActualizarDTO) -> ListaConfigurableDTO:
        lista_actual = self._repo_listas.obtener(lista_id)
        if lista_actual is None:
            raise EntidadNoEncontradaError(f"No existe la lista con id {lista_id}.")

        campos = datos.model_dump(exclude_none=True)
        if not campos:
            return ListaConfigurableDTO.model_validate(lista_actual)

        codigo = str(campos.get("codigo", lista_actual.codigo))
        nombre = str(campos.get("nombre", lista_actual.nombre))
        tipo_lista = str(campos.get("tipo_lista", lista_actual.tipo_lista))
        self._validar_lista(codigo, nombre, tipo_lista)

        existente = self._repo_listas.buscar_por_codigo(codigo)
        if existente is not None and existente.id != lista_id:
            raise DatoDuplicadoError(f"Ya existe una lista con codigo {codigo}.")

        lista = self._repo_listas.actualizar(lista_id, **campos)
        assert lista is not None
        return ListaConfigurableDTO.model_validate(lista)

    def desactivar_lista(self, lista_id: int) -> ListaConfigurableDTO:
        return self.actualizar_lista(lista_id, ListaConfigurableActualizarDTO(activa=False))

    def agregar_item(self, datos: ItemListaCrearDTO) -> ItemListaDTO:
        if self._repo_listas.obtener(datos.lista_id) is None:
            raise EntidadNoEncontradaError(f"No existe la lista con id {datos.lista_id}.")
        if not datos.valor.strip():
            raise ValidacionDominioError("El valor del item es obligatorio.")
        if self._repo_items.buscar_en_lista(datos.lista_id, datos.valor):
            raise DatoDuplicadoError(f"Ya existe el item {datos.valor} en la lista {datos.lista_id}.")

        item = self._repo_items.crear(**datos.model_dump())
        return ItemListaDTO.model_validate(item)

    def agregar_items_masivo(
        self,
        lista_id: int,
        items: list[ItemListaCrearDTO],
        ignorar_duplicados: bool = True,
    ) -> list[ItemListaDTO]:
        if self._repo_listas.obtener(lista_id) is None:
            raise EntidadNoEncontradaError(f"No existe la lista con id {lista_id}.")

        creados: list[ItemListaDTO] = []
        vistos: set[str] = set()
        for item in items:
            datos = item.model_copy(update={"lista_id": lista_id})
            if not datos.valor.strip():
                raise ValidacionDominioError("El valor del item es obligatorio.")

            valor_normalizado = normalizar_texto(datos.valor)
            duplicado = valor_normalizado in vistos or self._repo_items.buscar_en_lista(lista_id, datos.valor)
            if duplicado:
                if ignorar_duplicados:
                    continue
                raise DatoDuplicadoError(f"Ya existe el item {datos.valor} en la lista {lista_id}.")

            creado = self._repo_items.crear(**datos.model_dump())
            vistos.add(creado.valor_normalizado)
            creados.append(ItemListaDTO.model_validate(creado))
        return creados

    def listar_items(self, lista_id: int, activos: bool | None = None) -> list[ItemListaDTO]:
        if self._repo_listas.obtener(lista_id) is None:
            raise EntidadNoEncontradaError(f"No existe la lista con id {lista_id}.")

        if activos is True:
            items = self._repo_items.listar_activos_por_lista(lista_id)
        else:
            filtros = {"lista_id": lista_id}
            if activos is False:
                filtros["activo"] = False
            items = self._repo_items.listar(**filtros)
        return [ItemListaDTO.model_validate(item) for item in items]

    def listar_items_por_codigo(self, codigo_lista: str, activos: bool | None = None) -> list[ItemListaDTO]:
        lista = self._repo_listas.buscar_por_codigo(codigo_lista)
        if lista is None:
            return []
        return self.listar_items(lista.id, activos=activos)

    def buscar_items(
        self,
        lista_id: int,
        texto: str,
        pagina: int = 1,
        filas_por_pagina: int = 20,
    ) -> list[ItemListaDTO]:
        """Busca items de una lista por codigo, valor o descripcion."""
        if self._repo_listas.obtener(lista_id) is None:
            raise EntidadNoEncontradaError(f"No existe la lista con id {lista_id}.")

        items = sorted(
            self._repo_items.listar(lista_id=lista_id),
            key=lambda item: (item.valor_normalizado, item.id),
        )
        filtrados = [
            ItemListaDTO.model_validate(item)
            for item in items
            if contiene_texto(texto, (item.codigo, item.valor, item.valor_normalizado, item.descripcion))
        ]
        return paginar(filtrados, pagina, filas_por_pagina)

    def actualizar_item(self, item_id: int, datos: ItemListaActualizarDTO) -> ItemListaDTO:
        item_actual = self._repo_items.obtener(item_id)
        if item_actual is None:
            raise EntidadNoEncontradaError(f"No existe el item con id {item_id}.")

        campos = datos.model_dump(exclude_none=True)
        if not campos:
            return ItemListaDTO.model_validate(item_actual)

        if "valor" in campos:
            valor = str(campos["valor"])
            if not valor.strip():
                raise ValidacionDominioError("El valor del item no puede estar vacio.")
            existente = self._repo_items.buscar_en_lista(item_actual.lista_id, valor)
            if existente is not None and existente.id != item_id:
                raise DatoDuplicadoError(f"Ya existe el item {valor} en la lista {item_actual.lista_id}.")

        item = self._repo_items.actualizar(item_id, **campos)
        assert item is not None
        return ItemListaDTO.model_validate(item)

    def desactivar_item(self, item_id: int) -> ItemListaDTO:
        return self.actualizar_item(item_id, ItemListaActualizarDTO(activo=False))

    def eliminar_item(self, item_id: int) -> None:
        if not self._repo_items.eliminar(item_id):
            raise EntidadNoEncontradaError(f"No existe el item con id {item_id}.")

    def _validar_lista(self, codigo: str, nombre: str, tipo_lista: str) -> None:
        if not codigo.strip():
            raise ValidacionDominioError("El codigo de la lista es obligatorio.")
        if not nombre.strip():
            raise ValidacionDominioError("El nombre de la lista es obligatorio.")
        if tipo_lista not in TIPOS_LISTA_PERMITIDOS:
            permitidos = ", ".join(sorted(TIPOS_LISTA_PERMITIDOS))
            raise ValidacionDominioError(f"Tipo de lista no permitido. Use uno de: {permitidos}.")
