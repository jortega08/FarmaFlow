"""Vista de bienvenida de la aplicacion."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


class VistaInicio(QFrame):
    """Presenta un resumen de la aplicacion y el acceso rapido a la carga."""

    solicitar_seleccion_archivo = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("tarjeta")
        self._configurar_interfaz()

    def _configurar_interfaz(self) -> None:
        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(22, 22, 22, 22)
        disposicion.setSpacing(12)

        titulo = QLabel("Inicio")
        titulo.setObjectName("tituloSeccion")

        descripcion = QLabel(
            "Esta aplicacion permite seleccionar un archivo Excel exportado desde Oracle, "
            "leerlo de forma segura y mostrar un resumen basico de su estructura."
        )
        descripcion.setObjectName("textoSecundario")
        descripcion.setWordWrap(True)

        aclaracion = QLabel(
            "La version actual esta preparada para la estructura principal de Oracle. "
            "La compatibilidad con SAP no forma parte de esta fase."
        )
        aclaracion.setObjectName("textoSecundario")
        aclaracion.setWordWrap(True)

        boton = QPushButton("Seleccionar archivo")
        boton.clicked.connect(self.solicitar_seleccion_archivo.emit)

        disposicion.addWidget(titulo)
        disposicion.addWidget(descripcion)
        disposicion.addWidget(aclaracion)
        disposicion.addWidget(boton, 0)
