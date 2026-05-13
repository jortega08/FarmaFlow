"""Panel de botones principales para la carga del archivo."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QSizePolicy, QVBoxLayout, QWidget


class PanelAcciones(QWidget):
    """Agrupa las acciones principales de la vista de carga."""

    solicitar_seleccion = Signal()
    solicitar_carga = Signal()
    solicitar_exportacion = Signal()
    solicitar_limpieza = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._boton_seleccionar = QPushButton("Seleccionar archivo")
        self._boton_cargar = QPushButton("Procesar archivo")
        self._boton_exportar = QPushButton("Exportar resultado")
        self._boton_limpiar = QPushButton("Limpiar")
        self._configurar_interfaz()
        self._conectar_eventos()
        self.actualizar_estado_botones(hay_archivo=False, puede_exportar=False)

    def _configurar_interfaz(self) -> None:
        self._boton_seleccionar.setObjectName("botonSecundario")
        self._boton_cargar.setObjectName("botonPrincipal")
        self._boton_exportar.setObjectName("botonExito")
        self._boton_limpiar.setObjectName("botonTerciario")

        for boton in (
            self._boton_seleccionar,
            self._boton_cargar,
            self._boton_exportar,
            self._boton_limpiar,
        ):
            boton.setMinimumHeight(44)
            boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.setSpacing(12)
        disposicion.addWidget(self._boton_seleccionar)
        disposicion.addWidget(self._boton_cargar)
        disposicion.addWidget(self._boton_exportar)
        disposicion.addWidget(self._boton_limpiar)

    def _conectar_eventos(self) -> None:
        self._boton_seleccionar.clicked.connect(self.solicitar_seleccion.emit)
        self._boton_cargar.clicked.connect(self.solicitar_carga.emit)
        self._boton_exportar.clicked.connect(self.solicitar_exportacion.emit)
        self._boton_limpiar.clicked.connect(self.solicitar_limpieza.emit)

    def actualizar_estado_botones(self, hay_archivo: bool, puede_exportar: bool) -> None:
        """Habilita o deshabilita acciones segun el estado de la vista."""
        self._boton_cargar.setEnabled(hay_archivo)
        self._boton_exportar.setEnabled(puede_exportar)
        self._boton_limpiar.setEnabled(hay_archivo)
