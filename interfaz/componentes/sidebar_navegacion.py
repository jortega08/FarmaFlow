"""Barra de navegacion lateral fija de la aplicacion."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from interfaz.branding import NOMBRE_APP, RUTA_LOGO_APP
from interfaz.componentes.item_navegacion import ItemNavegacion

# (clave, titulo, numero, subtitulo)
_PASOS_PRINCIPALES: tuple[tuple[str, str, int, str], ...] = (
    ("carga", "Carga", 1, "Sube el archivo Excel"),
    ("novedades", "Novedades", 2, "Revisa hallazgos del archivo"),
    ("clinica", "Clinica y farmacias", 3, "Confirma origen y destinos"),
    ("reglas", "Reglas", 4, "Define como clasificar"),
    ("resultado", "Resultado", 5, "Revisa la preclasificacion"),
    ("exportar", "Exportar", 6, "Genera el archivo final"),
)

_CONFIG_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("clinicas", "Clinicas", "Dashboard e historial por clinica"),
    ("catalogos", "Catalogos", "Articulos, tipologias, farmacias"),
    ("historial", "Historial", "Ejecuciones anteriores"),
)


class SidebarNavegacion(QFrame):
    """Panel izquierdo fijo de navegacion entre pantallas."""

    pantalla_solicitada = Signal(str)

    def __init__(
        self,
        nombre_app: str = NOMBRE_APP,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._nombre_app = nombre_app
        self._items: dict[str, ItemNavegacion] = {}
        self._clave_activa: str | None = None

        self.setObjectName("sidebar")
        self.setMinimumWidth(72)
        self.setMaximumWidth(360)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self._construir_ui()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._crear_header())
        layout.addSpacing(12)

        etiqueta_pasos = QLabel("FLUJO DE TRABAJO")
        etiqueta_pasos.setObjectName("seccionNavTitle")
        etiqueta_pasos.setContentsMargins(20, 0, 0, 4)
        layout.addWidget(etiqueta_pasos)
        layout.addSpacing(4)

        for clave, texto, numero, subtitulo in _PASOS_PRINCIPALES:
            item = ItemNavegacion(
                clave=clave, texto=texto, numero=numero, subtitulo=subtitulo, parent=self
            )
            item.clic.connect(self._al_hacer_clic)
            self._items[clave] = item
            layout.addWidget(item)

        layout.addSpacing(16)
        layout.addWidget(self._crear_separador())
        layout.addSpacing(16)

        etiqueta_config = QLabel("CONFIGURACION")
        etiqueta_config.setObjectName("seccionNavTitle")
        etiqueta_config.setContentsMargins(20, 0, 0, 4)
        layout.addWidget(etiqueta_config)
        layout.addSpacing(4)

        for clave, texto, subtitulo in _CONFIG_ITEMS:
            item = ItemNavegacion(
                clave=clave, texto=texto, numero=None, subtitulo=subtitulo, parent=self
            )
            item.clic.connect(self._al_hacer_clic)
            self._items[clave] = item
            layout.addWidget(item)

        layout.addStretch(1)
        layout.addWidget(self._crear_footer())

    def _crear_header(self) -> QFrame:
        header = QFrame(self)
        header.setObjectName("sidebarHeader")

        layout = QVBoxLayout(header)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(0)

        logo = QLabel(self._nombre_app)
        logo.setObjectName("logoSidebar")
        logo.setFixedSize(218, 84)
        logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        logo.setToolTip(self._nombre_app)

        if RUTA_LOGO_APP.exists():
            pixmap = QPixmap(str(RUTA_LOGO_APP))
            if not pixmap.isNull():
                logo.setText("")
                logo.setPixmap(
                    pixmap.scaled(
                        218,
                        84,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )

        layout.addWidget(logo)
        return header

    def _crear_separador(self) -> QFrame:
        sep = QFrame(self)
        sep.setObjectName("separadorSidebar")
        sep.setFixedHeight(1)
        sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return sep

    def _crear_footer(self) -> QFrame:
        footer = QFrame(self)
        footer.setObjectName("sidebarFooter")

        layout = QVBoxLayout(footer)
        layout.setContentsMargins(20, 14, 20, 18)
        layout.setSpacing(2)

        for texto in ("Version 1.0.0", "(c) 2024"):
            lbl = QLabel(texto)
            lbl.setObjectName("versionSidebar")
            layout.addWidget(lbl)
        return footer

    def _al_hacer_clic(self, clave: str) -> None:
        self.activar_pantalla(clave)
        self.pantalla_solicitada.emit(clave)

    def activar_pantalla(self, clave: str) -> None:
        """Marca la pantalla indicada como activa y desactiva la anterior."""
        if self._clave_activa and self._clave_activa in self._items:
            self._items[self._clave_activa].establecer_activo(False)
        if clave in self._items:
            self._items[clave].establecer_activo(True)
            self._clave_activa = clave

    def claves_pantallas(self) -> list[str]:
        """Retorna las claves de todos los items registrados."""
        return list(self._items.keys())

    def ancho_preferido(self) -> int:
        """Ancho recomendado para restaurar la barra lateral."""
        return 260
