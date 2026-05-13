"""Contenedor tipo tarjeta con fondo blanco y titulo opcional."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout


class SeccionCard(QFrame):
    """Tarjeta blanca con esquinas redondeadas y titulo opcional."""

    def __init__(self, titulo: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panelArchivo")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._layout_principal = QVBoxLayout(self)
        self._layout_principal.setContentsMargins(20, 18, 20, 18)
        self._layout_principal.setSpacing(14)

        if titulo:
            lbl_titulo = QLabel(titulo)
            lbl_titulo.setObjectName("tituloSeccion")
            self._layout_principal.addWidget(lbl_titulo)

    @property
    def layout_principal(self) -> QVBoxLayout:
        """Acceso al layout interno para anadir contenido."""
        return self._layout_principal
