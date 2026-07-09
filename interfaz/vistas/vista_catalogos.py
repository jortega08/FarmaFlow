"""Vista administrativa de catalogos del sistema."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from interfaz.componentes.dialogo_editar_lista import DialogoEditarLista
from persistencia.conexion import sesion_scope
from servicios.servicio_farmacias import ServicioFarmacias
from servicios.servicio_listas import ServicioListas
from servicios.servicio_tipos_farmacia import ServicioTiposFarmacia


_CATALOGOS_BASE: tuple[tuple[str, str], ...] = (
    ("FARMACIAS", "Farmacias"),
    ("TIPOS_FARMACIA", "Tipos de farmacia"),
    ("LISTAS", "Listas configurables"),
    ("LIQUIDOS", "Articulos liquidos"),
    ("MCE_CIRUGIA", "Articulos MCE/CIRUGIA"),
    ("ORGANIZACIONES", "Organizaciones"),
    ("MOTIVOS_SUBINVENTARIOS", "Motivos / Subinventarios"),
)


class VistaCatalogos(QWidget):
    """Panel administrativo para revisar listas, farmacias y catalogos base."""

    cambios_configuracion = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._catalogo_actual = "LISTAS"
        self._listas = []
        self._items_lista = []
        self._construir_ui()
        self.recargar()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorVista")
        layout_c = QVBoxLayout(contenedor)
        layout_c.setContentsMargins(24, 24, 24, 24)
        layout_c.setSpacing(16)

        layout_c.addWidget(self._crear_titulo())
        layout_c.addWidget(self._crear_splitter(), 1)

        scroll.setWidget(contenedor)
        layout.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)
        titulo = QLabel("Catalogos")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Revise farmacias, tipos y listas configurables. Los cambios quedan pendientes hasta reprocesar."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        return card

    def _crear_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._crear_panel_catalogos())
        splitter.addWidget(self._crear_panel_detalle())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 780])
        return splitter

    def _crear_panel_catalogos(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        titulo = QLabel("Catalogos disponibles")
        titulo.setObjectName("tituloSubpanel")
        layout.addWidget(titulo)
        self._lista_catalogos = QListWidget()
        self._lista_catalogos.itemSelectionChanged.connect(self._al_seleccionar_catalogo)
        for codigo, nombre in _CATALOGOS_BASE:
            item = QListWidgetItem(nombre)
            item.setData(Qt.UserRole, codigo)
            self._lista_catalogos.addItem(item)
        layout.addWidget(self._lista_catalogos, 1)
        return card

    def _crear_panel_detalle(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        cab = QHBoxLayout()
        self._lbl_titulo_detalle = QLabel("Listas configurables")
        self._lbl_titulo_detalle.setObjectName("tituloSubpanel")
        self._btn_editar_lista = QPushButton("Editar lista seleccionada")
        self._btn_editar_lista.setObjectName("botonSecundario")
        self._btn_editar_lista.setMinimumHeight(38)
        self._btn_editar_lista.clicked.connect(self._editar_lista_actual)
        cab.addWidget(self._lbl_titulo_detalle)
        cab.addStretch(1)
        cab.addWidget(self._btn_editar_lista)
        layout.addLayout(cab)

        filtros = QGridLayout()
        self._buscador = QLineEdit()
        self._buscador.setPlaceholderText("Buscar por codigo, descripcion o tipo")
        self._buscador.textChanged.connect(self._actualizar_tabla)
        self._combo_tipo = ComboScrollSafe()
        self._combo_tipo.addItem("Todos los tipos", None)
        self._combo_tipo.currentIndexChanged.connect(self._actualizar_tabla)
        self._check_activos = QCheckBox("Solo activos")
        self._check_activos.setChecked(True)
        self._check_activos.toggled.connect(self._actualizar_tabla)
        filtros.addWidget(QLabel("Busqueda"), 0, 0)
        filtros.addWidget(QLabel("Tipo"), 0, 1)
        filtros.addWidget(self._buscador, 1, 0)
        filtros.addWidget(self._combo_tipo, 1, 1)
        filtros.addWidget(self._check_activos, 1, 2)
        filtros.setColumnStretch(0, 2)
        filtros.setColumnStretch(1, 1)
        layout.addLayout(filtros)

        self._lbl_info_lista = QLabel("Seleccione un catalogo para revisar su contenido.")
        self._lbl_info_lista.setObjectName("textoSecundario")
        self._lbl_info_lista.setWordWrap(True)
        layout.addWidget(self._lbl_info_lista)

        self._tabla = QTableWidget(0, 5)
        self._tabla.setHorizontalHeaderLabels(["CODIGO", "DESCRIPCION / NOMBRE", "VALOR NORMALIZADO", "ESTADO", "ACCIONES"])
        encabezado = self._tabla.horizontalHeader()
        encabezado.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        encabezado.setSectionResizeMode(1, QHeaderView.Stretch)
        encabezado.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        encabezado.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        encabezado.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setMinimumHeight(340)
        layout.addWidget(self._tabla, 1)
        return card

    def recargar(self) -> None:
        self._listas = []
        try:
            with sesion_scope() as sesion:
                self._listas = ServicioListas(sesion).listar_listas(activa=None)
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar listas: %s", error)
        self._llenar_combo_tipos()
        if self._lista_catalogos.count() and not self._lista_catalogos.selectedItems():
            self._lista_catalogos.setCurrentRow(2)
        self._actualizar_tabla()

    def _llenar_combo_tipos(self) -> None:
        actual = self._combo_tipo.currentData()
        self._combo_tipo.blockSignals(True)
        self._combo_tipo.clear()
        self._combo_tipo.addItem("Todos los tipos", None)
        for tipo in sorted({getattr(lista, "tipo_lista", "") for lista in self._listas if getattr(lista, "tipo_lista", "")}):
            self._combo_tipo.addItem(tipo, tipo)
        indice = self._combo_tipo.findData(actual)
        if indice >= 0:
            self._combo_tipo.setCurrentIndex(indice)
        self._combo_tipo.blockSignals(False)

    def _al_seleccionar_catalogo(self) -> None:
        items = self._lista_catalogos.selectedItems()
        if items:
            self._catalogo_actual = str(items[0].data(Qt.UserRole))
        self._actualizar_tabla()

    def _actualizar_tabla(self, *_args: Any) -> None:
        codigo = self._catalogo_actual
        es_lista_configurable = self._es_codigo_lista(codigo)
        self._btn_editar_lista.setVisible(codigo == "LISTAS" or es_lista_configurable)
        if codigo == "FARMACIAS":
            self._cargar_tabla_farmacias()
        elif codigo == "TIPOS_FARMACIA":
            self._cargar_tabla_tipos()
        elif es_lista_configurable:
            self._cargar_tabla_items_lista(codigo)
        elif codigo == "LISTAS":
            self._cargar_tabla_listas()
        else:
            self._tabla.setRowCount(0)
            self._lbl_titulo_detalle.setText(self._nombre_catalogo(codigo))
            self._lbl_info_lista.setText("Catalogo preparado para extension. No hay items registrados aun.")

    def _cargar_tabla_listas(self) -> None:
        self._lbl_titulo_detalle.setText("Listas configurables")
        texto = self._buscador.text().strip().lower()
        tipo = self._combo_tipo.currentData()
        solo_activos = self._check_activos.isChecked()
        filas = [
            lista
            for lista in self._listas
            if (not solo_activos or lista.activa)
            and (tipo is None or lista.tipo_lista == tipo)
            and (not texto or texto in f"{lista.codigo} {lista.nombre} {lista.tipo_lista} {lista.descripcion or ''}".lower())
        ]
        self._lbl_info_lista.setText(f"{len(filas)} listas visibles. Seleccione LIQUIDOS o MCE_CIRUGIA para editar items.")
        self._tabla.setRowCount(len(filas))
        for fila, lista in enumerate(filas):
            valores = [lista.codigo, lista.nombre, lista.tipo_lista, "Activa" if lista.activa else "Inactiva", "Abrir"]
            self._llenar_fila(
                valores,
                fila,
                accion=lambda _checked=False, codigo=lista.codigo: self._abrir_lista(codigo),
            )

    def _cargar_tabla_items_lista(self, codigo_lista: str) -> None:
        self._lbl_titulo_detalle.setText(self._nombre_catalogo(codigo_lista))
        try:
            with sesion_scope() as sesion:
                items = ServicioListas(sesion).listar_items_por_codigo(codigo_lista, activos=None)
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar items de %s: %s", codigo_lista, error)
            items = []
        texto = self._buscador.text().strip().lower()
        solo_activos = self._check_activos.isChecked()
        filas = [
            item
            for item in items
            if (not solo_activos or item.activo)
            and (not texto or texto in f"{item.codigo or ''} {item.valor} {item.descripcion or ''}".lower())
        ]
        self._lbl_info_lista.setText(
            f"Lista {codigo_lista}: codigo, descripcion/nombre, valor normalizado y estado. "
            "Guardar cambios aqui no reprocesa automaticamente."
        )
        self._tabla.setRowCount(len(filas))
        for fila, item in enumerate(filas):
            valores = [
                item.codigo or item.valor,
                item.descripcion or item.valor,
                item.valor_normalizado,
                "Activo" if item.activo else "Inactivo",
                "Editar",
            ]
            self._llenar_fila(valores, fila, accion=self._editar_lista_actual)

    def _cargar_tabla_farmacias(self) -> None:
        self._lbl_titulo_detalle.setText("Farmacias")
        try:
            with sesion_scope() as sesion:
                farmacias = ServicioFarmacias(sesion).listar_farmacias(activa=None)
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar farmacias: %s", error)
            farmacias = []
        texto = self._buscador.text().strip().lower()
        solo_activos = self._check_activos.isChecked()
        filas = [
            farmacia
            for farmacia in farmacias
            if (not solo_activos or farmacia.activa)
            and (not texto or texto in f"{farmacia.codigo} {farmacia.nombre_original}".lower())
        ]
        self._lbl_info_lista.setText(f"{len(filas)} farmacias visibles.")
        self._tabla.setRowCount(len(filas))
        for fila, farmacia in enumerate(filas):
            tipo = "Interna" if farmacia.es_interna else "Externa" if farmacia.es_externa else "Pendiente"
            valores = [
                farmacia.codigo,
                farmacia.nombre_original,
                tipo,
                "Activa" if farmacia.activa else "Inactiva",
                "Editar",
            ]
            self._llenar_fila(valores, fila)

    def _cargar_tabla_tipos(self) -> None:
        self._lbl_titulo_detalle.setText("Tipos de farmacia")
        try:
            with sesion_scope() as sesion:
                tipos = ServicioTiposFarmacia(sesion).listar_tipos()
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar tipos de farmacia: %s", error)
            tipos = []
        self._lbl_info_lista.setText(f"{len(tipos)} tipos disponibles.")
        self._tabla.setRowCount(len(tipos))
        for fila, tipo in enumerate(tipos):
            valores = [tipo.codigo, tipo.nombre, tipo.descripcion or "", "Activo", "Referencia"]
            self._llenar_fila(valores, fila)

    def _llenar_fila(
        self,
        valores: list[str],
        fila: int,
        accion: Callable[[], None] | None = None,
    ) -> None:
        for columna, valor in enumerate(valores):
            item = QTableWidgetItem(str(valor))
            item.setToolTip(str(valor))
            item.setTextAlignment(Qt.AlignCenter if columna in (0, 3, 4) else Qt.AlignVCenter)
            self._tabla.setItem(fila, columna, item)
        if accion is not None:
            boton = QPushButton(str(valores[4]))
            boton.setObjectName("botonTabla")
            boton.setMinimumHeight(26)
            boton.clicked.connect(lambda _checked=False, callback=accion: callback())
            self._tabla.setCellWidget(fila, 4, self._centrar(boton))
            self._tabla.setRowHeight(fila, 36)

    def _abrir_lista(self, codigo_lista: str) -> None:
        if not self._es_codigo_lista(codigo_lista):
            return
        self._catalogo_actual = codigo_lista
        self._tabla.clearSelection()
        self._actualizar_tabla()

    def _editar_lista_actual(self) -> None:
        codigo = self._catalogo_actual
        lista = None
        if self._es_codigo_lista(codigo):
            lista = next((item for item in self._listas if item.codigo == codigo), None)
        elif codigo == "LISTAS":
            fila = self._tabla.currentRow()
            item_codigo = self._tabla.item(fila, 0) if fila >= 0 else None
            if item_codigo is not None:
                lista = next((item for item in self._listas if item.codigo == item_codigo.text()), None)
        if lista is None:
            return
        dialogo = DialogoEditarLista(lista, self)
        dialogo.exec()
        if dialogo.hubo_cambios():
            self.cambios_configuracion.emit("listas")
        self.recargar()

    def _es_codigo_lista(self, codigo: str) -> bool:
        return any(lista.codigo == codigo for lista in self._listas)

    @staticmethod
    def _centrar(widget: QWidget) -> QWidget:
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.addWidget(widget)
        return contenedor

    @staticmethod
    def _nombre_catalogo(codigo: str) -> str:
        return next((nombre for clave, nombre in _CATALOGOS_BASE if clave == codigo), codigo)
