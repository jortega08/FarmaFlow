"""Panel visual para el resumen de preclasificacion."""

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

from modelos.resultado_preclasificacion import ResultadoPreclasificacion


class PanelPreclasificacion(QFrame):
    """Presenta totales y conteos de la preclasificacion preliminar."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panelPreclasificacion")

        self._estado = QLabel("Pendiente")
        self._detalle = QLabel("La preclasificacion se mostrara despues de la validacion.")
        self._valor_registros = QLabel("-")
        self._valor_clasificados = QLabel("-")
        self._valor_sin_clasificar = QLabel("-")
        self._valor_tipologias = QLabel("-")
        self._valor_farmacias = QLabel("-")
        self._contador_tipologias = QLabel("0")
        self._contador_farmacias = QLabel("0")
        self._lista_tipologias = QListWidget()
        self._lista_farmacias = QListWidget()

        self._configurar_interfaz()
        self.limpiar()

    def _configurar_interfaz(self) -> None:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        disposicion_principal = QVBoxLayout(self)
        disposicion_principal.setContentsMargins(22, 22, 22, 22)
        disposicion_principal.setSpacing(16)

        titulo = QLabel("Resultados de preclasificacion")
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

        etiqueta_observacion = QLabel("Resumen operativo")
        etiqueta_observacion.setObjectName("tituloBloque")

        disposicion_observacion.addWidget(etiqueta_observacion)
        disposicion_observacion.addWidget(self._detalle)

        metricas = QGridLayout()
        metricas.setHorizontalSpacing(14)
        metricas.setVerticalSpacing(14)
        for columna in range(3):
            metricas.setColumnStretch(columna, 1)

        definiciones_metricas = (
            ("Registros", self._valor_registros),
            ("Clasificados", self._valor_clasificados),
            ("Sin clasificar", self._valor_sin_clasificar),
            ("Tipologias detectadas", self._valor_tipologias),
            ("Farmacias detectadas", self._valor_farmacias),
        )

        for indice, (titulo_metrica, valor) in enumerate(definiciones_metricas):
            fila = indice // 3
            columna = indice % 3
            metricas.addWidget(self._crear_tarjeta_metrica(titulo_metrica, valor), fila, columna)

        bloques = QGridLayout()
        bloques.setHorizontalSpacing(14)
        bloques.setVerticalSpacing(14)
        bloques.addWidget(
            self._crear_bloque_lista("Tipologias detectadas", self._contador_tipologias, self._lista_tipologias),
            0,
            0,
        )
        bloques.addWidget(
            self._crear_bloque_lista("Farmacias detectadas", self._contador_farmacias, self._lista_farmacias),
            0,
            1,
        )
        bloques.setColumnStretch(0, 1)
        bloques.setColumnStretch(1, 1)
        bloques.setRowStretch(0, 1)

        disposicion_principal.addLayout(cabecera)
        disposicion_principal.addLayout(metricas)
        disposicion_principal.addWidget(observacion)
        disposicion_principal.addLayout(bloques)

    def _crear_bloque_lista(self, titulo: str, contador: QLabel, lista: QListWidget) -> QFrame:
        contenedor = QFrame()
        contenedor.setObjectName("subbloquePanel")
        contenedor.setMinimumHeight(200)
        contenedor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        disposicion = QVBoxLayout(contenedor)
        disposicion.setContentsMargins(16, 15, 16, 15)
        disposicion.setSpacing(8)

        encabezado = QHBoxLayout()
        encabezado.setContentsMargins(0, 0, 0, 0)
        encabezado.setSpacing(8)

        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("tituloBloque")
        contador.setObjectName("contadorListaNeutro")

        encabezado.addWidget(etiqueta)
        encabezado.addStretch(1)
        encabezado.addWidget(contador)

        lista.setMinimumHeight(148)
        lista.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        disposicion.addLayout(encabezado)
        disposicion.addWidget(lista)
        return contenedor

    def _crear_tarjeta_metrica(self, titulo: str, valor: QLabel) -> QFrame:
        contenedor = QFrame()
        contenedor.setObjectName("tarjetaMetrica")
        contenedor.setMinimumHeight(104)

        disposicion = QVBoxLayout(contenedor)
        disposicion.setContentsMargins(16, 14, 16, 14)
        disposicion.setSpacing(8)

        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("etiquetaMetrica")
        valor.setObjectName("valorMetrica")

        disposicion.addWidget(etiqueta)
        disposicion.addWidget(valor)
        return contenedor

    def actualizar_desde_resultado(
        self,
        resultado: ResultadoPreclasificacion | None,
        resumen: dict[str, object] | None = None,
    ) -> None:
        """Muestra el estado de preclasificacion disponible."""
        if resultado is None:
            self.mostrar_no_disponible(
                "La preclasificacion no se ejecuto porque la estructura aun no es valida."
            )
            return

        resumen = resumen or {}
        self._estado.setText("Disponible")
        self._estado.setObjectName("insigniaCorrecta")
        self._detalle.setText(resultado.mensaje)
        self._actualizar_estilo_estado()

        self._valor_registros.setText(str(resumen.get("cantidad_registros", resultado.cantidad_registros)))
        self._valor_clasificados.setText(
            str(resumen.get("cantidad_clasificados", resultado.cantidad_clasificados))
        )
        self._valor_sin_clasificar.setText(
            str(resumen.get("cantidad_sin_clasificar", resultado.cantidad_sin_clasificar))
        )
        self._valor_tipologias.setText(
            str(resumen.get("cantidad_tipologias_detectadas", len(resultado.tipologias_detectadas)))
        )
        self._valor_farmacias.setText(
            str(resumen.get("cantidad_farmacias_detectadas", len(resultado.farmacias_detectadas)))
        )

        tipologias = [
            f"{tipologia}: {cantidad}"
            for tipologia, cantidad in dict(resumen.get("tipologias_detectadas", {})).items()
        ]
        farmacias = [
            f"{farmacia}: {cantidad}"
            for farmacia, cantidad in dict(resumen.get("farmacias_detectadas", {})).items()
        ]

        self._actualizar_contador(
            self._contador_tipologias,
            int(resumen.get("cantidad_tipologias_detectadas", len(resultado.tipologias_detectadas))),
            "info" if tipologias else "neutro",
        )
        self._actualizar_contador(
            self._contador_farmacias,
            int(resumen.get("cantidad_farmacias_detectadas", len(resultado.farmacias_detectadas))),
            "info" if farmacias else "neutro",
        )
        self._cargar_lista(self._lista_tipologias, tipologias, "Sin tipologias detectadas.")
        self._cargar_lista(self._lista_farmacias, farmacias, "Sin farmacias detectadas.")

    def mostrar_no_disponible(self, mensaje: str) -> None:
        """Muestra el panel como no ejecutado."""
        self._estado.setText("No disponible")
        self._estado.setObjectName("insigniaAdvertencia")
        self._detalle.setText(mensaje)
        self._actualizar_estilo_estado()
        self._valor_registros.setText("-")
        self._valor_clasificados.setText("-")
        self._valor_sin_clasificar.setText("-")
        self._valor_tipologias.setText("-")
        self._valor_farmacias.setText("-")
        self._actualizar_contador(self._contador_tipologias, 0, "neutro")
        self._actualizar_contador(self._contador_farmacias, 0, "neutro")
        self._cargar_lista(self._lista_tipologias, [], "Sin resultados.")
        self._cargar_lista(self._lista_farmacias, [], "Sin resultados.")

    def limpiar(self) -> None:
        """Restablece el estado inicial del panel."""
        self.mostrar_no_disponible("La preclasificacion se mostrara despues de la validacion.")

    def _actualizar_estilo_estado(self) -> None:
        self.style().unpolish(self._estado)
        self.style().polish(self._estado)

    def _actualizar_contador(self, etiqueta: QLabel, cantidad: int, estado: str) -> None:
        nombre_estilo = {
            "neutro": "contadorListaNeutro",
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
