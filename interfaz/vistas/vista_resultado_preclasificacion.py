"""Vista de resultado de preclasificacion."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from interfaz.componentes.tarjeta_metrica import TarjetaMetrica
from modelos.resultado_carga import ResultadoCarga


_FILAS_POR_PAGINA = 10
_SIN_CLASIFICAR = "SIN_CLASIFICAR"
_COLORES_TIPOLOGIA = (
    "#2B6C58",
    "#124E78",
    "#0B3F66",
    "#D97706",
    "#B42318",
    "#083556",
)


class VistaResultadoPreclasificacion(QWidget):
    """Pantalla de resultado de la preclasificacion."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._resultado_carga: ResultadoCarga | None = None
        self._dataframe: pd.DataFrame | None = None
        self._dataframe_filtrado: pd.DataFrame = pd.DataFrame()
        self._pagina_actual = 1
        self._filas_por_pagina = _FILAS_POR_PAGINA
        self._animaciones: list[QPropertyAnimation] = []
        self._bloqueando_filtros = False

        self._construir_ui()
        self.limpiar_resultado()

    # ------------------------------------------------------------------
    # Construccion
    # ------------------------------------------------------------------

    def _construir_ui(self) -> None:
        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorVista")
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)

        layout.addWidget(self._crear_titulo())
        layout.addLayout(self._crear_kpis())
        layout.addWidget(self._crear_distribucion())
        layout.addWidget(self._crear_filtros())
        layout.addWidget(self._crear_tabla_resultado())
        layout.addWidget(self._crear_excepciones())
        layout.addStretch(1)

        scroll.setWidget(contenedor)
        layout_raiz.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        icono = QLabel("RS")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(50, 50)
        icono.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setSpacing(4)
        titulo = QLabel("4. Resultado de preclasificacion")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Revise tipologias detectadas, filtre registros y resuelva excepciones antes de exportar."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)

        layout.addWidget(icono)
        layout.addLayout(textos, 1)
        return card

    def _crear_kpis(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(16)
        self._kpi_total = TarjetaMetrica(
            "Registros procesados",
            "0",
            icono="REG",
            tipo="info",
            descripcion="Total de registros evaluados",
        )
        self._kpi_clasificados = TarjetaMetrica(
            "Clasificados",
            "0",
            icono="OK",
            tipo="exito",
            descripcion="0,00% del total",
        )
        self._kpi_sin_clasificar = TarjetaMetrica(
            "Sin clasificar",
            "0",
            icono="REV",
            tipo="advertencia",
            descripcion="0,00% del total",
        )
        self._kpi_tipologias = TarjetaMetrica(
            "Tipologias detectadas",
            "0",
            icono="TIP",
            tipo="neutro",
            descripcion="Incluye sin clasificar",
        )
        for tarjeta in (
            self._kpi_total,
            self._kpi_clasificados,
            self._kpi_sin_clasificar,
            self._kpi_tipologias,
        ):
            fila.addWidget(tarjeta)
        return fila

    def _crear_distribucion(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(24)

        panel = QVBoxLayout()
        panel.setSpacing(8)
        titulo = QLabel("Distribucion por tipologia")
        titulo.setObjectName("tituloSubpanel")
        self._layout_distribucion = QVBoxLayout()
        self._layout_distribucion.setSpacing(7)
        panel.addWidget(titulo)
        panel.addLayout(self._layout_distribucion)

        resumen = QFrame()
        resumen.setObjectName("subbloquePanel")
        resumen.setFixedWidth(170)
        resumen_layout = QVBoxLayout(resumen)
        resumen_layout.setContentsMargins(14, 14, 14, 14)
        resumen_layout.setSpacing(4)
        lbl_total = QLabel("Total procesados")
        lbl_total.setObjectName("textoSecundario")
        self._lbl_total_distribucion = QLabel("0")
        self._lbl_total_distribucion.setObjectName("valorMetrica")
        self._lbl_total_distribucion.setAlignment(Qt.AlignCenter)
        lbl_pct = QLabel("100%")
        lbl_pct.setObjectName("textoSecundario")
        lbl_pct.setAlignment(Qt.AlignCenter)
        resumen_layout.addWidget(lbl_total)
        resumen_layout.addWidget(self._lbl_total_distribucion)
        resumen_layout.addWidget(lbl_pct)
        resumen_layout.addStretch(1)

        layout.addLayout(panel, 1)
        layout.addWidget(resumen)
        return card

    def _crear_filtros(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QGridLayout(card)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(6)

        self._combo_tipologia = self._combo_filtro()
        self._combo_farmacia = self._combo_filtro()
        self._combo_estado = self._combo_filtro()
        self._combo_regla = self._combo_filtro()
        self._buscador = QLineEdit()
        self._buscador.setPlaceholderText("Buscar por codigo o descripcion")
        self._buscador.textChanged.connect(self._aplicar_filtros)

        filtros = (
            ("Tipologia", self._combo_tipologia),
            ("Farmacia", self._combo_farmacia),
            ("Estado", self._combo_estado),
            ("Regla aplicada", self._combo_regla),
            ("Buscar articulo", self._buscador),
        )
        for columna, (etiqueta, widget) in enumerate(filtros):
            lbl = QLabel(etiqueta)
            lbl.setObjectName("tituloBloque")
            layout.addWidget(lbl, 0, columna)
            layout.addWidget(widget, 1, columna)
            layout.setColumnStretch(columna, 1)

        limpiar = QPushButton("Limpiar filtros")
        limpiar.setObjectName("botonTerciario")
        limpiar.setMinimumHeight(36)
        limpiar.setFixedWidth(150)
        limpiar.clicked.connect(self._limpiar_filtros)
        layout.addWidget(limpiar, 2, len(filtros) - 1, alignment=Qt.AlignRight)
        return card

    def _crear_tabla_resultado(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        self._tabla_resultado = QTableWidget(0, 7)
        self._tabla_resultado.setHorizontalHeaderLabels(
            ["ARTICULO", "DESCRIPCION", "ORIGEN", "DESTINO", "TRANSACCION", "TIPOLOGIA", "REGLA"]
        )
        encabezado = self._tabla_resultado.horizontalHeader()
        encabezado.setMinimumSectionSize(58)
        for columna, ancho in {0: 82, 2: 128, 3: 128, 4: 118, 5: 170, 6: 90}.items():
            encabezado.setSectionResizeMode(columna, QHeaderView.Fixed)
            self._tabla_resultado.setColumnWidth(columna, ancho)
        encabezado.setSectionResizeMode(1, QHeaderView.Stretch)
        self._tabla_resultado.verticalHeader().setVisible(False)
        self._tabla_resultado.verticalHeader().setDefaultSectionSize(38)
        self._tabla_resultado.setAlternatingRowColors(True)
        self._tabla_resultado.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_resultado.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_resultado.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabla_resultado.setWordWrap(False)
        self._tabla_resultado.setMinimumHeight(300)
        layout.addWidget(self._tabla_resultado)

        pie = QHBoxLayout()
        self._lbl_paginacion = QLabel("Sin registros")
        self._lbl_paginacion.setObjectName("textoSecundario")
        self._boton_inicio = self._boton_paginacion("<<", self._ir_primera_pagina)
        self._boton_anterior = self._boton_paginacion("<", self._ir_anterior)
        self._lbl_pagina = QLabel("1")
        self._lbl_pagina.setObjectName("insigniaInfo")
        self._lbl_pagina.setAlignment(Qt.AlignCenter)
        self._lbl_pagina.setFixedWidth(36)
        self._boton_siguiente = self._boton_paginacion(">", self._ir_siguiente)
        self._boton_final = self._boton_paginacion(">>", self._ir_ultima_pagina)
        self._combo_filas = ComboScrollSafe()
        for valor in ("10", "20", "50"):
            self._combo_filas.addItem(f"{valor} por pagina", int(valor))
        self._combo_filas.addItem("Todas", 0)
        self._combo_filas.currentIndexChanged.connect(self._cambiar_filas_pagina)

        pie.addWidget(self._lbl_paginacion)
        pie.addStretch(1)
        for widget in (
            self._boton_inicio,
            self._boton_anterior,
            self._lbl_pagina,
            self._boton_siguiente,
            self._boton_final,
            self._combo_filas,
        ):
            pie.addWidget(widget)
        layout.addLayout(pie)
        return card

    def _crear_excepciones(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        panel = QVBoxLayout()
        panel.setSpacing(10)
        cab = QVBoxLayout()
        titulo = QLabel("Excepciones / Sin clasificar")
        titulo.setObjectName("tituloSubpanel")
        subtitulo = QLabel("Revise grupos sin clasificar para mejorar la precision del modelo.")
        subtitulo.setObjectName("textoSecundario")
        cab.addWidget(titulo)
        cab.addWidget(subtitulo)

        self._tabla_excepciones = QTableWidget(0, 3)
        self._tabla_excepciones.setHorizontalHeaderLabels(["GRUPO", "REGISTROS", "ACCION SUGERIDA"])
        encabezado = self._tabla_excepciones.horizontalHeader()
        encabezado.setSectionResizeMode(0, QHeaderView.Stretch)
        encabezado.setSectionResizeMode(1, QHeaderView.Fixed)
        encabezado.setSectionResizeMode(2, QHeaderView.Fixed)
        self._tabla_excepciones.setColumnWidth(1, 120)
        self._tabla_excepciones.setColumnWidth(2, 230)
        self._tabla_excepciones.verticalHeader().setVisible(False)
        self._tabla_excepciones.verticalHeader().setDefaultSectionSize(42)
        self._tabla_excepciones.setAlternatingRowColors(True)
        self._tabla_excepciones.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_excepciones.setWordWrap(False)
        self._tabla_excepciones.setMinimumHeight(160)

        panel.addLayout(cab)
        panel.addWidget(self._tabla_excepciones)

        aside = QFrame()
        aside.setObjectName("subbloquePanel")
        aside.setFixedWidth(270)
        aside_layout = QVBoxLayout(aside)
        aside_layout.setContentsMargins(16, 14, 16, 14)
        aside_layout.setSpacing(8)
        titulo_aside = QLabel("Lista para reprocesar")
        titulo_aside.setObjectName("valorCampo")
        self._lbl_reproceso = QLabel("Resuelva excepciones y reprocese para obtener una clasificacion mas precisa.")
        self._lbl_reproceso.setObjectName("textoSecundario")
        self._lbl_reproceso.setWordWrap(True)
        boton = QPushButton("Reprocesar clasificacion")
        boton.setObjectName("botonPrincipal")
        boton.setMinimumHeight(42)
        boton.clicked.connect(self._reprocesar_info)
        aside_layout.addWidget(titulo_aside)
        aside_layout.addWidget(self._lbl_reproceso)
        aside_layout.addStretch(1)
        aside_layout.addWidget(boton)

        layout.addLayout(panel, 1)
        layout.addWidget(aside)
        return card

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def establecer_resultado_carga(self, resultado: ResultadoCarga) -> None:
        """Muestra el resultado de preclasificacion del archivo cargado."""
        self._resultado_carga = resultado
        dataframe = resultado.dataframe_procesado
        if dataframe is None and resultado.resultado_preclasificacion is not None:
            dataframe = resultado.resultado_preclasificacion.dataframe_resultado
        if dataframe is None:
            dataframe = resultado.dataframe
        self._dataframe = dataframe.copy(deep=True) if dataframe is not None else pd.DataFrame()
        self._preparar_dataframe()
        self._cargar_filtros()
        self._aplicar_filtros()
        self._actualizar_kpis()
        self._actualizar_distribucion()
        self._actualizar_excepciones()
        self._animar_entrada(self._tabla_resultado)

    def limpiar_resultado(self) -> None:
        """Limpia la vista cuando se reinicia el flujo."""
        self._resultado_carga = None
        self._dataframe = pd.DataFrame()
        self._dataframe_filtrado = pd.DataFrame()
        self._pagina_actual = 1
        self._tabla_resultado.setRowCount(0)
        self._tabla_excepciones.setRowCount(0)
        self._bloqueando_filtros = True
        for combo in (self._combo_tipologia, self._combo_farmacia, self._combo_estado, self._combo_regla):
            combo.clear()
            combo.addItem("Todas", None)
        self._buscador.clear()
        self._bloqueando_filtros = False
        self._actualizar_kpis()
        self._actualizar_distribucion()
        self._actualizar_paginacion()

    # ------------------------------------------------------------------
    # Datos y filtros
    # ------------------------------------------------------------------

    def _preparar_dataframe(self) -> None:
        if self._dataframe is None or self._dataframe.empty:
            self._dataframe = pd.DataFrame()
            return
        df = self._dataframe.copy(deep=True)
        if "TIPOLOGIA_PRELIMINAR" not in df.columns:
            df["TIPOLOGIA_PRELIMINAR"] = _SIN_CLASIFICAR
        if "REGLA_APLICADA" not in df.columns:
            df["REGLA_APLICADA"] = ""
        if "FARMACIA_DETECTADA" not in df.columns:
            df["FARMACIA_DETECTADA"] = ""
        self._dataframe = df

    def _cargar_filtros(self) -> None:
        df = self._dataframe if self._dataframe is not None else pd.DataFrame()
        self._bloqueando_filtros = True
        self._llenar_combo(self._combo_tipologia, "Todas", self._valores_unicos(df, "TIPOLOGIA_PRELIMINAR"))
        self._llenar_combo(self._combo_farmacia, "Todas", self._valores_unicos(df, "FARMACIA_DETECTADA"))
        self._llenar_combo(self._combo_regla, "Todas", self._valores_unicos(df, "REGLA_APLICADA"))
        self._combo_estado.clear()
        self._combo_estado.addItem("Todos", None)
        self._combo_estado.addItem("Clasificados", "CLASIFICADO")
        self._combo_estado.addItem("Sin clasificar", _SIN_CLASIFICAR)
        self._bloqueando_filtros = False

    def _combo_filtro(self) -> QComboBox:
        combo = ComboScrollSafe()
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        combo.currentIndexChanged.connect(self._aplicar_filtros)
        return combo

    def _llenar_combo(self, combo: QComboBox, etiqueta_todos: str, valores: list[str]) -> None:
        combo.clear()
        combo.addItem(etiqueta_todos, None)
        for valor in valores:
            combo.addItem(valor, valor)

    def _valores_unicos(self, df: pd.DataFrame, columna: str) -> list[str]:
        if columna not in df.columns or df.empty:
            return []
        serie = df[columna].fillna("").astype(str).str.strip()
        return sorted(valor for valor in serie.unique().tolist() if valor)

    def _aplicar_filtros(self, *_args: Any) -> None:
        if self._bloqueando_filtros:
            return
        df = self._dataframe if self._dataframe is not None else pd.DataFrame()
        if df.empty:
            self._dataframe_filtrado = pd.DataFrame()
            self._actualizar_tabla()
            return

        filtrado = df
        tipologia = self._combo_tipologia.currentData()
        farmacia = self._combo_farmacia.currentData()
        estado = self._combo_estado.currentData()
        regla = self._combo_regla.currentData()
        texto = self._buscador.text().strip().lower()

        if tipologia:
            filtrado = filtrado[filtrado["TIPOLOGIA_PRELIMINAR"].fillna("").astype(str) == str(tipologia)]
        if farmacia:
            filtrado = filtrado[filtrado["FARMACIA_DETECTADA"].fillna("").astype(str) == str(farmacia)]
        if regla:
            filtrado = filtrado[filtrado["REGLA_APLICADA"].fillna("").astype(str) == str(regla)]
        if estado == "CLASIFICADO":
            filtrado = filtrado[filtrado["TIPOLOGIA_PRELIMINAR"].fillna("").astype(str) != _SIN_CLASIFICAR]
        elif estado == _SIN_CLASIFICAR:
            filtrado = filtrado[filtrado["TIPOLOGIA_PRELIMINAR"].fillna("").astype(str) == _SIN_CLASIFICAR]
        if texto:
            columnas_busqueda = [col for col in ("ARTICULO", "DESCRIPCION") if col in filtrado.columns]
            if columnas_busqueda:
                mascara = pd.Series(False, index=filtrado.index)
                for columna in columnas_busqueda:
                    mascara = mascara | filtrado[columna].fillna("").astype(str).str.lower().str.contains(
                        texto,
                        regex=False,
                    )
                filtrado = filtrado[mascara]

        self._dataframe_filtrado = filtrado
        self._pagina_actual = 1
        self._actualizar_tabla()

    def _limpiar_filtros(self) -> None:
        self._bloqueando_filtros = True
        for combo in (self._combo_tipologia, self._combo_farmacia, self._combo_estado, self._combo_regla):
            combo.setCurrentIndex(0)
        self._buscador.clear()
        self._bloqueando_filtros = False
        self._aplicar_filtros()

    # ------------------------------------------------------------------
    # KPIs y distribucion
    # ------------------------------------------------------------------

    def _actualizar_kpis(self) -> None:
        df = self._dataframe if self._dataframe is not None else pd.DataFrame()
        total = int(len(df))
        tipologias = self._serie_tipologia(df)
        sin_clasificar = int((tipologias == _SIN_CLASIFICAR).sum()) if total else 0
        clasificados = total - sin_clasificar
        cantidad_tipologias = int(tipologias.nunique()) if total else 0
        pct_clasificados = self._porcentaje(clasificados, total)
        pct_sin = self._porcentaje(sin_clasificar, total)

        self._kpi_total.actualizar(self._formatear_entero(total))
        self._kpi_clasificados.actualizar(
            self._formatear_entero(clasificados),
            descripcion=f"{pct_clasificados} del total",
            estilo_valor="valorMetricaCorrecto",
        )
        self._kpi_sin_clasificar.actualizar(
            self._formatear_entero(sin_clasificar),
            descripcion=f"{pct_sin} del total",
            estilo_valor="valorMetricaAdvertencia",
        )
        self._kpi_tipologias.actualizar(str(cantidad_tipologias))
        self._lbl_total_distribucion.setText(self._formatear_entero(total))

    def _actualizar_distribucion(self) -> None:
        self._limpiar_layout(self._layout_distribucion)
        df = self._dataframe if self._dataframe is not None else pd.DataFrame()
        total = len(df)
        if total == 0:
            vacio = QLabel("No hay resultados para mostrar.")
            vacio.setObjectName("textoSecundario")
            self._layout_distribucion.addWidget(vacio)
            return

        conteos = self._serie_tipologia(df).value_counts().head(6)
        maximo = int(conteos.max()) if not conteos.empty else 1
        for indice, (tipologia, cantidad) in enumerate(conteos.items()):
            self._layout_distribucion.addLayout(
                self._crear_fila_distribucion(
                    str(tipologia),
                    int(cantidad),
                    total,
                    maximo,
                    _COLORES_TIPOLOGIA[indice % len(_COLORES_TIPOLOGIA)],
                )
            )

    def _crear_fila_distribucion(
        self,
        tipologia: str,
        cantidad: int,
        total: int,
        maximo: int,
        color: str,
    ) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(12)
        etiqueta = QLabel(self._texto_corto(tipologia, 34))
        etiqueta.setObjectName("valorCampo")
        etiqueta.setFixedWidth(210)
        barra = QProgressBar()
        barra.setRange(0, max(maximo, 1))
        barra.setValue(cantidad)
        barra.setTextVisible(False)
        barra.setFixedHeight(10)
        barra.setStyleSheet(
            "QProgressBar { background-color: #D9E2EC; border: none; border-radius: 5px; }"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 5px; }}"
        )
        lbl_cantidad = QLabel(self._formatear_entero(cantidad))
        lbl_cantidad.setObjectName("valorCampo")
        lbl_cantidad.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_cantidad.setFixedWidth(86)
        lbl_pct = QLabel(self._porcentaje(cantidad, total))
        lbl_pct.setObjectName("textoSecundario")
        lbl_pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_pct.setFixedWidth(72)
        fila.addWidget(etiqueta)
        fila.addWidget(barra, 1)
        fila.addWidget(lbl_cantidad)
        fila.addWidget(lbl_pct)
        return fila

    # ------------------------------------------------------------------
    # Tabla
    # ------------------------------------------------------------------

    def _actualizar_tabla(self) -> None:
        df = self._dataframe_filtrado if self._dataframe_filtrado is not None else pd.DataFrame()
        self._tabla_resultado.setRowCount(0)
        total = len(df)
        if total == 0:
            self._actualizar_paginacion()
            return

        if self._mostrar_todas_las_filas():
            pagina = df
        else:
            inicio = self._inicio_pagina()
            fin = inicio + self._filas_por_pagina
            pagina = df.iloc[inicio:fin]
        self._tabla_resultado.setRowCount(len(pagina))
        for fila_tabla, (_idx, fila) in enumerate(pagina.iterrows()):
            valores = [
                self._valor_fila(fila, "ARTICULO"),
                self._valor_fila(fila, "DESCRIPCION"),
                self._valor_fila(fila, "ORG_ORIGEN"),
                self._valor_fila(fila, "ORG_DESTINO"),
                self._valor_fila(fila, "TIPO_TRANSACCION"),
                self._valor_fila(fila, "TIPOLOGIA_PRELIMINAR"),
                self._valor_fila(fila, "REGLA_APLICADA") or self._valor_fila(fila, "REGLA_ID"),
            ]
            for columna, valor in enumerate(valores):
                if columna == 5:
                    self._tabla_resultado.setCellWidget(
                        fila_tabla,
                        columna,
                        self._celda_centrada(self._badge_tipologia(valor)),
                    )
                else:
                    self._set_item(self._tabla_resultado, fila_tabla, columna, valor)
            self._tabla_resultado.setRowHeight(fila_tabla, 38)
        self._actualizar_paginacion()

    def _set_item(self, tabla: QTableWidget, fila: int, columna: int, texto: str, centro: bool = False) -> None:
        item = QTableWidgetItem(str(texto))
        item.setToolTip(str(texto))
        item.setTextAlignment(Qt.AlignCenter if centro else Qt.AlignVCenter)
        tabla.setItem(fila, columna, item)

    def _badge_tipologia(self, tipologia: str) -> QLabel:
        badge = QLabel(self._texto_corto(tipologia.replace("_", " "), 28))
        badge.setAlignment(Qt.AlignCenter)
        if tipologia == _SIN_CLASIFICAR:
            badge.setObjectName("insigniaAdvertencia")
        elif "DEVOL" in tipologia:
            badge.setObjectName("insigniaInfo")
        elif "SALIDA" in tipologia:
            badge.setObjectName("insigniaAdvertencia")
        else:
            badge.setObjectName("insigniaCorrecta")
        badge.setMinimumHeight(22)
        return badge

    def _celda_centrada(self, widget: QWidget, margen: int = 5) -> QWidget:
        cont = QWidget()
        layout = QHBoxLayout(cont)
        layout.setContentsMargins(margen, 3, margen, 3)
        layout.setSpacing(0)
        layout.addWidget(widget)
        return cont

    # ------------------------------------------------------------------
    # Excepciones
    # ------------------------------------------------------------------

    def _actualizar_excepciones(self) -> None:
        self._tabla_excepciones.setRowCount(0)
        df = self._dataframe if self._dataframe is not None else pd.DataFrame()
        if df.empty or "TIPOLOGIA_PRELIMINAR" not in df.columns:
            return
        sin = df[df["TIPOLOGIA_PRELIMINAR"].fillna("").astype(str) == _SIN_CLASIFICAR]
        if sin.empty:
            return

        grupos = self._construir_grupos_excepcion(sin)
        self._tabla_excepciones.setRowCount(len(grupos))
        total = len(sin)
        for fila, (grupo, cantidad, accion) in enumerate(grupos):
            self._set_item(self._tabla_excepciones, fila, 0, grupo)
            self._set_item(
                self._tabla_excepciones,
                fila,
                1,
                f"{self._formatear_entero(cantidad)} ({self._porcentaje(cantidad, total)})",
                centro=True,
            )
            self._tabla_excepciones.setCellWidget(fila, 2, self._celda_centrada(self._boton_accion(accion), margen=6))
            self._tabla_excepciones.setRowHeight(fila, 42)

    def _construir_grupos_excepcion(self, dataframe: pd.DataFrame) -> list[tuple[str, int, str]]:
        candidatos: list[tuple[str, int, str]] = []
        columnas = [
            ("TIPO_TRANSACCION", "Crear regla desde seleccion"),
            ("ORG_ORIGEN", "Marcar farmacia como CEDI"),
            ("ARTICULO", "Agregar articulos a lista"),
        ]
        for columna, accion in columnas:
            if columna not in dataframe.columns:
                continue
            conteos = dataframe[columna].fillna("").astype(str).str.strip()
            conteos = conteos[conteos != ""].value_counts().head(2)
            for valor, cantidad in conteos.items():
                candidatos.append((f"{columna} = {valor}", int(cantidad), accion))
        candidatos.sort(key=lambda item: item[1], reverse=True)
        return candidatos[:4]

    def _boton_accion(self, texto: str) -> QPushButton:
        boton = QPushButton(texto)
        boton.setObjectName("botonTabla")
        boton.setMinimumHeight(26)
        boton.setFixedWidth(200)
        boton.clicked.connect(lambda: QMessageBox.information(self, "Accion sugerida", texto))
        return boton

    # ------------------------------------------------------------------
    # Paginacion
    # ------------------------------------------------------------------

    def _boton_paginacion(self, texto: str, slot) -> QPushButton:
        boton = QPushButton(texto)
        boton.setObjectName("botonTerciario")
        boton.setFixedSize(34, 32)
        boton.clicked.connect(slot)
        return boton

    def _ir_primera_pagina(self) -> None:
        self._pagina_actual = 1
        self._actualizar_tabla()

    def _ir_anterior(self) -> None:
        self._pagina_actual = max(1, self._pagina_actual - 1)
        self._actualizar_tabla()

    def _ir_siguiente(self) -> None:
        self._pagina_actual = min(self._total_paginas(), self._pagina_actual + 1)
        self._actualizar_tabla()

    def _ir_ultima_pagina(self) -> None:
        self._pagina_actual = self._total_paginas()
        self._actualizar_tabla()

    def _cambiar_filas_pagina(self, *_args: Any) -> None:
        dato = self._combo_filas.currentData()
        self._filas_por_pagina = int(dato) if dato is not None else _FILAS_POR_PAGINA
        self._pagina_actual = 1
        self._actualizar_tabla()

    def _actualizar_paginacion(self) -> None:
        total = len(self._dataframe_filtrado)
        total_paginas = self._total_paginas()
        inicio = 0 if total == 0 else self._inicio_pagina() + 1
        fin = total if self._mostrar_todas_las_filas() else min(self._inicio_pagina() + self._filas_por_pagina, total)
        self._lbl_paginacion.setText(
            "Sin registros para mostrar"
            if total == 0
            else f"Mostrando {inicio} a {fin} de {self._formatear_entero(total)} registros"
        )
        self._lbl_pagina.setText(str(self._pagina_actual))
        self._boton_inicio.setEnabled(self._pagina_actual > 1)
        self._boton_anterior.setEnabled(self._pagina_actual > 1)
        self._boton_siguiente.setEnabled(self._pagina_actual < total_paginas)
        self._boton_final.setEnabled(self._pagina_actual < total_paginas)

    def _total_paginas(self) -> int:
        total = len(self._dataframe_filtrado)
        if total == 0 or self._mostrar_todas_las_filas():
            return 1
        return ((total - 1) // self._filas_por_pagina) + 1

    def _mostrar_todas_las_filas(self) -> bool:
        return self._filas_por_pagina <= 0

    def _inicio_pagina(self) -> int:
        if self._mostrar_todas_las_filas():
            return 0
        return (self._pagina_actual - 1) * self._filas_por_pagina

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _serie_tipologia(self, df: pd.DataFrame) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=str)
        if "TIPOLOGIA_PRELIMINAR" not in df.columns:
            return pd.Series([_SIN_CLASIFICAR] * len(df), index=df.index)
        return df["TIPOLOGIA_PRELIMINAR"].fillna(_SIN_CLASIFICAR).astype(str)

    def _valor_fila(self, fila: pd.Series, columna: str) -> str:
        valor = fila.get(columna, "")
        if pd.isna(valor):
            return ""
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        return str(valor)

    def _porcentaje(self, cantidad: int, total: int) -> str:
        if total <= 0:
            return "0,00%"
        return f"{(cantidad / total) * 100:.2f}%".replace(".", ",")

    def _formatear_entero(self, valor: int) -> str:
        return f"{int(valor):,}".replace(",", ".")

    def _texto_corto(self, texto: Any, limite: int) -> str:
        valor = str(texto)
        return valor if len(valor) <= limite else f"{valor[: max(0, limite - 3)]}..."

    def _limpiar_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._limpiar_layout(child_layout)  # type: ignore[arg-type]

    def _reprocesar_info(self) -> None:
        QMessageBox.information(
            self,
            "Reprocesar clasificacion",
            "Guarde cambios en reglas, farmacias o listas y vuelva a cargar el archivo para reprocesar.",
        )

    def _animar_entrada(self, widget: QWidget) -> None:
        efecto = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(efecto)
        animacion = QPropertyAnimation(efecto, b"opacity", widget)
        animacion.setDuration(220)
        animacion.setStartValue(0.0)
        animacion.setEndValue(1.0)
        animacion.setEasingCurve(QEasingCurve.OutCubic)
        animacion.finished.connect(lambda: widget.setGraphicsEffect(None))
        animacion.start()
        self._animaciones.append(animacion)
