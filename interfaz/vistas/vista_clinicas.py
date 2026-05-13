"""Vista dashboard de clinicas: resumen y historial de ejecuciones por clinica."""

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dto.clinica_dto import ClinicaDTO
from dto.ejecucion_dto import EjecucionDTO
from dto.farmacia_dto import FarmaciaDTO
from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from interfaz.componentes.tarjeta_metrica import TarjetaMetrica
from persistencia.conexion import sesion_scope
from servicios.servicio_clinicas import ServicioClinicas
from servicios.servicio_ejecuciones import ServicioEjecuciones


_ESTADOS_FILTRO: tuple[tuple[str, str], ...] = (
    ("TODOS", "Todos los estados"),
    ("CLASIFICADA", "Clasificada"),
    ("EXPORTADA", "Exportada"),
    ("VALIDADA", "Validada"),
    ("INICIADA", "Iniciada"),
    ("ERROR", "Error"),
    ("CANCELADA", "Cancelada"),
)


class VistaClinicas(QWidget):
    """Dashboard que muestra clinicas registradas y su historial de ejecuciones."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._clinicas: list[ClinicaDTO] = []
        self._ejecuciones: list[EjecucionDTO] = []
        self._farmacias_clinica: list[FarmaciaDTO] = []
        self._ejecuciones_por_clinica: dict[int, list[EjecucionDTO]] = {}
        self._clinica_seleccionada: ClinicaDTO | None = None

        self._construir_ui()
        self.recargar()

    # ------------------------------------------------------------------
    # Construccion
    # ------------------------------------------------------------------

    def _construir_ui(self) -> None:
        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorVista")
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)

        layout.addWidget(self._crear_titulo())
        layout.addLayout(self._crear_layout_principal(), 1)

        scroll.setWidget(contenedor)
        layout_raiz.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        icono = QLabel("CL")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(50, 50)
        icono.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setSpacing(4)
        titulo = QLabel("Dashboard de Clinicas")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Consulte las clinicas registradas, sus farmacias asociadas y el historial de exportaciones."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)

        layout.addWidget(icono)
        layout.addLayout(textos, 1)

        boton_recargar = QPushButton("Recargar")
        boton_recargar.setObjectName("botonSecundario")
        boton_recargar.setMinimumHeight(38)
        boton_recargar.clicked.connect(self.recargar)
        layout.addWidget(boton_recargar)
        return card

    def _crear_layout_principal(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(self._crear_panel_clinicas(), 1)
        layout.addWidget(self._crear_panel_dashboard(), 3)
        return layout

    def _crear_panel_clinicas(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        encabezado = QLabel("Clinicas registradas")
        encabezado.setObjectName("tituloSubpanel")
        layout.addWidget(encabezado)

        self._buscador = QLineEdit()
        self._buscador.setPlaceholderText("Buscar clinica")
        self._buscador.textChanged.connect(self._filtrar_clinicas)
        layout.addWidget(self._buscador)

        self._lista_clinicas = QListWidget()
        self._lista_clinicas.itemSelectionChanged.connect(self._al_seleccionar_clinica)
        layout.addWidget(self._lista_clinicas, 1)

        self._lbl_total_clinicas = QLabel("Sin clinicas registradas")
        self._lbl_total_clinicas.setObjectName("textoSecundario")
        layout.addWidget(self._lbl_total_clinicas)
        return card

    def _crear_panel_dashboard(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._crear_estado_vacio())
        self._stack.addWidget(self._crear_dashboard_clinica())
        layout.addWidget(self._stack)
        return card

    def _crear_estado_vacio(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 32, 0, 32)
        layout.addStretch(1)

        icono = QLabel("CL")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(60, 60)
        icono.setAlignment(Qt.AlignCenter)
        contenedor = QHBoxLayout()
        contenedor.addStretch(1)
        contenedor.addWidget(icono)
        contenedor.addStretch(1)
        layout.addLayout(contenedor)

        titulo = QLabel("Seleccione una clinica")
        titulo.setObjectName("tituloSubpanel")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)

        descripcion = QLabel(
            "Elija una clinica de la lista para ver su resumen, farmacias asociadas\n"
            "y el historial de exportaciones realizadas."
        )
        descripcion.setObjectName("textoSecundario")
        descripcion.setAlignment(Qt.AlignCenter)
        descripcion.setWordWrap(True)
        layout.addWidget(descripcion)

        layout.addStretch(2)
        return widget

    def _crear_dashboard_clinica(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._lbl_clinica_titulo = QLabel("")
        self._lbl_clinica_titulo.setObjectName("tituloSeccion")
        layout.addWidget(self._lbl_clinica_titulo)

        self._lbl_clinica_subtitulo = QLabel("")
        self._lbl_clinica_subtitulo.setObjectName("textoSecundario")
        layout.addWidget(self._lbl_clinica_subtitulo)

        # Tarjetas metricas
        metricas = QHBoxLayout()
        metricas.setSpacing(10)
        self._tm_ejecuciones = TarjetaMetrica("Ejecuciones", "0")
        self._tm_exportaciones = TarjetaMetrica("Exportaciones", "0")
        self._tm_farmacias = TarjetaMetrica("Farmacias", "0")
        self._tm_clasificados = TarjetaMetrica("Movimientos clasificados", "0")
        metricas.addWidget(self._tm_ejecuciones)
        metricas.addWidget(self._tm_exportaciones)
        metricas.addWidget(self._tm_farmacias)
        metricas.addWidget(self._tm_clasificados)
        layout.addLayout(metricas)

        # Farmacias asociadas
        layout.addWidget(self._crear_panel_farmacias())

        # Historial
        layout.addWidget(self._crear_panel_historial(), 1)
        return widget

    def _crear_panel_farmacias(self) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        encabezado = QLabel("Farmacias asociadas")
        encabezado.setObjectName("tituloBloque")
        layout.addWidget(encabezado)

        self._lbl_farmacias = QLabel("Sin farmacias asociadas a esta clinica.")
        self._lbl_farmacias.setObjectName("textoSecundario")
        self._lbl_farmacias.setWordWrap(True)
        layout.addWidget(self._lbl_farmacias)
        return card

    def _crear_panel_historial(self) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        cab = QHBoxLayout()
        encabezado = QLabel("Historial de ejecuciones")
        encabezado.setObjectName("tituloBloque")
        cab.addWidget(encabezado)
        cab.addStretch(1)

        self._combo_estado = ComboScrollSafe()
        for clave, etiqueta in _ESTADOS_FILTRO:
            self._combo_estado.addItem(etiqueta, clave)
        self._combo_estado.setMinimumWidth(180)
        self._combo_estado.currentIndexChanged.connect(self._actualizar_tabla_historial)
        cab.addWidget(self._combo_estado)

        self._buscador_archivo = QLineEdit()
        self._buscador_archivo.setPlaceholderText("Buscar por archivo")
        self._buscador_archivo.setMinimumWidth(220)
        self._buscador_archivo.textChanged.connect(self._actualizar_tabla_historial)
        cab.addWidget(self._buscador_archivo)
        layout.addLayout(cab)

        self._tabla_historial = QTableWidget(0, 6)
        self._tabla_historial.setHorizontalHeaderLabels(
            ["FECHA", "ARCHIVO", "REGISTROS", "CLASIFICADOS", "ESTADO", "MENSAJE"]
        )
        encabezado_tabla = self._tabla_historial.horizontalHeader()
        encabezado_tabla.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        encabezado_tabla.setSectionResizeMode(1, QHeaderView.Stretch)
        encabezado_tabla.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        encabezado_tabla.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        encabezado_tabla.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        encabezado_tabla.setSectionResizeMode(5, QHeaderView.Stretch)
        self._tabla_historial.verticalHeader().setVisible(False)
        self._tabla_historial.verticalHeader().setDefaultSectionSize(34)
        self._tabla_historial.setAlternatingRowColors(True)
        self._tabla_historial.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_historial.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_historial.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabla_historial.itemDoubleClicked.connect(self._mostrar_detalle_ejecucion)
        layout.addWidget(self._tabla_historial)

        ayuda = QLabel("Doble clic sobre una fila para ver el detalle de la ejecucion.")
        ayuda.setObjectName("textoSecundario")
        layout.addWidget(ayuda)
        return card

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def recargar(self) -> None:
        """Recarga clinicas y ejecuciones desde la base de datos."""
        try:
            with sesion_scope() as sesion:
                self._clinicas = sorted(
                    ServicioClinicas(sesion).listar_clinicas(activa=True),
                    key=lambda c: c.nombre.lower(),
                )
                self._ejecuciones = ServicioEjecuciones(sesion).listar_ejecuciones()
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible cargar dashboard de clinicas: %s", error)
            self._clinicas = []
            self._ejecuciones = []

        # Indexar ejecuciones por clinica para acceso rapido
        self._ejecuciones_por_clinica = {}
        for ejecucion in self._ejecuciones:
            if ejecucion.clinica_id is None:
                continue
            self._ejecuciones_por_clinica.setdefault(ejecucion.clinica_id, []).append(ejecucion)

        self._llenar_lista_clinicas()
        if self._clinica_seleccionada is not None:
            # Re-seleccionar misma clinica si sigue presente
            actualizada = next(
                (c for c in self._clinicas if c.id == self._clinica_seleccionada.id), None
            )
            if actualizada is not None:
                self._seleccionar_clinica(actualizada)
                return
        self._stack.setCurrentIndex(0)

    def _llenar_lista_clinicas(self) -> None:
        self._lista_clinicas.blockSignals(True)
        self._lista_clinicas.clear()
        texto_filtro = self._buscador.text().strip().lower() if hasattr(self, "_buscador") else ""
        for clinica in self._clinicas:
            if texto_filtro and texto_filtro not in clinica.nombre.lower():
                continue
            ejecuciones = self._ejecuciones_por_clinica.get(clinica.id, [])
            etiqueta = f"{clinica.nombre}\n  {len(ejecuciones)} ejecuciones"
            item = QListWidgetItem(etiqueta)
            item.setData(Qt.UserRole, clinica.id)
            self._lista_clinicas.addItem(item)
        self._lista_clinicas.blockSignals(False)
        self._lbl_total_clinicas.setText(
            "Sin clinicas registradas"
            if not self._clinicas
            else f"{len(self._clinicas)} clinicas activas"
        )

    def _filtrar_clinicas(self) -> None:
        self._llenar_lista_clinicas()

    def _al_seleccionar_clinica(self) -> None:
        items = self._lista_clinicas.selectedItems()
        if not items:
            return
        clinica_id = items[0].data(Qt.UserRole)
        clinica = next((c for c in self._clinicas if c.id == clinica_id), None)
        if clinica is not None:
            self._seleccionar_clinica(clinica)

    def _seleccionar_clinica(self, clinica: ClinicaDTO) -> None:
        self._clinica_seleccionada = clinica
        try:
            with sesion_scope() as sesion:
                self._farmacias_clinica = ServicioClinicas(sesion).listar_farmacias_de_clinica(
                    clinica.id
                )
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar farmacias de la clinica: %s", error)
            self._farmacias_clinica = []

        self._lbl_clinica_titulo.setText(clinica.nombre)
        codigo = f"Codigo: {clinica.codigo}" if clinica.codigo else "Sin codigo"
        creada = clinica.fecha_creacion.strftime("%Y-%m-%d") if clinica.fecha_creacion else "—"
        self._lbl_clinica_subtitulo.setText(
            f"{codigo} · Registrada: {creada}"
        )
        self._actualizar_metricas()
        self._actualizar_panel_farmacias()
        self._actualizar_tabla_historial()
        self._stack.setCurrentIndex(1)

    def _actualizar_metricas(self) -> None:
        if self._clinica_seleccionada is None:
            return
        ejecuciones = self._ejecuciones_por_clinica.get(self._clinica_seleccionada.id, [])
        exportadas = sum(1 for e in ejecuciones if e.estado == "EXPORTADA")
        clasificados = sum(int(e.total_clasificados or 0) for e in ejecuciones)
        self._tm_ejecuciones.actualizar(str(len(ejecuciones)))
        self._tm_exportaciones.actualizar(str(exportadas))
        self._tm_farmacias.actualizar(str(len(self._farmacias_clinica)))
        self._tm_clasificados.actualizar(self._formatear_numero(clasificados))

    def _actualizar_panel_farmacias(self) -> None:
        if not self._farmacias_clinica:
            self._lbl_farmacias.setText("Sin farmacias asociadas a esta clinica.")
            return
        nombres = [f.nombre_original for f in self._farmacias_clinica[:30]]
        texto = ", ".join(nombres)
        if len(self._farmacias_clinica) > 30:
            texto += f" (+ {len(self._farmacias_clinica) - 30} mas)"
        self._lbl_farmacias.setText(texto)

    def _actualizar_tabla_historial(self) -> None:
        if self._clinica_seleccionada is None:
            self._tabla_historial.setRowCount(0)
            return
        ejecuciones = self._ejecuciones_por_clinica.get(self._clinica_seleccionada.id, [])
        estado_filtro = self._combo_estado.currentData() if hasattr(self, "_combo_estado") else "TODOS"
        texto_archivo = self._buscador_archivo.text().strip().lower() if hasattr(self, "_buscador_archivo") else ""

        filtradas = [
            e
            for e in ejecuciones
            if (estado_filtro == "TODOS" or e.estado == estado_filtro)
            and (not texto_archivo or texto_archivo in (e.archivo_nombre or "").lower())
        ]

        self._tabla_historial.setRowCount(len(filtradas))
        for fila, ejecucion in enumerate(filtradas):
            fecha = (
                ejecucion.fecha_inicio.strftime("%Y-%m-%d %H:%M")
                if ejecucion.fecha_inicio
                else "—"
            )
            self._tabla_historial.setItem(fila, 0, QTableWidgetItem(fecha))
            self._tabla_historial.setItem(fila, 1, QTableWidgetItem(ejecucion.archivo_nombre or "—"))
            self._tabla_historial.setItem(fila, 2, self._item_numero(ejecucion.total_registros))
            self._tabla_historial.setItem(fila, 3, self._item_numero(ejecucion.total_clasificados))

            badge = QLabel(ejecucion.estado)
            badge.setAlignment(Qt.AlignCenter)
            badge.setObjectName(self._badge_para_estado(ejecucion.estado))
            cont = QWidget()
            cont_layout = QHBoxLayout(cont)
            cont_layout.setContentsMargins(4, 0, 4, 0)
            cont_layout.addWidget(badge)
            self._tabla_historial.setCellWidget(fila, 4, cont)

            mensaje = (ejecucion.mensaje or "").splitlines()[0] if ejecucion.mensaje else ""
            item_msg = QTableWidgetItem(mensaje)
            item_msg.setData(Qt.UserRole, ejecucion.id)
            self._tabla_historial.setItem(fila, 5, item_msg)

    def _mostrar_detalle_ejecucion(self, item: QTableWidgetItem) -> None:
        fila = item.row()
        item_id = self._tabla_historial.item(fila, 5)
        if item_id is None:
            return
        ejecucion_id = item_id.data(Qt.UserRole)
        ejecucion = next((e for e in self._ejecuciones if e.id == ejecucion_id), None)
        if ejecucion is None:
            return

        duracion = (
            f"{ejecucion.duracion_segundos:.2f} s"
            if ejecucion.duracion_segundos is not None
            else "—"
        )
        fecha_inicio = ejecucion.fecha_inicio.strftime("%Y-%m-%d %H:%M:%S") if ejecucion.fecha_inicio else "—"
        fecha_fin = ejecucion.fecha_fin.strftime("%Y-%m-%d %H:%M:%S") if ejecucion.fecha_fin else "En curso"

        QMessageBox.information(
            self,
            f"Detalle de ejecucion #{ejecucion.id}",
            (
                f"Archivo: {ejecucion.archivo_nombre or '—'}\n"
                f"Hoja: {ejecucion.hoja or '—'}\n"
                f"Estado: {ejecucion.estado}\n"
                f"Inicio: {fecha_inicio}\n"
                f"Fin: {fecha_fin}\n"
                f"Duracion: {duracion}\n\n"
                f"Registros totales: {ejecucion.total_registros}\n"
                f"Clasificados: {ejecucion.total_clasificados}\n"
                f"Sin clasificar: {ejecucion.total_sin_clasificar}\n\n"
                f"Mensaje: {ejecucion.mensaje or '—'}"
            ),
        )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _item_numero(self, valor: int | None) -> QTableWidgetItem:
        item = QTableWidgetItem(self._formatear_numero(valor or 0))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    def _formatear_numero(self, valor: int) -> str:
        return f"{valor:,}".replace(",", ".")

    def _badge_para_estado(self, estado: str) -> str:
        return {
            "EXPORTADA": "insigniaCorrecta",
            "CLASIFICADA": "insigniaInfo",
            "VALIDADA": "insigniaInfo",
            "INICIADA": "insigniaNeutra",
            "ERROR": "insigniaError",
            "CANCELADA": "insigniaAdvertencia",
        }.get(estado, "insigniaNeutra")
