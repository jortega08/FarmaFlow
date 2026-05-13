"""Badge visual de estado con variantes de color semantico."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

_NOMBRES_POR_TIPO: dict[str, str] = {
    "correcto": "insigniaCorrecta",
    "advertencia": "insigniaAdvertencia",
    "error": "insigniaError",
    "info": "insigniaInfo",
    "neutro": "insigniaNeutra",
}


class BadgeEstado(QLabel):
    """Etiqueta de estado con fondo y color segun tipo semantico."""

    def __init__(self, texto: str = "", tipo: str = "neutro", parent=None) -> None:
        super().__init__(texto, parent)
        self._aplicar_tipo(tipo)

    def establecer_estado(self, texto: str, tipo: str = "neutro") -> None:
        """Actualiza el texto y el tipo visual del badge."""
        self.setText(texto)
        self._aplicar_tipo(tipo)

    def _aplicar_tipo(self, tipo: str) -> None:
        self.setObjectName(_NOMBRES_POR_TIPO.get(tipo, "insigniaNeutra"))
        if self.style():
            self.style().unpolish(self)
            self.style().polish(self)
