"""Elemento seleccionable de la barra de navegacion lateral."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

ESTADO_ACTIVO = "activo"
ESTADO_COMPLETADO = "completado"
ESTADO_PENDIENTE = "pendiente"


class ItemNavegacion(QFrame):
    """Elemento de navegacion lateral con numero de paso, texto y subtitulo opcional."""

    clic = Signal(str)

    def __init__(
        self,
        clave: str,
        texto: str,
        numero: int | None = None,
        subtitulo: str | None = None,
        mostrar_subtitulo: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._clave = clave
        self._estado = ESTADO_PENDIENTE
        self._tiene_subtitulo = bool(subtitulo and mostrar_subtitulo)

        self.setObjectName("itemNavNormal")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(46)

        disposicion = QHBoxLayout(self)
        disposicion.setContentsMargins(16, 0, 16, 0)
        disposicion.setSpacing(12)

        if numero is not None:
            self._badge_num: QLabel | None = QLabel(str(numero))
            self._badge_num.setObjectName("badgeNumNav")
            self._badge_num.setFixedSize(24, 24)
            self._badge_num.setAlignment(Qt.AlignCenter)
            disposicion.addWidget(self._badge_num)
        else:
            self._badge_num = None

        textos = QVBoxLayout()
        textos.setSpacing(0)
        textos.setContentsMargins(0, 0, 0, 0)

        self._etiqueta = QLabel(texto)
        self._etiqueta.setObjectName("textoNavNormal")
        textos.addWidget(self._etiqueta)

        self._subtitulo: QLabel | None = None
        if subtitulo and mostrar_subtitulo:
            self._subtitulo = QLabel(subtitulo)
            self._subtitulo.setObjectName("subtituloNav")
            self._subtitulo.setWordWrap(False)
            textos.addWidget(self._subtitulo)

        disposicion.addLayout(textos, 1)

    @property
    def clave(self) -> str:
        """Retorna la clave identificadora del item."""
        return self._clave

    def establecer_activo(self, activo: bool) -> None:
        """Actualiza el estado visual activo/inactivo."""
        self._estado = ESTADO_ACTIVO if activo else ESTADO_PENDIENTE
        self.setObjectName("itemNavActivo" if activo else "itemNavNormal")
        self._etiqueta.setObjectName("textoNavActivo" if activo else "textoNavNormal")
        if self._badge_num:
            self._badge_num.setObjectName(
                "badgeNumNavActivo" if activo else "badgeNumNav"
            )
        if self._subtitulo:
            self._subtitulo.setObjectName(
                "subtituloNavActivo" if activo else "subtituloNav"
            )
        self._refrescar_estilos()

    def establecer_completado(self) -> None:
        """Marca el item como completado con icono de verificacion."""
        self._estado = ESTADO_COMPLETADO
        self.setObjectName("itemNavNormal")
        self._etiqueta.setObjectName("textoNavNormal")
        if self._badge_num:
            self._badge_num.setObjectName("badgeNumNavCompletado")
            self._badge_num.setText("OK")
        self._refrescar_estilos()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clic.emit(self._clave)
        super().mousePressEvent(event)

    def _refrescar_estilos(self) -> None:
        widgets: list[QLabel | QFrame] = [self, self._etiqueta]
        if self._badge_num:
            widgets.append(self._badge_num)
        if self._subtitulo:
            widgets.append(self._subtitulo)
        for w in widgets:
            if self.style():
                self.style().unpolish(w)
                self.style().polish(w)
