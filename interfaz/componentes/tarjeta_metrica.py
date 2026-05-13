"""Tarjeta visual con valor destacado y etiqueta descriptiva."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout


class TarjetaMetrica(QFrame):
    """Contenedor de una metrica con valor grande y titulo descriptivo."""

    def __init__(
        self,
        titulo: str,
        valor_inicial: str = "-",
        icono: str = "",
        tipo: str = "info",
        descripcion: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tarjetaMetrica")
        self.setMinimumHeight(108)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._icono = QLabel(icono)
        self._icono.setObjectName(self._nombre_icono(tipo))
        self._icono.setFixedSize(48, 48)
        self._icono.setAlignment(Qt.AlignCenter)

        self._etiqueta = QLabel(titulo)
        self._etiqueta.setObjectName("etiquetaMetrica")

        self._valor = QLabel(valor_inicial)
        self._valor.setObjectName("valorMetrica")
        self._valor.setWordWrap(True)

        self._descripcion = QLabel(descripcion)
        self._descripcion.setObjectName("descripcionMetrica")
        self._descripcion.setWordWrap(True)

        textos = QVBoxLayout()
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(3)
        textos.addWidget(self._etiqueta)
        textos.addWidget(self._valor)
        textos.addWidget(self._descripcion)

        disposicion = QHBoxLayout(self)
        disposicion.setContentsMargins(16, 14, 16, 14)
        disposicion.setSpacing(14)
        disposicion.addWidget(self._icono, 0)
        disposicion.addLayout(textos, 1)

    def actualizar(
        self,
        valor: str,
        titulo: str | None = None,
        descripcion: str | None = None,
        estilo_valor: str = "valorMetrica",
    ) -> None:
        """Actualiza el valor mostrado y opcionalmente titulo/descripcion."""
        self._valor.setText(valor)
        self._valor.setObjectName(estilo_valor)
        if titulo is not None:
            self._etiqueta.setText(titulo)
        if descripcion is not None:
            self._descripcion.setText(descripcion)
        self._refrescar_estilo(self._valor)

    def establecer_icono(self, texto: str, tipo: str = "info") -> None:
        """Actualiza el icono textual y su color semantico."""
        self._icono.setText(texto)
        self._icono.setObjectName(self._nombre_icono(tipo))
        self._refrescar_estilo(self._icono)

    def _nombre_icono(self, tipo: str) -> str:
        nombres = {
            "info": "iconoTarjetaInfo",
            "exito": "iconoTarjetaExito",
            "neutro": "iconoTarjetaNeutro",
            "advertencia": "iconoTarjetaAdvertencia",
        }
        return nombres.get(tipo, "iconoTarjetaInfo")

    def _refrescar_estilo(self, widget: QLabel) -> None:
        if self.style():
            self.style().unpolish(widget)
            self.style().polish(widget)
