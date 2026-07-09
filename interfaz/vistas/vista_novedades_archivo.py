"""Vista de novedades detectadas en el archivo mensual."""

from __future__ import annotations

import logging

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
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from interfaz.componentes.tarjeta_metrica import TarjetaMetrica
from logica.novedades_archivo import FarmaciaArchivo, NovedadesArchivo
from modelos.resultado_carga import ResultadoCarga


class VistaNovedadesArchivo(QWidget):
    """Resumen guiado de novedades del archivo actual."""

    guardar_farmacias_solicitado = Signal()
    continuar_solicitado = Signal()
    revisar_resultados_solicitado = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._resultado_carga: ResultadoCarga | None = None
        self._novedades = NovedadesArchivo()
        self._construir_ui()
        self.limpiar()

    def _construir_ui(self) -> None:
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorVista")
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)

        layout.addWidget(self._crear_titulo())
        layout.addLayout(self._crear_kpis())
        layout.addWidget(self._crear_resumen_farmacias())
        layout.addWidget(self._crear_tabla_farmacias())
        layout.addWidget(self._crear_articulos())
        layout.addWidget(self._crear_acciones())
        layout.addStretch(1)

        scroll.setWidget(contenedor)
        raiz.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        icono = QLabel("NV")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(50, 50)
        icono.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        titulo = QLabel("2. Novedades detectadas")
        titulo.setObjectName("tituloSeccion")
        self._lbl_subtitulo = QLabel("Cargue un archivo para detectar farmacias y articulos pendientes.")
        self._lbl_subtitulo.setObjectName("textoSecundario")
        self._lbl_subtitulo.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(self._lbl_subtitulo)

        layout.addWidget(icono)
        layout.addLayout(textos, 1)
        return card

    def _crear_kpis(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        self._kpi_internas = TarjetaMetrica("Internas detectadas", "0", icono="INT", tipo="info")
        self._kpi_externas = TarjetaMetrica("Externas detectadas", "0", icono="EXT", tipo="advertencia")
        self._kpi_nuevas = TarjetaMetrica("Nuevas", "0", icono="NEW", tipo="exito")
        self._kpi_pendientes = TarjetaMetrica("Pendientes", "0", icono="REV", tipo="advertencia")
        for indice, tarjeta in enumerate((
            self._kpi_internas,
            self._kpi_externas,
            self._kpi_nuevas,
            self._kpi_pendientes,
        )):
            grid.addWidget(tarjeta, indice // 2, indice % 2)
        return grid

    def _crear_resumen_farmacias(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        titulo = QLabel("Resumen de revision")
        titulo.setObjectName("tituloSubpanel")
        self._lbl_resumen = QLabel("Sin archivo cargado.")
        self._lbl_resumen.setObjectName("textoSecundario")
        self._lbl_resumen.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(self._lbl_resumen)
        return card

    def _crear_tabla_farmacias(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        titulo = QLabel("Farmacias internas, externas y pendientes")
        titulo.setObjectName("tituloSubpanel")
        layout.addWidget(titulo)

        self._tabla_farmacias = QTableWidget(0, 7)
        self._tabla_farmacias.setHorizontalHeaderLabels(
            ["GUARDAR", "FARMACIA", "ORIGEN", "TIPO", "HISTORIAL", "PRESTA", "REVISION"]
        )
        encabezado = self._tabla_farmacias.horizontalHeader()
        encabezado.setSectionResizeMode(0, QHeaderView.Fixed)
        self._tabla_farmacias.setColumnWidth(0, 72)
        encabezado.setSectionResizeMode(1, QHeaderView.Stretch)
        for columna, ancho in {2: 120, 3: 140, 4: 96, 5: 86, 6: 130}.items():
            encabezado.setSectionResizeMode(columna, QHeaderView.Fixed)
            self._tabla_farmacias.setColumnWidth(columna, ancho)
        self._tabla_farmacias.verticalHeader().setVisible(False)
        self._tabla_farmacias.setAlternatingRowColors(True)
        self._tabla_farmacias.setSelectionMode(QAbstractItemView.NoSelection)
        self._tabla_farmacias.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_farmacias.setMinimumHeight(260)
        layout.addWidget(self._tabla_farmacias)
        return card

    def _crear_articulos(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        titulo = QLabel("Articulos candidatos a revisar en LIQUIDOS o MCE_CIRUGIA")
        titulo.setObjectName("tituloSubpanel")
        layout.addWidget(titulo)
        self._tabla_articulos = QTableWidget(0, 4)
        self._tabla_articulos.setHorizontalHeaderLabels(["CODIGO", "DESCRIPCION", "CONTEO", "MOTIVO"])
        encabezado = self._tabla_articulos.horizontalHeader()
        encabezado.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        encabezado.setSectionResizeMode(1, QHeaderView.Stretch)
        encabezado.setSectionResizeMode(2, QHeaderView.Fixed)
        encabezado.setSectionResizeMode(3, QHeaderView.Fixed)
        self._tabla_articulos.setColumnWidth(2, 90)
        self._tabla_articulos.setColumnWidth(3, 150)
        self._tabla_articulos.verticalHeader().setVisible(False)
        self._tabla_articulos.setMinimumHeight(140)
        self._tabla_articulos.setAlternatingRowColors(True)
        self._tabla_articulos.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._tabla_articulos)
        return card

    def _crear_acciones(self) -> QFrame:
        barra = QFrame()
        barra.setObjectName("barraInferior")
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)
        self._lbl_estado = QLabel("Revise novedades antes de continuar.")
        self._lbl_estado.setObjectName("mensajeEstadoNeutro")
        self._lbl_estado.setWordWrap(True)

        self._btn_guardar = QPushButton("Guardar farmacias revisadas")
        self._btn_guardar.setObjectName("botonPrincipal")
        self._btn_guardar.setMinimumHeight(40)
        self._btn_guardar.clicked.connect(self.guardar_farmacias_solicitado.emit)

        self._btn_continuar = QPushButton("Continuar sin guardar")
        self._btn_continuar.setObjectName("botonSecundario")
        self._btn_continuar.setMinimumHeight(40)
        self._btn_continuar.clicked.connect(self.continuar_solicitado.emit)

        self._btn_resultados = QPushButton("Continuar a resultados")
        self._btn_resultados.setObjectName("botonExito")
        self._btn_resultados.setMinimumHeight(40)
        self._btn_resultados.clicked.connect(self.revisar_resultados_solicitado.emit)

        layout.addWidget(self._lbl_estado, 1)
        layout.addWidget(self._btn_guardar)
        layout.addWidget(self._btn_continuar)
        layout.addWidget(self._btn_resultados)
        return barra

    def establecer_novedades(self, resultado: ResultadoCarga, novedades: NovedadesArchivo) -> None:
        self._resultado_carga = resultado
        self._novedades = novedades
        self._lbl_subtitulo.setText(
            f"Archivo cargado correctamente: {resultado.nombre_archivo or 'archivo'}. "
            "Revise lo nuevo antes de cerrar la clasificacion mensual."
        )
        self._actualizar_kpis()
        self._actualizar_resumen()
        self._actualizar_tabla_farmacias()
        self._actualizar_tabla_articulos()
        self._lbl_estado.setText(
            "Hay pendientes por revisar." if novedades.total_pendientes else "No se detectaron farmacias pendientes."
        )

    def limpiar(self) -> None:
        self._resultado_carga = None
        self._novedades = NovedadesArchivo()
        self._lbl_subtitulo.setText("Cargue un archivo para detectar farmacias y articulos pendientes.")
        self._actualizar_kpis()
        self._lbl_resumen.setText("Sin archivo cargado.")
        self._tabla_farmacias.setRowCount(0)
        self._tabla_articulos.setRowCount(0)
        self._lbl_estado.setText("Revise novedades antes de continuar.")

    def _actualizar_kpis(self) -> None:
        novedades = self._novedades
        self._kpi_internas.actualizar(str(len(novedades.internas_detectadas)))
        self._kpi_externas.actualizar(str(len(novedades.externas_detectadas)))
        self._kpi_nuevas.actualizar(str(len(novedades.farmacias_nuevas)))
        self._kpi_pendientes.actualizar(str(novedades.total_pendientes))

    def _actualizar_resumen(self) -> None:
        novedades = self._novedades
        self._lbl_resumen.setText(
            "Farmacias internas detectadas: {internas}. Farmacias externas detectadas: {externas}. "
            "Farmacias nuevas: {nuevas}. Farmacias conocidas: {conocidas}. "
            "Pendientes de revision: {pendientes}.".format(
                internas=len(novedades.internas_detectadas),
                externas=len(novedades.externas_detectadas),
                nuevas=len(novedades.farmacias_nuevas),
                conocidas=len(novedades.farmacias_conocidas),
                pendientes=novedades.total_pendientes,
            )
        )

    def _actualizar_tabla_farmacias(self) -> None:
        self._tabla_farmacias.setRowCount(0)
        for fila, farmacia in enumerate(self._novedades.farmacias):
            self._tabla_farmacias.insertRow(fila)
            check = QCheckBox()
            check.setChecked(farmacia.tipo_sugerido != "NO_CLASIFICABLE")
            self._tabla_farmacias.setCellWidget(fila, 0, self._centrar(check))
            self._set_item(self._tabla_farmacias, fila, 1, farmacia.codigo)
            self._set_item(self._tabla_farmacias, fila, 2, ", ".join(farmacia.origenes))
            self._tabla_farmacias.setCellWidget(fila, 3, self._combo_tipo(farmacia.tipo_sugerido))
            self._set_item(self._tabla_farmacias, fila, 4, "Conocida" if farmacia.conocida else "Nueva", centro=True)
            self._tabla_farmacias.setCellWidget(fila, 5, self._combo_presta(farmacia.puede_prestar))
            self._set_item(
                self._tabla_farmacias,
                fila,
                6,
                "Pendiente" if farmacia.pendiente_revision else "OK",
                centro=True,
            )
            self._tabla_farmacias.setRowHeight(fila, 34)

    def _actualizar_tabla_articulos(self) -> None:
        self._tabla_articulos.setRowCount(0)
        articulos = self._novedades.articulos_candidatos
        if articulos.empty:
            return
        for fila, (_idx, item) in enumerate(articulos.iterrows()):
            self._tabla_articulos.insertRow(fila)
            for columna, nombre in enumerate(("CODIGO", "DESCRIPCION", "CONTEO", "MOTIVO")):
                self._set_item(self._tabla_articulos, fila, columna, str(item.get(nombre, "")), centro=columna == 2)

    def _combo_tipo(self, tipo_actual: str) -> QComboBox:
        combo = ComboScrollSafe()
        for codigo, etiqueta in (
            ("INTERNA", "Interna"),
            ("EXTERNA", "Externa"),
            ("CEDI", "CEDI"),
            ("ALMACEN", "Almacen"),
            ("REEMPAQUE", "Reempaque/Reenvase"),
            ("DEVOLUCIONES", "Devoluciones"),
            ("NO_CLASIFICABLE", "Pendiente"),
        ):
            combo.addItem(etiqueta, codigo)
        indice = combo.findData(tipo_actual)
        combo.setCurrentIndex(indice if indice >= 0 else combo.findData("NO_CLASIFICABLE"))
        return combo

    def _combo_presta(self, puede_prestar: bool | None) -> QComboBox:
        combo = ComboScrollSafe()
        combo.addItem("Pendiente", None)
        combo.addItem("Si", True)
        combo.addItem("No", False)
        if puede_prestar is True:
            combo.setCurrentIndex(1)
        elif puede_prestar is False:
            combo.setCurrentIndex(2)
        return combo

    def _set_item(self, tabla: QTableWidget, fila: int, columna: int, texto: str, centro: bool = False) -> None:
        item = QTableWidgetItem(texto)
        item.setToolTip(texto)
        item.setTextAlignment(Qt.AlignCenter if centro else Qt.AlignVCenter)
        tabla.setItem(fila, columna, item)

    @staticmethod
    def _centrar(widget: QWidget) -> QWidget:
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.addWidget(widget)
        return contenedor
