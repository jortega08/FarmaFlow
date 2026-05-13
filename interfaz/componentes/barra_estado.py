"""Barra de estado inferior."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from utilidades.mensajes import MensajesInterfaz


class BarraEstado(QFrame):
    """Widget simple para mostrar el estado actual de la aplicacion."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("barraEstado")
        self._indicador = QFrame()
        self._indicador.setObjectName("indicadorEstadoNeutro")
        self._etiqueta_titulo = QLabel("Estado del sistema")
        self._etiqueta_titulo.setObjectName("tituloBloque")
        self._etiqueta_mensaje = QLabel(MensajesInterfaz.LISTO)
        self._etiqueta_mensaje.setObjectName("mensajeBarraEstado")
        self._configurar_interfaz()

    def _configurar_interfaz(self) -> None:
        disposicion = QHBoxLayout(self)
        disposicion.setContentsMargins(14, 8, 14, 8)
        disposicion.setSpacing(10)
        self._indicador.setFixedSize(10, 10)
        disposicion.addWidget(self._indicador)
        disposicion.addWidget(self._etiqueta_titulo)
        disposicion.addWidget(self._etiqueta_mensaje)
        disposicion.addStretch(1)

    def actualizar_mensaje(self, mensaje: str) -> None:
        """Actualiza el texto mostrado en la barra."""
        self._etiqueta_mensaje.setText(mensaje)
        self._indicador.setObjectName(self._obtener_indicador(mensaje))
        self.style().unpolish(self._indicador)
        self.style().polish(self._indicador)

    def _obtener_indicador(self, mensaje: str) -> str:
        mensaje_normalizado = mensaje.lower()

        if "error" in mensaje_normalizado or "no fue posible" in mensaje_normalizado:
            return "indicadorEstadoError"
        if "invalida" in mensaje_normalizado or "invalido" in mensaje_normalizado:
            return "indicadorEstadoAdvertencia"
        if "exportado" in mensaje_normalizado or "cargado correctamente" in mensaje_normalizado:
            return "indicadorEstadoCorrecto"
        if "procesando" in mensaje_normalizado:
            return "indicadorEstadoInfo"
        return "indicadorEstadoNeutro"
