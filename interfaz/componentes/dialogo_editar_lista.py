"""Dialogo para editar items de una lista configurable."""

from __future__ import annotations

import re
from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dto.lista_dto import ItemListaCrearDTO, ItemListaDTO, ListaConfigurableDTO
from persistencia.conexion import sesion_scope
from servicios.excepciones import ErrorDominio
from servicios.servicio_listas import ServicioListas
from utilidades.texto import normalizar_codigo


class DialogoEditarLista(QDialog):
    """Permite agregar y eliminar items de una lista."""

    cambios_realizados = Signal()

    def __init__(self, lista: ListaConfigurableDTO, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lista = lista
        self._items: list[ItemListaDTO] = []
        self._hubo_cambios = False

        self.setWindowTitle(f"Editar lista - {lista.nombre}")
        self.setMinimumWidth(620)
        self.setMinimumHeight(520)

        self._construir_ui()
        self._cargar_items()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        titulo = QLabel(self._lista.nombre)
        titulo.setObjectName("tituloSubpanel")
        layout.addWidget(titulo)

        detalle = QLabel(f"{self._lista.codigo} - {self._lista.tipo_lista}")
        detalle.setObjectName("textoSecundario")
        layout.addWidget(detalle)

        layout.addWidget(self._crear_tabla(), 1)
        layout.addWidget(self._crear_panel_agregar())
        layout.addWidget(self._crear_botones())

    def _crear_tabla(self) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self._tabla = QTableWidget(0, 4)
        self._tabla.setHorizontalHeaderLabels(["CODIGO", "DESCRIPCION / NOMBRE", "ESTADO", "ACCIONES"])
        encabezado = self._tabla.horizontalHeader()
        encabezado.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        encabezado.setSectionResizeMode(1, QHeaderView.Stretch)
        encabezado.setSectionResizeMode(2, QHeaderView.Fixed)
        encabezado.setSectionResizeMode(3, QHeaderView.Fixed)
        self._tabla.setColumnWidth(2, 82)
        self._tabla.setColumnWidth(3, 96)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionMode(QAbstractItemView.NoSelection)
        self._tabla.setAlternatingRowColors(True)
        layout.addWidget(self._tabla)
        return card

    def _crear_panel_agregar(self) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        etiqueta = QLabel("Agregar codigos y descripcion")
        etiqueta.setObjectName("tituloBloque")
        self._entrada_items = QPlainTextEdit()
        self._entrada_items.setPlaceholderText(
            "Pegue codigos separados por coma o en lineas distintas.\n"
            "Opcional: CODIGO | descripcion del articulo."
        )
        self._entrada_items.setMinimumHeight(86)

        boton = QPushButton("Agregar")
        boton.setObjectName("botonPrincipal")
        boton.setMinimumHeight(38)
        boton.clicked.connect(self._agregar_items)

        layout.addWidget(etiqueta)
        layout.addWidget(self._entrada_items)
        layout.addWidget(boton, alignment=Qt.AlignRight)
        return card

    def _crear_botones(self) -> QDialogButtonBox:
        botones = QDialogButtonBox()
        cerrar = botones.addButton("Cerrar", QDialogButtonBox.AcceptRole)
        cerrar.setObjectName("botonPrincipal")
        cerrar.setMinimumHeight(38)
        cerrar.clicked.connect(self.accept)
        return botones

    def _cargar_items(self) -> None:
        try:
            with sesion_scope() as sesion:
                self._items = ServicioListas(sesion).listar_items(self._lista.id, activos=True)
        except Exception:  # noqa: BLE001
            self._items = []
        self._actualizar_tabla()

    def _actualizar_tabla(self) -> None:
        self._tabla.setRowCount(0)
        for fila, item in enumerate(sorted(self._items, key=lambda x: (x.valor_normalizado, x.id))):
            self._tabla.insertRow(fila)
            self._tabla.setItem(fila, 0, QTableWidgetItem(item.codigo or ""))
            self._tabla.setItem(fila, 1, QTableWidgetItem(item.descripcion or item.valor))
            self._tabla.setItem(fila, 2, QTableWidgetItem("Activo" if item.activo else "Inactivo"))
            eliminar = QPushButton("Eliminar")
            eliminar.setObjectName("botonTablaPeligro")
            eliminar.setFixedHeight(26)
            eliminar.clicked.connect(lambda _checked=False, item_id=item.id: self._eliminar_item(item_id))
            self._tabla.setCellWidget(fila, 3, self._centrar(eliminar))
            self._tabla.setRowHeight(fila, 34)

    def _agregar_items(self) -> None:
        items = list(self._parsear_items(self._entrada_items.toPlainText()))
        if not items:
            return
        try:
            with sesion_scope() as sesion:
                ServicioListas(sesion).agregar_items_masivo(
                    self._lista.id,
                    [
                        ItemListaCrearDTO(
                            lista_id=self._lista.id,
                            codigo=codigo,
                            valor=codigo,
                            descripcion=descripcion or None,
                        )
                        for codigo, descripcion in items
                    ],
                    ignorar_duplicados=True,
                )
        except ErrorDominio as error:
            QMessageBox.warning(self, "No fue posible agregar items", str(error))
            return
        self._entrada_items.clear()
        self._hubo_cambios = True
        self.cambios_realizados.emit()
        self._cargar_items()
        QMessageBox.information(
            self,
            "Items agregados",
            f"Se agregaron {len(items)} item(s) a la lista.",
        )

    def _eliminar_item(self, item_id: int) -> None:
        confirmacion = QMessageBox.question(
            self,
            "Eliminar item",
            "El item se eliminara de la lista. Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        try:
            with sesion_scope() as sesion:
                ServicioListas(sesion).eliminar_item(item_id)
        except ErrorDominio as error:
            QMessageBox.warning(self, "No fue posible eliminar el item", str(error))
            return
        self._cargar_items()
        self._hubo_cambios = True
        self.cambios_realizados.emit()
        QMessageBox.information(self, "Item eliminado", "El item se elimino correctamente.")

    def hubo_cambios(self) -> bool:
        return self._hubo_cambios

    @staticmethod
    def _parsear_items(texto: str) -> Iterable[tuple[str, str]]:
        vistos: set[str] = set()
        for parte in re.split(r"[\n,;]+", texto):
            fragmentos = [frag.strip() for frag in re.split(r"\s*\|\s*", parte, maxsplit=1)]
            codigo = normalizar_codigo(fragmentos[0] if fragmentos else "")
            descripcion = fragmentos[1].strip() if len(fragmentos) > 1 else ""
            if codigo and codigo not in vistos:
                vistos.add(codigo)
                yield codigo, descripcion

    @staticmethod
    def _parsear_codigos(texto: str) -> Iterable[str]:
        for codigo, _descripcion in DialogoEditarLista._parsear_items(texto):
            yield codigo

    @staticmethod
    def _centrar(widget: QWidget) -> QWidget:
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.addWidget(widget)
        return contenedor
