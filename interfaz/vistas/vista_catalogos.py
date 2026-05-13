"""Vista de gestion de catalogos del sistema."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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


class VistaCatalogos(QWidget):
    """Pantalla de gestion de catalogos del sistema (placeholder visual)."""

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
        layout_c.addLayout(self._crear_catalogos())
        layout_c.addStretch(1)

        scroll.setWidget(contenedor)
        layout.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        titulo = QLabel("Catálogos")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Gestione los catálogos de artículos, tipologías y farmacias utilizados en la clasificación."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        return card

    def _crear_catalogos(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(14)

        for titulo_cat in ("Artículos", "Tipologías", "Farmacias"):
            layout.addWidget(self._crear_catalogo_card(titulo_cat))
        return layout

    def _crear_catalogo_card(self, titulo: str) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        cab = QHBoxLayout()
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("tituloSubpanel")
        badge = QLabel("0")
        badge.setObjectName("insigniaNeutra")
        cab.addWidget(lbl_titulo)
        cab.addStretch()
        cab.addWidget(badge)

        buscador = QLineEdit()
        buscador.setPlaceholderText(f"Buscar en {titulo.lower()}...")

        tabla = QTableWidget(0, 2)
        tabla.setHorizontalHeaderLabels(["Código", "Descripción"])
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tabla.verticalHeader().setVisible(False)
        tabla.setAlternatingRowColors(True)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setMinimumHeight(200)

        botones = QHBoxLayout()
        for texto, obj in (("Agregar", "botonSecundario"), ("Eliminar", "botonTerciario")):
            btn = QPushButton(texto)
            btn.setObjectName(obj)
            btn.setMinimumHeight(36)
            botones.addWidget(btn)
        botones.addStretch()

        layout.addLayout(cab)
        layout.addWidget(buscador)
        layout.addWidget(tabla)
        layout.addLayout(botones)
        return card
