"""ComboBox que no cambia de valor con la rueda del mouse accidentalmente."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox


class ComboScrollSafe(QComboBox):
    """QComboBox que deja que el scroll lo maneje el contenedor padre."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        event.ignore()
