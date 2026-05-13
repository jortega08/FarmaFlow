"""Vista del historial de ejecuciones y exportaciones."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from interfaz.componentes.tarjeta_metrica import TarjetaMetrica


class VistaHistorial(QWidget):
    """Pantalla del historial de ejecuciones (placeholder visual)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorVista")
        layout_c = QVBoxLayout(contenedor)
        layout_c.setContentsMargins(24, 24, 24, 24)
        layout_c.setSpacing(16)

        layout_c.addWidget(self._crear_titulo())
        layout_c.addLayout(self._crear_metricas())
        layout_c.addWidget(self._crear_filtros())
        layout_c.addWidget(self._crear_tabla())
        layout_c.addStretch(1)

        scroll.setWidget(contenedor)
        layout.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        titulo = QLabel("Historial")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Registro completo de archivos cargados, clasificados y exportados."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        return card

    def _crear_metricas(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(14)
        for titulo, valor in (
            ("Ejecuciones totales", "—"),
            ("Exportaciones", "—"),
            ("Con errores", "—"),
        ):
            fila.addWidget(TarjetaMetrica(titulo, valor))
        return fila

    def _crear_filtros(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(10)

        lbl = QLabel("Filtros:")
        lbl.setObjectName("tituloBloque")
        lbl.setFixedWidth(55)

        combo_estado = ComboScrollSafe()
        combo_estado.addItems(["Todos los estados", "Clasificada", "Exportada", "Error"])
        combo_estado.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        buscador = QLineEdit()
        buscador.setPlaceholderText("Buscar por nombre de archivo...")
        buscador.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.setObjectName("botonTerciario")
        btn_limpiar.setMinimumHeight(38)

        layout.addWidget(lbl)
        layout.addWidget(combo_estado)
        layout.addWidget(buscador, 1)
        layout.addWidget(btn_limpiar)
        return card

    def _crear_tabla(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        cab = QHBoxLayout()
        cab.addWidget(self._lbl("Ejecuciones", "tituloSubpanel"))
        cab.addStretch()

        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.setObjectName("botonTerciario")
        btn_actualizar.setMinimumHeight(36)
        cab.addWidget(btn_actualizar)

        tabla = QTableWidget(0, 6)
        tabla.setHorizontalHeaderLabels([
            "Fecha", "Archivo", "Hoja", "Registros", "Clasificados", "Estado"
        ])
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tabla.verticalHeader().setVisible(False)
        tabla.setAlternatingRowColors(True)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setMinimumHeight(300)

        placeholder = QLabel("No hay ejecuciones registradas.")
        placeholder.setObjectName("descripcionPlaceholder")
        placeholder.setAlignment(Qt.AlignCenter)

        layout.addLayout(cab)
        layout.addWidget(tabla)
        layout.addWidget(placeholder)
        return card

    @staticmethod
    def _lbl(texto: str, objeto: str) -> QLabel:
        l = QLabel(texto)
        l.setObjectName(objeto)
        return l
