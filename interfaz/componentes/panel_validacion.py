"""Panel visual para el estado de validacion estructural."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QSizePolicy,
    QVBoxLayout,
)

from modelos.resultado_validacion import ResultadoValidacion


class PanelValidacion(QFrame):
    """Presenta el estado de columnas encontradas y faltantes."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panelValidacion")

        self._estado = QLabel("Pendiente")
        self._detalle = QLabel("La validacion se mostrara despues de cargar un archivo.")
        self._contador_encontradas = QLabel("0")
        self._contador_faltantes = QLabel("0")
        self._contador_mapeadas = QLabel("0")
        self._contador_desconocidas = QLabel("0")
        self._lista_encontradas = QListWidget()
        self._lista_faltantes = QListWidget()
        self._lista_mapeadas = QListWidget()
        self._lista_desconocidas = QListWidget()

        self._configurar_interfaz()
        self.limpiar()

    def _configurar_interfaz(self) -> None:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        disposicion_principal = QVBoxLayout(self)
        disposicion_principal.setContentsMargins(22, 22, 22, 22)
        disposicion_principal.setSpacing(16)

        titulo = QLabel("Validacion estructural")
        titulo.setObjectName("tituloSubpanel")

        cabecera = QHBoxLayout()
        cabecera.setContentsMargins(0, 0, 0, 0)
        cabecera.setSpacing(10)
        cabecera.addWidget(titulo)
        cabecera.addStretch(1)
        cabecera.addWidget(self._estado)

        self._estado.setObjectName("insigniaNeutra")
        self._detalle.setObjectName("textoSecundario")
        self._detalle.setWordWrap(True)

        observacion = QFrame(self)
        observacion.setObjectName("subbloquePanel")
        observacion.setMinimumHeight(96)
        disposicion_observacion = QVBoxLayout(observacion)
        disposicion_observacion.setContentsMargins(16, 15, 16, 15)
        disposicion_observacion.setSpacing(8)

        etiqueta_observacion = QLabel("Observaciones")
        etiqueta_observacion.setObjectName("tituloBloque")

        disposicion_observacion.addWidget(etiqueta_observacion)
        disposicion_observacion.addWidget(self._detalle)

        resumen = QGridLayout()
        resumen.setHorizontalSpacing(14)
        resumen.setVerticalSpacing(14)
        resumen.addWidget(self._crear_resumen("Encontradas", self._contador_encontradas), 0, 0)
        resumen.addWidget(self._crear_resumen("Faltantes", self._contador_faltantes), 0, 1)
        resumen.addWidget(self._crear_resumen("Mapeadas por alias", self._contador_mapeadas), 0, 2)
        resumen.addWidget(self._crear_resumen("Adicionales", self._contador_desconocidas), 0, 3)
        for columna in range(4):
            resumen.setColumnStretch(columna, 1)

        bloques = QGridLayout()
        bloques.setHorizontalSpacing(14)
        bloques.setVerticalSpacing(14)
        bloques.addWidget(self._crear_bloque_lista("Columnas encontradas", self._lista_encontradas), 0, 0)
        bloques.addWidget(self._crear_bloque_lista("Columnas faltantes", self._lista_faltantes), 0, 1)
        bloques.addWidget(self._crear_bloque_lista("Mapeadas por alias", self._lista_mapeadas), 1, 0)
        bloques.addWidget(self._crear_bloque_lista("Columnas adicionales", self._lista_desconocidas), 1, 1)
        bloques.setColumnStretch(0, 1)
        bloques.setColumnStretch(1, 1)
        bloques.setRowStretch(0, 1)
        bloques.setRowStretch(1, 1)

        disposicion_principal.addLayout(cabecera)
        disposicion_principal.addLayout(resumen)
        disposicion_principal.addWidget(observacion)
        disposicion_principal.addLayout(bloques)

    def _crear_bloque_lista(self, titulo: str, lista: QListWidget) -> QFrame:
        contenedor = QFrame()
        contenedor.setObjectName("subbloquePanel")
        contenedor.setMinimumHeight(176)
        contenedor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        disposicion = QVBoxLayout(contenedor)
        disposicion.setContentsMargins(16, 15, 16, 15)
        disposicion.setSpacing(8)

        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("tituloBloque")

        lista.setMinimumHeight(132)
        lista.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        disposicion.addWidget(etiqueta)
        disposicion.addWidget(lista)
        return contenedor

    def _crear_resumen(self, titulo: str, valor: QLabel) -> QFrame:
        contenedor = QFrame()
        contenedor.setObjectName("tarjetaMetrica")
        contenedor.setMinimumHeight(102)

        disposicion = QVBoxLayout(contenedor)
        disposicion.setContentsMargins(16, 14, 16, 14)
        disposicion.setSpacing(8)

        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("etiquetaMetrica")
        valor.setObjectName("contadorListaNeutro")

        disposicion.addWidget(etiqueta)
        disposicion.addWidget(valor)
        return contenedor

    def actualizar_desde_resultado(
        self,
        resultado: ResultadoValidacion | None,
        resumen: dict[str, object] | None = None,
    ) -> None:
        """Muestra el resultado de validacion en el panel."""
        if resultado is None:
            self.limpiar()
            return

        resumen = resumen or {}
        self._estado.setText("Valida" if resultado.estructura_valida else "Invalida")
        self._estado.setObjectName("insigniaCorrecta" if resultado.estructura_valida else "insigniaError")
        self._detalle.setText(resultado.mensaje)
        self._actualizar_estilo_estado()

        columnas_encontradas = list(resumen.get("columnas_encontradas", []))
        columnas_faltantes = list(resumen.get("columnas_faltantes", []))
        mapeadas = [
            f"{columna_canonica} <- {columna_original}"
            for columna_canonica, columna_original in dict(
                resumen.get("columnas_mapeadas_por_alias", {})
            ).items()
        ]
        columnas_desconocidas = list(resumen.get("columnas_desconocidas", []))

        self._actualizar_contador(self._contador_encontradas, len(columnas_encontradas), "correcto")
        self._actualizar_contador(
            self._contador_faltantes,
            len(columnas_faltantes),
            "error" if columnas_faltantes else "correcto",
        )
        self._actualizar_contador(
            self._contador_mapeadas,
            len(mapeadas),
            "info" if mapeadas else "neutro",
        )
        self._actualizar_contador(
            self._contador_desconocidas,
            len(columnas_desconocidas),
            "advertencia" if columnas_desconocidas else "neutro",
        )

        self._cargar_lista(self._lista_encontradas, columnas_encontradas, "Sin coincidencias.")
        self._cargar_lista(self._lista_faltantes, columnas_faltantes, "No faltan columnas.")
        self._cargar_lista(self._lista_mapeadas, mapeadas, "No hubo mapeos por alias.")
        self._cargar_lista(
            self._lista_desconocidas,
            columnas_desconocidas,
            "No se detectaron columnas adicionales.",
        )

    def limpiar(self) -> None:
        """Restablece el estado inicial del panel."""
        self._estado.setText("Pendiente")
        self._estado.setObjectName("insigniaNeutra")
        self._detalle.setText("La validacion se mostrara despues de cargar un archivo.")
        self._actualizar_estilo_estado()
        self._actualizar_contador(self._contador_encontradas, 0, "neutro")
        self._actualizar_contador(self._contador_faltantes, 0, "neutro")
        self._actualizar_contador(self._contador_mapeadas, 0, "neutro")
        self._actualizar_contador(self._contador_desconocidas, 0, "neutro")
        self._cargar_lista(self._lista_encontradas, [], "Sin datos.")
        self._cargar_lista(self._lista_faltantes, [], "Sin datos.")
        self._cargar_lista(self._lista_mapeadas, [], "Sin datos.")
        self._cargar_lista(self._lista_desconocidas, [], "Sin datos.")

    def _actualizar_estilo_estado(self) -> None:
        self.style().unpolish(self._estado)
        self.style().polish(self._estado)

    def _actualizar_contador(self, etiqueta: QLabel, cantidad: int, estado: str) -> None:
        nombre_estilo = {
            "neutro": "contadorListaNeutro",
            "correcto": "contadorListaCorrecto",
            "advertencia": "contadorListaAdvertencia",
            "error": "contadorListaError",
            "info": "contadorListaInfo",
        }.get(estado, "contadorListaNeutro")

        etiqueta.setText(str(cantidad))
        etiqueta.setObjectName(nombre_estilo)
        self.style().unpolish(etiqueta)
        self.style().polish(etiqueta)

    def _cargar_lista(self, lista: QListWidget, valores: list[str], mensaje_vacio: str) -> None:
        lista.clear()
        lista.addItems(valores or [mensaje_vacio])
