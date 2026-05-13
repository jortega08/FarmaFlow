"""Panel para mostrar la informacion del archivo cargado."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout

from modelos.resultado_carga import ResultadoCarga


class PanelInformacionArchivo(QFrame):
    """Presenta los metadatos basicos del archivo leido."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panelArchivo")

        self._valor_nombre = QLabel("-")
        self._valor_hoja = QLabel("-")
        self._estado_estructura = QLabel("Pendiente")
        self._metricas: dict[str, QLabel] = {}

        self._configurar_interfaz()
        self.limpiar()

    def _configurar_interfaz(self) -> None:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        disposicion_principal = QVBoxLayout(self)
        disposicion_principal.setContentsMargins(22, 22, 22, 22)
        disposicion_principal.setSpacing(16)

        titulo = QLabel("Resumen general")
        titulo.setObjectName("tituloSeccion")

        descripcion = QLabel(
            "Vista ejecutiva del archivo procesado, la estructura detectada y los indicadores principales del flujo."
        )
        descripcion.setObjectName("textoSecundario")
        descripcion.setWordWrap(True)

        self._valor_nombre.setObjectName("valorCampo")
        self._valor_nombre.setWordWrap(True)
        self._valor_hoja.setObjectName("valorCampo")
        self._valor_hoja.setWordWrap(True)

        datos_principales = QGridLayout()
        datos_principales.setHorizontalSpacing(14)
        datos_principales.setVerticalSpacing(14)
        datos_principales.addWidget(self._crear_bloque_dato("Archivo cargado", self._valor_nombre), 0, 0, 1, 2)
        datos_principales.addWidget(self._crear_bloque_dato("Hoja utilizada", self._valor_hoja), 0, 2)
        datos_principales.addWidget(self._crear_bloque_dato("Estado estructural", self._estado_estructura), 0, 3)
        for columna in range(4):
            datos_principales.setColumnStretch(columna, 1)

        grilla_metricas = QGridLayout()
        grilla_metricas.setHorizontalSpacing(14)
        grilla_metricas.setVerticalSpacing(14)
        for columna in range(3):
            grilla_metricas.setColumnStretch(columna, 1)

        definiciones_metricas = (
            ("total_registros", "Total registros"),
            ("total_columnas", "Total columnas"),
            ("farmacias_detectadas", "Farmacias detectadas"),
            ("registros_clasificados", "Clasificados"),
            ("registros_sin_clasificar", "Sin clasificar"),
        )

        for indice, (clave, titulo_metrica) in enumerate(definiciones_metricas):
            fila = indice // 3
            columna = indice % 3
            tarjeta, valor = self._crear_tarjeta_metrica(titulo_metrica)
            self._metricas[clave] = valor
            grilla_metricas.addWidget(tarjeta, fila, columna)

        disposicion_principal.addWidget(titulo)
        disposicion_principal.addWidget(descripcion)
        disposicion_principal.addLayout(datos_principales)
        disposicion_principal.addLayout(grilla_metricas)

    def actualizar_desde_resultado(self, resultado: ResultadoCarga) -> None:
        """Carga la informacion de un resultado en la interfaz."""
        self._valor_nombre.setText(resultado.nombre_archivo or "-")
        self._valor_hoja.setText(resultado.hoja_utilizada or "-")

        self._estado_estructura.setText("Valida" if resultado.estructura_valida else "Invalida")
        self._estado_estructura.setObjectName("insigniaCorrecta" if resultado.estructura_valida else "insigniaError")
        self._aplicar_estilo(self._estado_estructura)

        resumen_preclasificacion = resultado.resumen_preclasificacion or {}
        preclasificacion_disponible = resultado.resultado_preclasificacion is not None

        self._metricas["total_registros"].setText(str(resultado.cantidad_filas))
        self._metricas["total_columnas"].setText(str(resultado.cantidad_columnas))
        self._metricas["farmacias_detectadas"].setText(
            str(resumen_preclasificacion.get("cantidad_farmacias_detectadas", "-")) if preclasificacion_disponible else "-"
        )
        self._metricas["registros_clasificados"].setText(
            str(resumen_preclasificacion.get("cantidad_clasificados", "-")) if preclasificacion_disponible else "-"
        )
        self._metricas["registros_sin_clasificar"].setText(
            str(resumen_preclasificacion.get("cantidad_sin_clasificar", "-")) if preclasificacion_disponible else "-"
        )

    def limpiar(self) -> None:
        """Restablece los valores iniciales del panel."""
        self._valor_nombre.setText("-")
        self._valor_hoja.setText("-")
        self._estado_estructura.setText("Pendiente")
        self._estado_estructura.setObjectName("insigniaNeutra")
        self._aplicar_estilo(self._estado_estructura)

        for valor in self._metricas.values():
            valor.setText("-")

    def _crear_bloque_dato(self, titulo: str, valor: QLabel) -> QFrame:
        contenedor = QFrame(self)
        contenedor.setObjectName("subbloquePanel")
        contenedor.setMinimumHeight(92)

        disposicion = QVBoxLayout(contenedor)
        disposicion.setContentsMargins(16, 15, 16, 15)
        disposicion.setSpacing(8)

        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("tituloBloque")

        disposicion.addWidget(etiqueta)
        disposicion.addWidget(valor)
        return contenedor

    def _crear_tarjeta_metrica(self, titulo: str) -> tuple[QFrame, QLabel]:
        contenedor = QFrame(self)
        contenedor.setObjectName("tarjetaMetrica")
        contenedor.setMinimumHeight(106)

        disposicion = QVBoxLayout(contenedor)
        disposicion.setContentsMargins(16, 15, 16, 15)
        disposicion.setSpacing(8)

        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("etiquetaMetrica")

        valor = QLabel("-")
        valor.setObjectName("valorMetrica")

        disposicion.addWidget(etiqueta)
        disposicion.addWidget(valor)
        disposicion.addStretch(1)
        return contenedor, valor

    def _aplicar_estilo(self, widget: QLabel) -> None:
        self.style().unpolish(widget)
        self.style().polish(widget)
