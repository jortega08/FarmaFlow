"""Vista funcional de gestion de clinica y farmacias detectadas."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dto.clinica_dto import ClinicaCrearDTO, ClinicaDTO
from dto.farmacia_dto import FarmaciaActualizarDTO, TipoFarmaciaDTO
from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from interfaz.componentes.tarjeta_metrica import TarjetaMetrica
from modelos.resultado_carga import ResultadoCarga
from persistencia.conexion import sesion_scope
from servicios.excepciones import ErrorDominio
from servicios.servicio_clinicas import ServicioClinicas
from servicios.servicio_deteccion_farmacias import ServicioDeteccionFarmacias
from servicios.servicio_farmacias import ServicioFarmacias
from servicios.servicio_tipos_farmacia import ServicioTiposFarmacia


_FILAS_POR_PAGINA = 8
_TIPO_NO_CLASIFICABLE = "NO_CLASIFICABLE"


@dataclass
class _FilaFarmacia:
    """Estado editable de una farmacia detectada en la UI."""

    codigo: str
    nombre: str
    movimientos: int
    estado: str
    tipo_codigo: str
    farmacia_id: int | None
    puede_prestar: bool
    es_interna: bool
    es_externa: bool
    pertenece_clinica: bool


class VistaClinicaFarmacias(QWidget):
    """Pantalla de seleccion de clinica y confirmacion de farmacias."""

    farmacias_actualizadas = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._resultado_carga: ResultadoCarga | None = None
        self._clinicas: list[ClinicaDTO] = []
        self._tipos: list[TipoFarmaciaDTO] = []
        self._tipos_por_codigo: dict[str, TipoFarmaciaDTO] = {}
        self._filas: list[_FilaFarmacia] = []
        self._filas_filtradas: list[int] = []
        self._pagina_actual = 1
        self._filas_por_pagina = _FILAS_POR_PAGINA
        self._indice_seleccionado: int | None = None
        self._bloqueando_eventos = False
        self._botones_filtro_farmacias: dict[str, QPushButton] = {}
        self._animaciones: list[QPropertyAnimation] = []

        self._construir_ui()
        self._cargar_catalogos()
        self._actualizar_estado_vacio()

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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorVista")
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)

        layout.addWidget(self._crear_titulo())
        layout.addWidget(self._crear_selector_clinica())
        layout.addLayout(self._crear_metricas())
        layout.addLayout(self._crear_contenido_principal())
        layout.addWidget(self._crear_barra_inferior())
        layout.addStretch(1)

        scroll.setWidget(contenedor)
        layout_raiz.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        icono = QLabel("CL")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(50, 50)
        icono.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(4)
        titulo = QLabel("2. Clinica y farmacias")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Selecciona la clinica y valida las farmacias detectadas en el archivo."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)

        layout.addWidget(icono)
        layout.addLayout(textos, 1)
        return card

    def _crear_selector_clinica(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        etiqueta = QLabel("Clinica seleccionada")
        etiqueta.setObjectName("tituloBloque")

        fila = QHBoxLayout()
        fila.setSpacing(16)
        self._combo_clinica = ComboScrollSafe()
        self._combo_clinica.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._combo_clinica.currentIndexChanged.connect(self._al_cambiar_clinica)

        self._boton_crear_clinica = QPushButton("Crear nueva clinica")
        self._boton_crear_clinica.setObjectName("botonSecundario")
        self._boton_crear_clinica.setMinimumHeight(42)
        self._boton_crear_clinica.setMinimumWidth(200)
        self._boton_crear_clinica.clicked.connect(self._crear_nueva_clinica)

        fila.addWidget(self._combo_clinica, 1)
        fila.addWidget(self._boton_crear_clinica)

        layout.addWidget(etiqueta)
        layout.addLayout(fila)
        return card

    def _crear_metricas(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(16)

        self._tarjeta_detectadas = TarjetaMetrica(
            "Farmacias detectadas",
            "0",
            icono="FAR",
            tipo="info",
            descripcion="Total en el archivo",
        )
        self._tarjeta_nuevas = TarjetaMetrica(
            "Nuevas",
            "0",
            icono="NEW",
            tipo="exito",
            descripcion="No existen en el catalogo",
        )
        self._tarjeta_internas = TarjetaMetrica(
            "Internas",
            "0",
            icono="INT",
            tipo="neutro",
            descripcion="Pertenecen a la clinica",
        )
        self._tarjeta_externas = TarjetaMetrica(
            "Externas / especiales",
            "0",
            icono="EXT",
            tipo="advertencia",
            descripcion="No pertenecen o son especiales",
        )

        for tarjeta in (
            self._tarjeta_detectadas,
            self._tarjeta_nuevas,
            self._tarjeta_internas,
            self._tarjeta_externas,
        ):
            fila.addWidget(tarjeta)
        return fila

    def _crear_contenido_principal(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(self._crear_tabla_farmacias(), 3)
        layout.addWidget(self._crear_panel_detalle(), 1)
        return layout

    def _crear_tabla_farmacias(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        cabecera = QHBoxLayout()
        titulo = QLabel("Farmacias detectadas en el archivo")
        titulo.setObjectName("tituloSubpanel")
        cabecera.addWidget(titulo)
        cabecera.addStretch(1)

        herramientas = QHBoxLayout()
        herramientas.setSpacing(8)
        self._buscador = QLineEdit()
        self._buscador.setPlaceholderText("Buscar codigo o nombre")
        self._buscador.setMinimumWidth(180)
        self._buscador.textChanged.connect(self._aplicar_filtro)
        herramientas.addWidget(self._buscador)
        herramientas.addStretch(1)

        filtros = (
            ("Internas", "INTERNAS", "Muestra farmacias internas detectadas.", 104),
            ("Externas", "EXTERNAS", "Muestra farmacias externas detectadas.", 108),
            ("CEDI", "CEDI", "Muestra farmacias clasificadas como CEDI.", 86),
            ("No prestan", "NO_PRESTAN", "Muestra farmacias que no pueden prestar.", 112),
        )
        for texto, clave, tooltip, ancho in filtros:
            boton = QPushButton(texto)
            boton.setObjectName("botonFiltroTabla")
            boton.setCheckable(True)
            boton.setToolTip(tooltip)
            boton.setMinimumHeight(38)
            boton.setFixedWidth(ancho)
            boton.clicked.connect(self._aplicar_filtro)
            self._botones_filtro_farmacias[clave] = boton
            herramientas.addWidget(boton)

        self._tabla = QTableWidget(0, 8)
        self._tabla.setHorizontalHeaderLabels(
            [
                "ESTADO",
                "CODIGO",
                "NOMBRE",
                "TIPO",
                "CLINICA",
                "PRESTA",
                "MOV.",
                "ACCION",
            ]
        )
        encabezado = self._tabla.horizontalHeader()
        encabezado.setMinimumSectionSize(44)
        encabezado.setStretchLastSection(False)
        for columna, ancho in {
            0: 96,
            1: 66,
            3: 112,
            4: 62,
            5: 62,
            6: 48,
            7: 86,
        }.items():
            encabezado.setSectionResizeMode(columna, QHeaderView.Fixed)
            self._tabla.setColumnWidth(columna, ancho)
        encabezado.setSectionResizeMode(2, QHeaderView.Stretch)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.verticalHeader().setDefaultSectionSize(42)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._tabla.setMinimumHeight(330)
        self._tabla.setWordWrap(False)
        self._tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._tabla.itemSelectionChanged.connect(self._al_seleccionar_fila)

        pie = QHBoxLayout()
        self._lbl_paginacion = QLabel("Sin farmacias detectadas")
        self._lbl_paginacion.setObjectName("textoSecundario")
        pie.addWidget(self._lbl_paginacion)
        pie.addStretch(1)

        self._boton_inicio = self._boton_paginacion("<<", self._ir_primera_pagina)
        self._boton_anterior = self._boton_paginacion("<", self._ir_pagina_anterior)
        self._lbl_pagina = QLabel("1")
        self._lbl_pagina.setObjectName("insigniaInfo")
        self._lbl_pagina.setAlignment(Qt.AlignCenter)
        self._lbl_pagina.setFixedWidth(36)
        self._boton_siguiente = self._boton_paginacion(">", self._ir_pagina_siguiente)
        self._boton_final = self._boton_paginacion(">>", self._ir_ultima_pagina)

        self._combo_filas_pagina = ComboScrollSafe()
        for valor in ("8", "12", "20"):
            self._combo_filas_pagina.addItem(valor, int(valor))
        self._combo_filas_pagina.addItem("Todas", 0)
        self._combo_filas_pagina.currentIndexChanged.connect(self._cambiar_filas_pagina)

        for widget in (
            self._boton_inicio,
            self._boton_anterior,
            self._lbl_pagina,
            self._boton_siguiente,
            self._boton_final,
        ):
            pie.addWidget(widget)
        pie.addSpacing(12)
        pie.addWidget(QLabel("Filas por pagina"))
        pie.addWidget(self._combo_filas_pagina)

        layout.addLayout(cabecera)
        layout.addLayout(herramientas)
        layout.addWidget(self._tabla)
        layout.addLayout(pie)
        return card

    def _crear_panel_detalle(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        card.setMinimumWidth(280)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        titulo = QLabel("Detalle de la farmacia seleccionada")
        titulo.setObjectName("tituloSubpanel")
        layout.addWidget(titulo)

        self._entrada_codigo = self._crear_entrada_detalle(layout, "Codigo")
        self._entrada_nombre = self._crear_entrada_detalle(layout, "Nombre")

        self._combo_tipo = self._crear_combo_detalle(layout, "Tipo")
        self._combo_clinica_detalle = self._crear_combo_detalle(layout, "Clinica asociada")
        self._combo_puede_prestar = self._crear_combo_detalle(layout, "Puede prestar")
        self._combo_puede_prestar.addItem("Si", True)
        self._combo_puede_prestar.addItem("No", False)

        self._combo_relacion = self._crear_combo_detalle(layout, "Interna / Externa")
        self._combo_relacion.addItem("Interna", "INTERNA")
        self._combo_relacion.addItem("Externa", "EXTERNA")
        self._combo_relacion.addItem("Especial", "ESPECIAL")

        self._entrada_alias = self._crear_entrada_detalle(layout, "Alias opcional")

        self._boton_guardar = QPushButton("Guardar farmacia")
        self._boton_guardar.setObjectName("botonPrincipal")
        self._boton_guardar.setMinimumHeight(46)
        self._boton_guardar.clicked.connect(self._guardar_farmacia_seleccionada)
        layout.addSpacing(8)
        layout.addWidget(self._boton_guardar)
        layout.addStretch(1)

        self._habilitar_detalle(False)
        return card

    def _crear_barra_inferior(self) -> QFrame:
        barra = QFrame()
        barra.setObjectName("barraInferior")
        barra.setMinimumHeight(70)
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        self._icono_estado = QLabel("i")
        self._icono_estado.setObjectName("iconoEstadoInfo")
        self._icono_estado.setFixedSize(30, 30)
        self._icono_estado.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(2)
        self._lbl_estado = QLabel("Carga un archivo para detectar farmacias.")
        self._lbl_estado.setObjectName("mensajeEstadoNeutro")
        self._lbl_estado_detalle = QLabel("La pantalla se actualiza despues de validar el Excel.")
        self._lbl_estado_detalle.setObjectName("textoSecundario")
        textos.addWidget(self._lbl_estado)
        textos.addWidget(self._lbl_estado_detalle)

        self._boton_resumen = QPushButton("Ver resumen")
        self._boton_resumen.setObjectName("botonSecundario")
        self._boton_resumen.setMinimumHeight(40)
        self._boton_resumen.clicked.connect(self._mostrar_resumen)

        layout.addWidget(self._icono_estado)
        layout.addLayout(textos, 1)
        layout.addWidget(self._boton_resumen)
        return barra

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def establecer_resultado_carga(self, resultado: ResultadoCarga) -> None:
        """Recibe el archivo validado y detecta farmacias del dataframe."""
        self._resultado_carga = resultado
        self._detectar_farmacias_desde_resultado()

    def limpiar_resultado(self) -> None:
        """Limpia la informacion detectada cuando se reinicia la carga."""
        self._resultado_carga = None
        self._filas = []
        self._filas_filtradas = []
        self._indice_seleccionado = None
        self._pagina_actual = 1
        self._tabla.setRowCount(0)
        self._buscador.clear()
        self._actualizar_metricas()
        self._actualizar_detalle(None)
        self._actualizar_estado_vacio()

    def recargar(self) -> None:
        """Recarga catalogos y vuelve a detectar farmacias si hay un archivo vigente."""
        self._cargar_catalogos()
        if self._resultado_carga is not None:
            self._detectar_farmacias_desde_resultado()
        else:
            self._actualizar_estado_vacio()

    # ------------------------------------------------------------------
    # Catalogos y deteccion
    # ------------------------------------------------------------------

    def _cargar_catalogos(self) -> None:
        try:
            with sesion_scope() as sesion:
                self._clinicas = ServicioClinicas(sesion).listar_clinicas(activa=True)
                self._tipos = ServicioTiposFarmacia(sesion).listar_tipos()
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar catalogos: %s", error)
            self._clinicas = []
            self._tipos = []

        self._tipos_por_codigo = {tipo.codigo: tipo for tipo in self._tipos}
        self._llenar_combo_clinicas()
        self._llenar_combo_tipos()

    def _llenar_combo_clinicas(self) -> None:
        self._bloqueando_eventos = True
        clinica_actual = self._clinica_id_actual()
        for combo in (self._combo_clinica, self._combo_clinica_detalle):
            combo.clear()
            combo.addItem("Sin clinica seleccionada", None)
            for clinica in self._clinicas:
                combo.addItem(clinica.nombre, clinica.id)
        self._restaurar_combo_por_dato(self._combo_clinica, clinica_actual)
        self._restaurar_combo_por_dato(self._combo_clinica_detalle, clinica_actual)
        self._bloqueando_eventos = False

    def _llenar_combo_tipos(self) -> None:
        self._combo_tipo.clear()
        for tipo in self._tipos:
            self._combo_tipo.addItem(tipo.nombre, tipo.codigo)

    def _detectar_farmacias_desde_resultado(self) -> None:
        resultado = self._resultado_carga
        if resultado is None or resultado.dataframe is None or resultado.dataframe.empty:
            self._actualizar_estado_vacio()
            return

        clinica_id = self._clinica_id_actual()
        try:
            with sesion_scope() as sesion:
                servicio = ServicioDeteccionFarmacias(sesion)
                deteccion = servicio.detectar_farmacias(
                    resultado.dataframe,
                    clinica_id=clinica_id,
                    ejecucion_id=None,
                )
                asociadas = set()
                if clinica_id is not None:
                    asociadas = {
                        farmacia.id
                        for farmacia in ServicioClinicas(sesion).listar_farmacias_de_clinica(clinica_id)
                    }
        except ErrorDominio as error:
            self._mostrar_error(str(error))
            return
        except Exception as error:  # noqa: BLE001
            self._logger.exception("Fallo detectando farmacias: %s", error)
            self._mostrar_error("No fue posible detectar farmacias del archivo.")
            return

        filas: list[_FilaFarmacia] = []
        for detectada in deteccion.farmacias_detectadas:
            tipo_codigo = detectada.tipo_sugerido or _TIPO_NO_CLASIFICABLE
            es_interna = (
                bool(detectada.es_interna)
                if detectada.es_interna is not None
                else tipo_codigo == "INTERNA"
            )
            es_externa = (
                bool(detectada.es_externa)
                if detectada.es_externa is not None
                else tipo_codigo == "EXTERNA"
            )
            puede_prestar = (
                bool(detectada.puede_prestar)
                if detectada.puede_prestar is not None
                else True
            )
            pertenece = (
                detectada.farmacia_id in asociadas
                if detectada.farmacia_id is not None
                else clinica_id is not None and tipo_codigo not in {"EXTERNA", _TIPO_NO_CLASIFICABLE}
            )
            filas.append(
                _FilaFarmacia(
                    codigo=detectada.codigo_detectado or "",
                    nombre=detectada.nombre_detectado,
                    movimientos=detectada.cantidad_registros,
                    estado=detectada.estado_deteccion,
                    tipo_codigo=tipo_codigo,
                    farmacia_id=detectada.farmacia_id,
                    puede_prestar=puede_prestar,
                    es_interna=es_interna,
                    es_externa=es_externa,
                    pertenece_clinica=pertenece,
                )
            )

        self._filas = filas
        self._pagina_actual = 1
        self._aplicar_filtro()
        self._actualizar_metricas()
        self._actualizar_estado_resumen()
        self._animar_entrada(self._tabla)

    # ------------------------------------------------------------------
    # Tabla, filtros y paginacion
    # ------------------------------------------------------------------

    def _aplicar_filtro(self) -> None:
        texto = self._buscador.text().strip().lower() if hasattr(self, "_buscador") else ""
        self._filas_filtradas = [
            indice
            for indice, fila in enumerate(self._filas)
            if self._fila_cumple_filtro(fila, texto)
        ]
        self._pagina_actual = min(self._pagina_actual, self._total_paginas())
        self._pagina_actual = max(1, self._pagina_actual)
        self._actualizar_tabla()

    def _actualizar_tabla(self) -> None:
        self._tabla.blockSignals(True)
        self._tabla.setRowCount(0)

        indices_pagina = self._indices_pagina_actual()

        self._tabla.setRowCount(len(indices_pagina))
        for fila_tabla, indice_fila in enumerate(indices_pagina):
            fila = self._filas[indice_fila]
            self._set_item(fila_tabla, 0, self._estado_legible(fila.estado), indice_fila)
            self._tabla.setCellWidget(
                fila_tabla,
                0,
                self._contenedor_celda(self._badge(self._estado_legible(fila.estado), fila.estado)),
            )
            self._set_item(fila_tabla, 1, fila.codigo or "-", indice_fila)
            self._set_item(fila_tabla, 2, fila.nombre, indice_fila)
            self._set_item(fila_tabla, 3, self._nombre_tipo_corto(fila.tipo_codigo), indice_fila)
            self._tabla.setCellWidget(
                fila_tabla,
                3,
                self._contenedor_celda(self._badge(self._nombre_tipo_corto(fila.tipo_codigo), fila.tipo_codigo)),
            )
            self._set_item(fila_tabla, 4, self._si_no(fila.pertenece_clinica), indice_fila)
            self._set_item(fila_tabla, 5, self._si_no(fila.puede_prestar), indice_fila)
            self._set_item(fila_tabla, 6, str(fila.movimientos), indice_fila)
            self._tabla.setCellWidget(
                fila_tabla,
                7,
                self._contenedor_celda(self._crear_acciones_fila(indice_fila), margen=3),
            )
            self._tabla.setRowHeight(fila_tabla, 42)
            if self._indice_seleccionado == indice_fila:
                self._tabla.selectRow(fila_tabla)

        self._tabla.blockSignals(False)
        self._actualizar_paginacion()

    def _set_item(self, fila: int, columna: int, texto: str, indice_fila: int) -> None:
        item = QTableWidgetItem(texto)
        item.setToolTip(texto)
        item.setData(Qt.UserRole, indice_fila)
        item.setTextAlignment(Qt.AlignCenter if columna in {0, 1, 4, 5, 6} else Qt.AlignVCenter)
        self._tabla.setItem(fila, columna, item)

    def _crear_acciones_fila(self, indice_fila: int) -> QWidget:
        boton_guardar = QPushButton("Guardar")
        boton_guardar.setObjectName("botonTabla")
        boton_guardar.setFixedHeight(26)
        boton_guardar.setFixedWidth(72)
        boton_guardar.clicked.connect(lambda: self._guardar_indice(indice_fila))
        return boton_guardar

    def _badge(self, texto: str, estado: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setObjectName(self._badge_objeto(estado))
        etiqueta.setMinimumHeight(22)
        etiqueta.setMaximumHeight(24)
        etiqueta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return etiqueta

    def _contenedor_celda(self, widget: QWidget, margen: int = 5) -> QWidget:
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(margen, 3, margen, 3)
        layout.setSpacing(0)
        layout.addWidget(widget)
        return contenedor

    def _badge_objeto(self, estado: str) -> str:
        if estado in {"EXISTENTE", "INTERNA", "CEDI"}:
            return "insigniaInfo"
        if estado in {"NUEVA", "ALMACEN"}:
            return "insigniaCorrecta"
        if estado in {"EXTERNA", "DEVOLUCIONES", _TIPO_NO_CLASIFICABLE, "AMBIGUA"}:
            return "insigniaAdvertencia"
        if estado == "IGNORADA":
            return "insigniaError"
        return "insigniaNeutra"

    def _boton_paginacion(self, texto: str, slot) -> QPushButton:
        boton = QPushButton(texto)
        boton.setObjectName("botonTerciario")
        boton.setFixedSize(34, 32)
        boton.clicked.connect(slot)
        return boton

    def _actualizar_paginacion(self) -> None:
        total = len(self._filas_filtradas)
        total_paginas = self._total_paginas()
        inicio = 0 if total == 0 else self._inicio_pagina() + 1
        fin = total if self._mostrar_todas_las_filas() else min(self._inicio_pagina() + self._filas_por_pagina, total)
        self._lbl_paginacion.setText(
            "Sin farmacias detectadas"
            if total == 0
            else f"Mostrando {inicio} a {fin} de {total} farmacias"
        )
        self._lbl_pagina.setText(str(self._pagina_actual))
        self._boton_inicio.setEnabled(self._pagina_actual > 1)
        self._boton_anterior.setEnabled(self._pagina_actual > 1)
        self._boton_siguiente.setEnabled(self._pagina_actual < total_paginas)
        self._boton_final.setEnabled(self._pagina_actual < total_paginas)

    def _total_paginas(self) -> int:
        if not self._filas_filtradas or self._mostrar_todas_las_filas():
            return 1
        return ((len(self._filas_filtradas) - 1) // self._filas_por_pagina) + 1

    def _ir_primera_pagina(self) -> None:
        self._pagina_actual = 1
        self._actualizar_tabla()

    def _ir_pagina_anterior(self) -> None:
        self._pagina_actual = max(1, self._pagina_actual - 1)
        self._actualizar_tabla()

    def _ir_pagina_siguiente(self) -> None:
        self._pagina_actual = min(self._total_paginas(), self._pagina_actual + 1)
        self._actualizar_tabla()

    def _ir_ultima_pagina(self) -> None:
        self._pagina_actual = self._total_paginas()
        self._actualizar_tabla()

    def _cambiar_filas_pagina(self) -> None:
        dato = self._combo_filas_pagina.currentData()
        self._filas_por_pagina = int(dato) if dato is not None else _FILAS_POR_PAGINA
        self._pagina_actual = 1
        self._actualizar_tabla()

    def _fila_cumple_filtro(self, fila: _FilaFarmacia, texto: str) -> bool:
        if not self._fila_cumple_filtros_rapidos(fila):
            return False
        if not texto:
            return True
        valores = (
            fila.codigo,
            fila.nombre,
            fila.tipo_codigo,
            self._nombre_tipo(fila.tipo_codigo),
            self._nombre_tipo_corto(fila.tipo_codigo),
            fila.estado,
            self._estado_legible(fila.estado),
            "clinica" if fila.pertenece_clinica else "sin clinica",
            "presta" if fila.puede_prestar else "no presta",
            "interna" if fila.es_interna else "",
            "externa" if fila.es_externa else "",
        )
        return any(texto in str(valor).lower() for valor in valores)

    def _fila_cumple_filtros_rapidos(self, fila: _FilaFarmacia) -> bool:
        botones = self._botones_filtro_farmacias
        if not botones:
            return True

        filtros_tipo = [
            self._es_boton_filtro_activo("INTERNAS") and (fila.es_interna or fila.tipo_codigo == "INTERNA"),
            self._es_boton_filtro_activo("EXTERNAS") and (fila.es_externa or fila.tipo_codigo == "EXTERNA"),
            self._es_boton_filtro_activo("CEDI") and fila.tipo_codigo == "CEDI",
        ]
        hay_filtro_tipo = any(
            self._es_boton_filtro_activo(clave)
            for clave in ("INTERNAS", "EXTERNAS", "CEDI")
        )
        if hay_filtro_tipo and not any(filtros_tipo):
            return False

        if self._es_boton_filtro_activo("NO_PRESTAN") and fila.puede_prestar:
            return False

        return True

    def _es_boton_filtro_activo(self, clave: str) -> bool:
        boton = self._botones_filtro_farmacias.get(clave)
        return bool(boton and boton.isChecked())

    def _mostrar_todas_las_filas(self) -> bool:
        return self._filas_por_pagina <= 0

    def _inicio_pagina(self) -> int:
        if self._mostrar_todas_las_filas():
            return 0
        return (self._pagina_actual - 1) * self._filas_por_pagina

    def _indices_pagina_actual(self) -> list[int]:
        if self._mostrar_todas_las_filas():
            return list(self._filas_filtradas)
        inicio = self._inicio_pagina()
        fin = inicio + self._filas_por_pagina
        return self._filas_filtradas[inicio:fin]

    # ------------------------------------------------------------------
    # Detalle y acciones
    # ------------------------------------------------------------------

    def _crear_entrada_detalle(self, layout: QVBoxLayout, etiqueta: str) -> QLineEdit:
        lbl = QLabel(etiqueta)
        lbl.setObjectName("tituloBloque")
        entrada = QLineEdit()
        layout.addWidget(lbl)
        layout.addWidget(entrada)
        return entrada

    def _crear_combo_detalle(self, layout: QVBoxLayout, etiqueta: str) -> QComboBox:
        lbl = QLabel(etiqueta)
        lbl.setObjectName("tituloBloque")
        combo = ComboScrollSafe()
        layout.addWidget(lbl)
        layout.addWidget(combo)
        return combo

    def _al_seleccionar_fila(self) -> None:
        filas = self._tabla.selectionModel().selectedRows()
        if not filas:
            self._actualizar_detalle(None)
            return
        item = self._tabla.item(filas[0].row(), 1)
        indice = item.data(Qt.UserRole) if item is not None else None
        self._actualizar_detalle(indice)

    def _seleccionar_indice(self, indice_fila: int) -> None:
        self._indice_seleccionado = indice_fila
        for fila_tabla in range(self._tabla.rowCount()):
            item = self._tabla.item(fila_tabla, 1)
            if item is not None and item.data(Qt.UserRole) == indice_fila:
                self._tabla.selectRow(fila_tabla)
                break
        self._actualizar_detalle(indice_fila)

    def _actualizar_detalle(self, indice_fila: int | None) -> None:
        self._bloqueando_eventos = True
        self._indice_seleccionado = indice_fila
        fila = self._filas[indice_fila] if indice_fila is not None else None

        self._habilitar_detalle(fila is not None)
        if fila is None:
            self._entrada_codigo.clear()
            self._entrada_nombre.clear()
            self._entrada_alias.clear()
            self._bloqueando_eventos = False
            return

        self._entrada_codigo.setText(fila.codigo)
        self._entrada_nombre.setText(fila.nombre)
        self._entrada_alias.clear()
        self._restaurar_combo_por_dato(self._combo_tipo, fila.tipo_codigo)
        self._restaurar_combo_por_dato(
            self._combo_clinica_detalle,
            self._clinica_id_actual() if fila.pertenece_clinica else None,
        )
        self._restaurar_combo_por_dato(self._combo_puede_prestar, fila.puede_prestar)
        relacion = "EXTERNA" if fila.es_externa else "INTERNA" if fila.es_interna else "ESPECIAL"
        self._restaurar_combo_por_dato(self._combo_relacion, relacion)
        self._bloqueando_eventos = False

    def _habilitar_detalle(self, habilitado: bool) -> None:
        for widget in (
            self._entrada_codigo,
            self._entrada_nombre,
            self._combo_tipo,
            self._combo_clinica_detalle,
            self._combo_puede_prestar,
            self._combo_relacion,
            self._entrada_alias,
            self._boton_guardar,
        ):
            widget.setEnabled(habilitado)

    def _indices_seleccionados(self) -> list[int]:
        indices: list[int] = []
        for modelo in self._tabla.selectionModel().selectedRows():
            item = self._tabla.item(modelo.row(), 1)
            if item is not None:
                indices.append(int(item.data(Qt.UserRole)))
        return indices

    def _marcar_seleccion_interna(self) -> None:
        self._aplicar_cambio_masivo(tipo_codigo="INTERNA", puede_prestar=True, relacion="INTERNA")

    def _marcar_seleccion_externa(self) -> None:
        self._aplicar_cambio_masivo(tipo_codigo="EXTERNA", puede_prestar=True, relacion="EXTERNA")

    def _marcar_seleccion_cedi(self) -> None:
        self._aplicar_cambio_masivo(tipo_codigo="CEDI", puede_prestar=True, relacion="ESPECIAL")

    def _marcar_no_pueden_prestar(self) -> None:
        self._aplicar_cambio_masivo(puede_prestar=False)

    def _aplicar_cambio_masivo(
        self,
        *,
        tipo_codigo: str | None = None,
        puede_prestar: bool | None = None,
        relacion: str | None = None,
    ) -> None:
        indices = self._indices_seleccionados()
        if not indices:
            self._mensaje_estado("Selecciona una o mas farmacias para aplicar cambios.", "advertencia")
            return

        clinica_id = self._clinica_id_actual()
        for indice in indices:
            fila = self._filas[indice]
            if tipo_codigo is not None:
                fila.tipo_codigo = tipo_codigo
                fila.pertenece_clinica = clinica_id is not None and tipo_codigo != "EXTERNA"
            if puede_prestar is not None:
                fila.puede_prestar = puede_prestar
            if relacion == "INTERNA":
                fila.es_interna = True
                fila.es_externa = False
            elif relacion == "EXTERNA":
                fila.es_interna = False
                fila.es_externa = True
                fila.pertenece_clinica = False
            elif relacion == "ESPECIAL":
                fila.es_interna = False
                fila.es_externa = False

        self._actualizar_tabla()
        self._actualizar_metricas()
        self._actualizar_detalle(indices[0])
        self._mensaje_estado("Cambios aplicados en la tabla. Guarda las farmacias para persistirlos.", "info")

    def _guardar_indice(self, indice_fila: int) -> None:
        self._actualizar_detalle(indice_fila)
        self._guardar_farmacia_seleccionada()

    def _guardar_farmacia_seleccionada(self) -> None:
        if self._indice_seleccionado is None:
            self._mensaje_estado("Selecciona una farmacia antes de guardar.", "advertencia")
            return

        fila = self._filas[self._indice_seleccionado]
        codigo = self._entrada_codigo.text().strip() or fila.codigo
        nombre = self._entrada_nombre.text().strip()
        tipo_codigo = str(self._combo_tipo.currentData() or fila.tipo_codigo or _TIPO_NO_CLASIFICABLE)
        clinica_id = self._combo_clinica_detalle.currentData()
        puede_prestar = bool(self._combo_puede_prestar.currentData())
        relacion = str(self._combo_relacion.currentData() or "ESPECIAL")
        es_interna = relacion == "INTERNA"
        es_externa = relacion == "EXTERNA"

        if not codigo or not nombre:
            self._mensaje_estado("Codigo y nombre son obligatorios.", "advertencia")
            return

        tipo = self._tipos_por_codigo.get(tipo_codigo)
        if tipo is None:
            self._mensaje_estado("Selecciona un tipo de farmacia valido.", "advertencia")
            return

        try:
            with sesion_scope() as sesion:
                servicio = ServicioFarmacias(sesion)
                if fila.farmacia_id is None:
                    farmacia = servicio.crear_desde_deteccion(
                        codigo_detectado=codigo,
                        nombre_detectado=nombre,
                        tipo_codigo=tipo_codigo,
                        puede_prestar=puede_prestar,
                        es_interna=es_interna,
                        es_externa=es_externa,
                    )
                else:
                    farmacia = servicio.actualizar_farmacia(
                        fila.farmacia_id,
                        FarmaciaActualizarDTO(
                            codigo=codigo,
                            nombre_original=nombre,
                            tipo_farmacia_id=tipo.id,
                            puede_prestar=puede_prestar,
                            es_interna=es_interna,
                            es_externa=es_externa,
                        ),
                    )

                if clinica_id is not None:
                    farmacia = servicio.asociar_a_clinica(farmacia.id, int(clinica_id), relacion=relacion)
                elif self._clinica_id_actual() is not None:
                    servicio.desasociar_de_clinica(farmacia.id, int(self._clinica_id_actual()))
        except ErrorDominio as error:
            self._mensaje_estado(str(error), "error")
            QMessageBox.warning(self, "No fue posible guardar", str(error))
            return
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible guardar farmacia: %s", error)
            self._mensaje_estado("No fue posible guardar la farmacia.", "error")
            QMessageBox.critical(
                self,
                "Error al guardar",
                "No fue posible guardar la farmacia. Revise los datos e intente nuevamente.",
            )
            return

        fila.codigo = farmacia.codigo
        fila.nombre = farmacia.nombre_original
        fila.farmacia_id = farmacia.id
        fila.estado = "EXISTENTE"
        fila.tipo_codigo = tipo_codigo
        fila.puede_prestar = farmacia.puede_prestar
        fila.es_interna = farmacia.es_interna
        fila.es_externa = farmacia.es_externa
        fila.pertenece_clinica = clinica_id is not None

        self._actualizar_tabla()
        self._actualizar_metricas()
        self._actualizar_detalle(self._indice_seleccionado)
        self._actualizar_estado_resumen()
        self._mensaje_estado("Farmacia guardada correctamente.", "correcto")
        self.farmacias_actualizadas.emit()
        QMessageBox.information(
            self,
            "Farmacia guardada",
            f"La farmacia \"{farmacia.codigo}\" se guardo correctamente.",
        )

    # ------------------------------------------------------------------
    # Clinicas
    # ------------------------------------------------------------------

    def _al_cambiar_clinica(self) -> None:
        if self._bloqueando_eventos:
            return
        self._restaurar_combo_por_dato(self._combo_clinica_detalle, self._clinica_id_actual())
        if self._resultado_carga is not None:
            self._detectar_farmacias_desde_resultado()

    def _crear_nueva_clinica(self) -> None:
        nombre, aceptado = QInputDialog.getText(self, "Nueva clinica", "Nombre de la clinica:")
        nombre = nombre.strip()
        if not aceptado or not nombre:
            return

        try:
            with sesion_scope() as sesion:
                clinica = ServicioClinicas(sesion).crear_clinica(ClinicaCrearDTO(nombre=nombre))
        except ErrorDominio as error:
            self._mensaje_estado(str(error), "error")
            return
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible crear clinica: %s", error)
            self._mensaje_estado("No fue posible crear la clinica.", "error")
            return

        self._cargar_catalogos()
        self._restaurar_combo_por_dato(self._combo_clinica, clinica.id)
        self._restaurar_combo_por_dato(self._combo_clinica_detalle, clinica.id)
        self._mensaje_estado("Clinica creada correctamente.", "correcto")
        if self._resultado_carga is not None:
            self._detectar_farmacias_desde_resultado()

    def _clinica_id_actual(self) -> int | None:
        if not hasattr(self, "_combo_clinica"):
            return None
        dato = self._combo_clinica.currentData()
        return int(dato) if dato is not None else None

    # ------------------------------------------------------------------
    # Estado visual
    # ------------------------------------------------------------------

    def _actualizar_metricas(self) -> None:
        total = len(self._filas)
        nuevas = sum(1 for fila in self._filas if fila.estado == "NUEVA")
        internas = sum(1 for fila in self._filas if fila.es_interna or fila.tipo_codigo == "INTERNA")
        externas = sum(
            1
            for fila in self._filas
            if fila.es_externa
            or fila.tipo_codigo in {"EXTERNA", "CEDI", "DEVOLUCIONES", "ALMACEN", _TIPO_NO_CLASIFICABLE}
            or not fila.pertenece_clinica
        )

        self._tarjeta_detectadas.actualizar(str(total))
        self._tarjeta_nuevas.actualizar(str(nuevas))
        self._tarjeta_internas.actualizar(str(internas), estilo_valor="valorMetricaCorrecto")
        self._tarjeta_externas.actualizar(str(externas), estilo_valor="valorMetricaAdvertencia")

    def _actualizar_estado_vacio(self) -> None:
        self._actualizar_metricas()
        self._mensaje_estado("Carga un archivo para detectar farmacias.", "neutro")
        self._lbl_estado_detalle.setText("La pantalla se actualiza despues de validar el Excel.")

    def _actualizar_estado_resumen(self) -> None:
        nuevas = sum(1 for fila in self._filas if fila.estado == "NUEVA")
        if nuevas:
            self._mensaje_estado(f"{nuevas} farmacias nuevas fueron detectadas.", "correcto")
            self._lbl_estado_detalle.setText("Revisa los detalles y clasificalas para continuar.")
            return
        if self._filas:
            self._mensaje_estado("Farmacias detectadas listas para revisar.", "correcto")
            self._lbl_estado_detalle.setText("Puedes ajustar tipos, relacion con la clinica y capacidad de prestar.")

    def _mensaje_estado(self, mensaje: str, tipo: str) -> None:
        nombres_icono = {
            "correcto": "iconoEstadoCorrecto",
            "error": "iconoEstadoError",
            "advertencia": "iconoEstadoAdvertencia",
            "info": "iconoEstadoInfo",
            "neutro": "iconoEstadoNeutro",
        }
        iconos = {"correcto": "OK", "error": "X", "advertencia": "!", "info": "i", "neutro": "-"}
        nombres_texto = {
            "correcto": "mensajeEstado",
            "error": "mensajeEstadoError",
            "advertencia": "mensajeEstadoAdvertencia",
            "info": "mensajeCargaInfo",
            "neutro": "mensajeEstadoNeutro",
        }
        self._icono_estado.setText(iconos.get(tipo, "i"))
        self._icono_estado.setObjectName(nombres_icono.get(tipo, "iconoEstadoInfo"))
        self._lbl_estado.setText(mensaje)
        self._lbl_estado.setObjectName(nombres_texto.get(tipo, "mensajeEstadoNeutro"))
        self._aplicar_estilo(self._icono_estado)
        self._aplicar_estilo(self._lbl_estado)

    def _mostrar_error(self, mensaje: str) -> None:
        self._filas = []
        self._filas_filtradas = []
        self._actualizar_tabla()
        self._actualizar_metricas()
        self._mensaje_estado(mensaje, "error")

    def _mostrar_resumen(self) -> None:
        total = len(self._filas)
        nuevas = sum(1 for fila in self._filas if fila.estado == "NUEVA")
        existentes = sum(1 for fila in self._filas if fila.estado == "EXISTENTE")
        no_prestan = sum(1 for fila in self._filas if not fila.puede_prestar)
        QMessageBox.information(
            self,
            "Resumen de farmacias",
            (
                f"Farmacias detectadas: {total}\n"
                f"Nuevas: {nuevas}\n"
                f"Existentes: {existentes}\n"
                f"No pueden prestar: {no_prestan}"
            ),
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

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _restaurar_combo_por_dato(self, combo: QComboBox, dato: Any) -> None:
        for indice in range(combo.count()):
            if combo.itemData(indice) == dato:
                combo.setCurrentIndex(indice)
                return
        if combo.count():
            combo.setCurrentIndex(0)

    def _nombre_tipo(self, codigo: str) -> str:
        tipo = self._tipos_por_codigo.get(codigo)
        return tipo.nombre if tipo else codigo.replace("_", " ").title()

    def _nombre_tipo_corto(self, codigo: str) -> str:
        nombres = {
            "INTERNA": "Interna",
            "EXTERNA": "Externa",
            "CEDI": "CEDI",
            "DEVOLUCIONES": "Devol.",
            "ALMACEN": "Almacen",
            "BODEGA": "Bodega",
            "CENTRAL_PREPARACION": "Central",
            "REEMPAQUE": "Reempaque",
            "REREPOSICION": "Reempaque",
            _TIPO_NO_CLASIFICABLE: "Sin clasif.",
        }
        return nombres.get(codigo, self._nombre_tipo(codigo))

    def _estado_legible(self, estado: str) -> str:
        nombres = {
            "NUEVA": "Nueva",
            "EXISTENTE": "Existente",
            "AMBIGUA": "Ambigua",
            "IGNORADA": "Ignorada",
        }
        return nombres.get(estado, estado.title())

    def _si_no(self, valor: bool) -> str:
        return "Si" if valor else "No"

    def _aplicar_estilo(self, widget: QWidget) -> None:
        if self.style():
            self.style().unpolish(widget)
            self.style().polish(widget)
