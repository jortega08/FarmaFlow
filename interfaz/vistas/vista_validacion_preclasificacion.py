"""Vista compacta para validacion y preclasificacion."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy

from interfaz.componentes.panel_preclasificacion import PanelPreclasificacion
from interfaz.componentes.panel_validacion import PanelValidacion
from modelos.resultado_carga import ResultadoCarga


class VistaValidacionPreclasificacion(QFrame):
    """Agrupa el diagnostico estructural y el resumen preliminar."""

    def __init__(self) -> None:
        super().__init__()
        self._panel_validacion = PanelValidacion()
        self._panel_preclasificacion = PanelPreclasificacion()
        self._configurar_interfaz()

    def _configurar_interfaz(self) -> None:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._panel_validacion.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._panel_preclasificacion.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        disposicion = QHBoxLayout(self)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.setSpacing(18)
        disposicion.addWidget(self._panel_validacion, 1)
        disposicion.addWidget(self._panel_preclasificacion, 1)

    def actualizar_resultado(self, resultado: ResultadoCarga) -> None:
        """Actualiza ambos paneles a partir del resultado de carga."""
        self._panel_validacion.actualizar_desde_resultado(
            resultado.resultado_validacion,
            resultado.resumen_validacion,
        )
        self._panel_preclasificacion.actualizar_desde_resultado(
            resultado.resultado_preclasificacion,
            resultado.resumen_preclasificacion,
        )

    def limpiar(self) -> None:
        """Restablece la vista al estado inicial."""
        self._panel_validacion.limpiar()
        self._panel_preclasificacion.limpiar()
