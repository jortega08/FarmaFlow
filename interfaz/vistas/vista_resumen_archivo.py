"""Vista para presentar el resumen del archivo cargado."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from interfaz.componentes.panel_informacion_archivo import PanelInformacionArchivo
from modelos.resultado_carga import ResultadoCarga


class VistaResumenArchivo(QFrame):
    """Muestra la informacion principal del archivo despues de la lectura."""

    def __init__(self) -> None:
        super().__init__()
        self._panel_informacion = PanelInformacionArchivo()
        self._contenedor_vacio = QFrame()
        self._contenedor_vacio.setObjectName("panelArchivo")
        self._mensaje_vacio = QLabel(
            "El resumen general aparecera aqui cuando termine la lectura del archivo seleccionado."
        )
        self._mensaje_vacio.setObjectName("descripcionPlaceholder")
        self._mensaje_vacio.setWordWrap(True)
        self._configurar_interfaz()

    def _configurar_interfaz(self) -> None:
        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.setSpacing(0)

        disposicion_vacio = QVBoxLayout(self._contenedor_vacio)
        disposicion_vacio.setContentsMargins(26, 24, 26, 24)
        disposicion_vacio.setSpacing(10)

        titulo_vacio = QLabel("Resumen general")
        titulo_vacio.setObjectName("tituloSeccion")

        apoyo_vacio = QLabel(
            "Aqui se consolidan el archivo cargado, el estado estructural y los principales indicadores del procesamiento."
        )
        apoyo_vacio.setObjectName("textoSecundario")
        apoyo_vacio.setWordWrap(True)

        disposicion_vacio.addWidget(titulo_vacio)
        disposicion_vacio.addWidget(apoyo_vacio)
        disposicion_vacio.addWidget(self._mensaje_vacio)
        disposicion_vacio.addStretch(1)

        disposicion.addWidget(self._panel_informacion)
        disposicion.addWidget(self._contenedor_vacio)

        self._panel_informacion.hide()

    def actualizar_resultado(self, resultado: ResultadoCarga) -> None:
        """Actualiza la tarjeta con la informacion del archivo cargado."""
        self._contenedor_vacio.hide()
        self._panel_informacion.actualizar_desde_resultado(resultado)
        self._panel_informacion.show()

    def limpiar(self) -> None:
        """Limpia la informacion mostrada y vuelve al estado inicial."""
        self._panel_informacion.limpiar()
        self._panel_informacion.hide()
        self._contenedor_vacio.show()
