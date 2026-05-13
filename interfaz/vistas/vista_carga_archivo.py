"""Vista principal de carga y validacion de archivo Excel."""

from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interfaz.componentes.tarjeta_metrica import TarjetaMetrica
from interfaz.workers.worker_procesamiento import WorkerProcesamiento
from logica.lector_excel import LectorExcel
from modelos.progreso_proceso import ProgresoProceso
from modelos.resultado_carga import ResultadoCarga
from utilidades.mensajes import MensajesInterfaz

_MAX_FILAS_PREVIEW = 5
_MAX_COLS_PREVIEW = 6


class VistaCargaArchivo(QWidget):
    """Pantalla de carga, validacion y previsualizacion del archivo Excel."""

    archivo_cargado = Signal(object)
    exportacion_solicitada = Signal()
    estado_actualizado = Signal(str)
    vista_limpiada = Signal()

    def __init__(
        self,
        configuracion: dict[str, Any],
        lector_excel: LectorExcel | None = None,
    ) -> None:
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._configuracion = configuracion
        self._lector_excel = lector_excel or LectorExcel(configuracion=configuracion)
        self._ruta_seleccionada: str = ""
        self._worker_actual: WorkerProcesamiento | None = None
        self._animaciones: list[QPropertyAnimation] = []

        self._construir_ui()

    # ------------------------------------------------------------------
    # Construccion de la interfaz
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
        layout_contenedor = QVBoxLayout(contenedor)
        layout_contenedor.setContentsMargins(24, 24, 24, 16)
        layout_contenedor.setSpacing(16)

        layout_contenedor.addWidget(self._crear_card_carga())
        layout_contenedor.addLayout(self._crear_fila_metricas())
        layout_contenedor.addWidget(self._crear_card_resumen_validacion())
        layout_contenedor.addWidget(self._crear_card_preview())
        layout_contenedor.addStretch(1)

        scroll.setWidget(contenedor)
        layout_raiz.addWidget(scroll, 1)
        layout_raiz.addWidget(self._crear_barra_inferior())

    def _crear_card_carga(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(14)

        cabecera = QVBoxLayout()
        cabecera.setContentsMargins(0, 0, 0, 0)
        cabecera.setSpacing(4)

        titulo = QLabel("1. Cargar archivo")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Seleccione el Excel de movimientos, valide su estructura y revise el resumen antes de procesar."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        cabecera.addWidget(titulo)
        cabecera.addWidget(subtitulo)

        contenido = QHBoxLayout()
        contenido.setContentsMargins(0, 0, 0, 0)
        contenido.setSpacing(18)
        contenido.addWidget(self._crear_zona_carga(), 3)
        contenido.addWidget(self._crear_info_archivo(), 5)
        contenido.addWidget(self._crear_panel_botones(), 2)

        layout.addLayout(cabecera)
        layout.addLayout(contenido)
        return card

    def _crear_zona_carga(self) -> QFrame:
        zona = QFrame()
        zona.setObjectName("uploadZone")
        zona.setMinimumWidth(220)
        zona.setMinimumHeight(168)
        zona.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(zona)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        icono = QLabel("XLS")
        icono.setObjectName("iconoExcel")
        icono.setAlignment(Qt.AlignCenter)
        icono.setFixedSize(58, 52)

        titulo = QLabel("Archivo Excel de movimientos")
        titulo.setObjectName("tituloUpload")
        titulo.setAlignment(Qt.AlignCenter)

        self._boton_seleccionar = QPushButton("Seleccionar archivo Excel")
        self._boton_seleccionar.setObjectName("botonPrincipal")
        self._boton_seleccionar.setMinimumHeight(42)
        self._boton_seleccionar.clicked.connect(self.seleccionar_archivo)

        formatos = QLabel("Formatos aceptados: .xlsx, .xls")
        formatos.setObjectName("textoFormatos")
        formatos.setAlignment(Qt.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(icono, 0, Qt.AlignCenter)
        layout.addWidget(titulo, 0, Qt.AlignCenter)
        layout.addWidget(self._boton_seleccionar)
        layout.addWidget(formatos, 0, Qt.AlignCenter)
        layout.addStretch(1)
        return zona

    def _crear_info_archivo(self) -> QFrame:
        self._contenedor_info = QFrame()
        self._contenedor_info.setObjectName("infoArchivo")
        self._contenedor_info.setMinimumHeight(168)

        layout_outer = QVBoxLayout(self._contenedor_info)
        layout_outer.setContentsMargins(16, 14, 16, 14)
        layout_outer.setSpacing(10)

        self._panel_placeholder_info = QLabel(
            "Seleccione un archivo para ver nombre, hoja, registros, columnas y tamano."
        )
        self._panel_placeholder_info.setObjectName("descripcionPlaceholder")
        self._panel_placeholder_info.setAlignment(Qt.AlignCenter)
        self._panel_placeholder_info.setWordWrap(True)

        self._card_info = QWidget()
        self._card_info.setVisible(False)

        layout = QVBoxLayout(self._card_info)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        fila_nombre = QHBoxLayout()
        fila_nombre.setSpacing(10)
        icono_doc = QLabel("DOC")
        icono_doc.setObjectName("iconoDocumento")
        icono_doc.setFixedSize(34, 30)
        icono_doc.setAlignment(Qt.AlignCenter)
        self._lbl_nombre_archivo = QLabel("-")
        self._lbl_nombre_archivo.setObjectName("nombreArchivo")
        self._lbl_nombre_archivo.setWordWrap(True)
        fila_nombre.addWidget(icono_doc)
        fila_nombre.addWidget(self._lbl_nombre_archivo, 1)

        fila_meta1 = QHBoxLayout()
        fila_meta1.setSpacing(18)
        self._lbl_hoja = self._meta_par("Hoja", "-")
        self._lbl_registros = self._meta_par("Registros", "-")
        self._lbl_columnas = self._meta_par("Columnas", "-")
        for widget in (self._lbl_hoja, self._lbl_registros, self._lbl_columnas):
            fila_meta1.addWidget(widget)

        fila_meta2 = QHBoxLayout()
        fila_meta2.setSpacing(18)
        self._lbl_fecha = self._meta_par("Modificado", "-")
        self._lbl_tamano = self._meta_par("Tamano", "-")
        fila_meta2.addWidget(self._lbl_fecha)
        fila_meta2.addWidget(self._lbl_tamano)
        fila_meta2.addStretch(1)

        layout.addLayout(fila_nombre)
        layout.addLayout(fila_meta1)
        layout.addLayout(fila_meta2)

        layout_outer.addWidget(self._panel_placeholder_info, 1)
        layout_outer.addWidget(self._card_info)
        return self._contenedor_info

    def _meta_par(self, etiqueta: str, valor: str) -> QWidget:
        cont = QWidget()
        layout = QVBoxLayout(cont)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        lbl_e = QLabel(etiqueta.upper())
        lbl_e.setObjectName("tituloBloque")
        lbl_v = QLabel(valor)
        lbl_v.setObjectName("metadatoArchivo")

        layout.addWidget(lbl_e)
        layout.addWidget(lbl_v)
        return cont

    def _crear_panel_botones(self) -> QWidget:
        cont = QWidget()
        layout = QVBoxLayout(cont)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignTop)

        self._boton_validar = QPushButton("Validar archivo")
        self._boton_validar.setObjectName("botonPrincipal")
        self._boton_validar.setMinimumHeight(46)
        self._boton_validar.setMinimumWidth(150)
        self._boton_validar.setEnabled(False)
        self._boton_validar.clicked.connect(self.cargar_archivo)

        self._boton_limpiar = QPushButton("Limpiar")
        self._boton_limpiar.setObjectName("botonSecundario")
        self._boton_limpiar.setMinimumHeight(44)
        self._boton_limpiar.setEnabled(False)
        self._boton_limpiar.clicked.connect(self.limpiar)

        self._boton_exportar = QPushButton("Exportar resultado")
        self._boton_exportar.setObjectName("botonExito")
        self._boton_exportar.setMinimumHeight(44)
        self._boton_exportar.setEnabled(False)
        self._boton_exportar.setVisible(False)
        self._boton_exportar.clicked.connect(self.exportacion_solicitada.emit)

        layout.addWidget(self._boton_validar)
        layout.addWidget(self._boton_limpiar)
        layout.addWidget(self._boton_exportar)
        return cont

    def _crear_fila_metricas(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(16)

        self._tarjeta_registros = TarjetaMetrica(
            "Registros",
            "-",
            icono="DOC",
            tipo="info",
            descripcion="Total de registros detectados",
        )
        self._tarjeta_columnas = TarjetaMetrica(
            "Columnas validas",
            "-",
            icono="OK",
            tipo="exito",
            descripcion="Columnas requeridas presentes",
        )
        self._tarjeta_estado = TarjetaMetrica(
            "Estado",
            "-",
            icono="VAL",
            tipo="neutro",
            descripcion="Pendiente de validacion",
        )

        for tarjeta in (
            self._tarjeta_registros,
            self._tarjeta_columnas,
            self._tarjeta_estado,
        ):
            fila.addWidget(tarjeta)
        return fila

    def _crear_card_resumen_validacion(self) -> QFrame:
        self._card_validacion = QFrame()
        self._card_validacion.setObjectName("panelArchivo")
        self._card_validacion.setVisible(False)

        layout = QVBoxLayout(self._card_validacion)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        cabecera = QHBoxLayout()
        titulo_val = QLabel("Resumen de validacion")
        titulo_val.setObjectName("tituloSubpanel")

        self._boton_colapsar = QPushButton("^")
        self._boton_colapsar.setObjectName("botonTerciario")
        self._boton_colapsar.setFixedSize(32, 32)
        self._boton_colapsar.clicked.connect(self._toggle_validacion)

        cabecera.addWidget(titulo_val)
        cabecera.addStretch(1)
        cabecera.addWidget(self._boton_colapsar)

        self._contenido_validacion = QWidget()
        layout_val = QHBoxLayout(self._contenido_validacion)
        layout_val.setContentsMargins(0, 0, 0, 0)
        layout_val.setSpacing(18)

        self._fila_columnas_req = self._crear_fila_validacion(
            "OK", "correcto", "Columnas requeridas", "-", "-"
        )
        self._fila_aliases = self._crear_fila_validacion(
            "AL", "info", "Aliases detectados", "-", "-"
        )
        self._fila_desconocidas = self._crear_fila_validacion(
            "?", "advertencia", "Columnas desconocidas", "-", "-"
        )

        layout_val.addWidget(self._fila_columnas_req, 1)
        layout_val.addWidget(self._crear_divisor_vertical())
        layout_val.addWidget(self._fila_aliases, 1)
        layout_val.addWidget(self._crear_divisor_vertical())
        layout_val.addWidget(self._fila_desconocidas, 1)

        layout.addLayout(cabecera)
        layout.addWidget(self._contenido_validacion)
        return self._card_validacion

    def _crear_fila_validacion(
        self,
        icono: str,
        tipo: str,
        titulo: str,
        cantidad: str,
        descripcion: str,
    ) -> QFrame:
        fila = QFrame()
        fila.setObjectName("itemResumenVal")

        layout = QHBoxLayout(fila)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(12)

        from interfaz.componentes.badge_estado import BadgeEstado

        badge = BadgeEstado(icono, tipo)
        badge.setFixedSize(34, 34)
        badge.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(3)
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("tituloBloque")
        lbl_cantidad = QLabel(cantidad)
        lbl_cantidad.setObjectName("valorCampo")
        lbl_desc = QLabel(descripcion)
        lbl_desc.setObjectName("textoSecundario")
        lbl_desc.setWordWrap(True)

        textos.addWidget(lbl_titulo)
        textos.addWidget(lbl_cantidad)
        textos.addWidget(lbl_desc)

        layout.addWidget(badge)
        layout.addLayout(textos, 1)

        fila._lbl_cantidad = lbl_cantidad  # type: ignore[attr-defined]
        fila._lbl_desc = lbl_desc  # type: ignore[attr-defined]
        fila._badge = badge  # type: ignore[attr-defined]
        return fila

    def _crear_divisor_vertical(self) -> QFrame:
        divisor = QFrame()
        divisor.setObjectName("divisorVertical")
        divisor.setFixedWidth(1)
        return divisor

    def _crear_card_preview(self) -> QFrame:
        self._card_preview = QFrame()
        self._card_preview.setObjectName("panelArchivo")
        self._card_preview.setVisible(False)

        layout = QVBoxLayout(self._card_preview)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        titulo_prev = QLabel(f"Vista previa de datos (primeras {_MAX_FILAS_PREVIEW} filas)")
        titulo_prev.setObjectName("tituloSubpanel")

        self._tabla_preview = QTableWidget(0, 0)
        self._tabla_preview.setAlternatingRowColors(True)
        self._tabla_preview.verticalHeader().setVisible(False)
        self._tabla_preview.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_preview.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla_preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._tabla_preview.setMinimumHeight(178)

        layout.addWidget(titulo_prev)
        layout.addWidget(self._tabla_preview)
        return self._card_preview

    def _crear_barra_inferior(self) -> QFrame:
        barra = QFrame()
        barra.setObjectName("barraInferior")
        barra.setFixedHeight(68)

        layout = QHBoxLayout(barra)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        self._icono_estado = QLabel("-")
        self._icono_estado.setObjectName("iconoEstadoNeutro")
        self._icono_estado.setFixedSize(30, 30)
        self._icono_estado.setAlignment(Qt.AlignCenter)

        self._lbl_estado_barra = QLabel("Sin archivo cargado")
        self._lbl_estado_barra.setObjectName("mensajeEstadoNeutro")

        self._barra_progreso = QProgressBar()
        self._barra_progreso.setRange(0, 100)
        self._barra_progreso.setValue(0)
        self._barra_progreso.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._boton_ver_detalles = QPushButton("Ver detalles")
        self._boton_ver_detalles.setObjectName("botonSecundario")
        self._boton_ver_detalles.setMinimumHeight(36)
        self._boton_ver_detalles.setFixedWidth(132)
        self._boton_ver_detalles.setVisible(False)

        layout.addWidget(self._icono_estado)
        layout.addWidget(self._lbl_estado_barra)
        layout.addWidget(self._barra_progreso, 1)
        layout.addWidget(self._boton_ver_detalles)
        return barra

    # ------------------------------------------------------------------
    # API publica (conservada del diseno original)
    # ------------------------------------------------------------------

    def seleccionar_archivo(self) -> None:
        """Abre el selector de archivos Excel."""
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo Excel",
            "",
            "Archivos Excel (*.xlsx *.xls)",
        )

        if not ruta:
            self._actualizar_barra("Sin archivo seleccionado", 0, "neutro")
            self.estado_actualizado.emit(MensajesInterfaz.LISTO)
            return

        self._ruta_seleccionada = ruta
        self._boton_validar.setEnabled(True)
        self._boton_limpiar.setEnabled(True)
        self._mostrar_archivo_seleccionado(ruta)
        self._actualizar_barra(f"Archivo seleccionado: {Path(ruta).name}", 0, "info")
        self.estado_actualizado.emit(MensajesInterfaz.ARCHIVO_SELECCIONADO)

    def cargar_archivo(self) -> None:
        """Inicia la lectura del archivo en un worker de segundo plano."""
        if not self._ruta_seleccionada:
            self._actualizar_barra(MensajesInterfaz.ERROR_SIN_ARCHIVO, 0, "error")
            self.estado_actualizado.emit(MensajesInterfaz.ERROR_LECTURA)
            return

        self._actualizar_barra(MensajesInterfaz.PROCESANDO, 20, "info")
        self.estado_actualizado.emit(MensajesInterfaz.PROCESANDO)
        self._boton_validar.setEnabled(False)
        self._boton_seleccionar.setEnabled(False)
        self._boton_limpiar.setEnabled(False)

        self._worker_actual = WorkerProcesamiento(
            self._lector_excel, Path(self._ruta_seleccionada)
        )
        self._worker_actual.senales.progreso.connect(self._al_recibir_progreso)
        self._worker_actual.senales.finalizado.connect(self._al_finalizar)
        self._worker_actual.senales.error.connect(self._al_ocurrir_error)
        self._worker_actual.senales.cancelado.connect(self._al_cancelar)
        QThreadPool.globalInstance().start(self._worker_actual)

    def limpiar(self) -> None:
        """Restablece la vista al estado inicial."""
        self._ruta_seleccionada = ""
        self._worker_actual = None

        self._boton_validar.setEnabled(False)
        self._boton_limpiar.setEnabled(False)
        self._boton_exportar.setEnabled(False)
        self._boton_exportar.setVisible(False)
        self._boton_seleccionar.setEnabled(True)

        self._tarjeta_registros.actualizar("-")
        self._tarjeta_columnas.actualizar("-")
        self._tarjeta_estado.actualizar(
            "-",
            descripcion="Pendiente de validacion",
            estilo_valor="valorMetrica",
        )
        self._tarjeta_estado.establecer_icono("VAL", "neutro")

        self._card_validacion.setVisible(False)
        self._card_preview.setVisible(False)
        self._card_info.setVisible(False)
        self._boton_ver_detalles.setVisible(False)
        self._tabla_preview.setRowCount(0)
        self._tabla_preview.setColumnCount(0)

        self._contenedor_info.setObjectName("infoArchivo")
        self._aplicar_estilo(self._contenedor_info)
        self._panel_placeholder_info.setVisible(True)

        self._actualizar_barra("Sin archivo cargado", 0, "neutro")
        self.estado_actualizado.emit(MensajesInterfaz.LISTO)
        self.vista_limpiada.emit()

    def establecer_exportacion_disponible(self, disponible: bool) -> None:
        """Muestra u oculta el boton de exportacion."""
        self._boton_exportar.setEnabled(disponible)
        self._boton_exportar.setVisible(disponible)

    def mostrar_resultado_exportacion(self, mensaje: str, exito: bool) -> None:
        """Muestra el resultado de la exportacion en la barra inferior."""
        tipo = "correcto" if exito else "error"
        progreso = 100 if exito else 0
        self._actualizar_barra(mensaje, progreso, tipo)

    def actualizar_estado_flujo(self, mensaje: str) -> None:
        """Actualiza el mensaje de estado en la barra inferior."""
        tipo = self._inferir_tipo(mensaje)
        self._actualizar_barra(mensaje, self._barra_progreso.value(), tipo)

    # ------------------------------------------------------------------
    # Manejadores del worker
    # ------------------------------------------------------------------

    def _al_recibir_progreso(self, progreso: ProgresoProceso) -> None:
        porcentaje = progreso.porcentaje if hasattr(progreso, "porcentaje") else 50
        pct = min(80, max(20, porcentaje))
        self._actualizar_barra(progreso.mensaje, pct, "info")

    def _al_finalizar(self, resultado: ResultadoCarga) -> None:
        self._worker_actual = None
        self._boton_validar.setEnabled(True)
        self._boton_seleccionar.setEnabled(True)
        self._boton_limpiar.setEnabled(True)

        if resultado.exito:
            self._mostrar_resultado(resultado)
            exportable = bool(
                resultado.estructura_valida and resultado.dataframe_procesado is not None
            )
            self._boton_exportar.setEnabled(exportable)
            self._boton_exportar.setVisible(exportable)
            tipo = "correcto" if resultado.estructura_valida else "advertencia"
            self._actualizar_barra(resultado.mensaje, 100, tipo)
            self.estado_actualizado.emit(
                MensajesInterfaz.ARCHIVO_CARGADO
                if resultado.estructura_valida
                else MensajesInterfaz.ESTRUCTURA_INVALIDA
            )
            self.archivo_cargado.emit(resultado)
            return

        self._logger.warning("Carga fallida: %s", resultado.mensaje)
        self._boton_exportar.setEnabled(False)
        self._boton_exportar.setVisible(False)
        self._actualizar_barra(resultado.mensaje, 0, "error")
        self.estado_actualizado.emit(MensajesInterfaz.ERROR_LECTURA)

    def _al_ocurrir_error(self, mensaje_error: str) -> None:
        self._worker_actual = None
        self._boton_validar.setEnabled(True)
        self._boton_seleccionar.setEnabled(True)
        self._boton_limpiar.setEnabled(True)
        self._logger.error("Error en worker: %s", mensaje_error)
        self._actualizar_barra(f"{MensajesInterfaz.ERROR_APERTURA}: {mensaje_error}", 0, "error")
        self.estado_actualizado.emit(MensajesInterfaz.ERROR_LECTURA)

    def _al_cancelar(self) -> None:
        self._worker_actual = None
        self._boton_validar.setEnabled(True)
        self._boton_seleccionar.setEnabled(True)
        self._boton_limpiar.setEnabled(True)
        self._actualizar_barra("Procesamiento cancelado.", 0, "advertencia")
        self.estado_actualizado.emit(MensajesInterfaz.LISTO)

    # ------------------------------------------------------------------
    # Visualizacion del resultado
    # ------------------------------------------------------------------

    def _mostrar_resultado(self, resultado: ResultadoCarga) -> None:
        self._actualizar_info_archivo(resultado)
        self._actualizar_metricas(resultado)
        self._actualizar_resumen_validacion(resultado)
        self._actualizar_tabla_preview(resultado)
        self._animar_entrada(self._card_validacion)
        if self._card_preview.isVisible():
            self._animar_entrada(self._card_preview)

    def _mostrar_archivo_seleccionado(self, ruta: str) -> None:
        self._lbl_nombre_archivo.setText(Path(ruta).name)
        self._set_meta(self._lbl_hoja, self._configuracion.get("hoja_excel", "-"))
        self._set_meta(self._lbl_registros, "Pendiente")
        self._set_meta(self._lbl_columnas, "Pendiente")
        self._actualizar_meta_archivo(ruta)
        self._card_info.setVisible(True)
        self._panel_placeholder_info.setVisible(False)
        self._contenedor_info.setObjectName("infoArchivoActivo")
        self._aplicar_estilo(self._contenedor_info)
        self._animar_entrada(self._card_info)

    def _actualizar_info_archivo(self, resultado: ResultadoCarga) -> None:
        self._lbl_nombre_archivo.setText(resultado.nombre_archivo or "-")

        hoja = resultado.hoja_utilizada or "-"
        registros = self._formatear_entero(resultado.cantidad_filas)
        columnas = str(resultado.cantidad_columnas) if resultado.cantidad_columnas else "-"

        self._set_meta(self._lbl_hoja, hoja)
        self._set_meta(self._lbl_registros, registros)
        self._set_meta(self._lbl_columnas, columnas)

        if resultado.ruta_archivo:
            self._actualizar_meta_archivo(resultado.ruta_archivo)

        self._card_info.setVisible(True)
        self._panel_placeholder_info.setVisible(False)
        self._contenedor_info.setObjectName("infoArchivoActivo")
        self._aplicar_estilo(self._contenedor_info)

    def _actualizar_meta_archivo(self, ruta_archivo: str) -> None:
        try:
            stat = os.stat(ruta_archivo)
            tamano_mb = stat.st_size / (1024 * 1024)
            tamano_str = f"{tamano_mb:.1f} MB"
            fecha = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
        except OSError:
            tamano_str = "-"
            fecha = "-"
        self._set_meta(self._lbl_fecha, fecha)
        self._set_meta(self._lbl_tamano, tamano_str)

    def _actualizar_metricas(self, resultado: ResultadoCarga) -> None:
        self._tarjeta_registros.actualizar(
            self._formatear_entero(resultado.cantidad_filas)
        )

        resumen_val = resultado.resumen_validacion or {}
        encontradas = len(resumen_val.get("columnas_encontradas", []))
        mapeadas = len(resumen_val.get("columnas_mapeadas_por_alias", {}))
        total_validas = encontradas + mapeadas
        total_requeridas = len(self._configuracion.get("columnas_requeridas", [])) or total_validas
        total_requeridas = max(total_requeridas, total_validas)
        self._tarjeta_columnas.actualizar(
            f"{total_validas}/{total_requeridas}" if total_requeridas else "-"
        )

        if resultado.estructura_valida:
            self._tarjeta_estado.establecer_icono("OK", "exito")
            self._tarjeta_estado.actualizar(
                "Archivo valido",
                descripcion="Listo para procesar",
                estilo_valor="valorMetricaEstadoCorrecto",
            )
        else:
            self._tarjeta_estado.establecer_icono("REV", "advertencia")
            self._tarjeta_estado.actualizar(
                "Revisar estructura",
                descripcion="Hay columnas pendientes",
                estilo_valor="valorMetricaEstadoAdvertencia",
            )

    def _actualizar_resumen_validacion(self, resultado: ResultadoCarga) -> None:
        resumen = resultado.resumen_validacion or {}
        encontradas = list(resumen.get("columnas_encontradas", []))
        mapeadas = dict(resumen.get("columnas_mapeadas_por_alias", {}))
        desconocidas = list(resumen.get("columnas_desconocidas", []))
        faltantes = list(resumen.get("columnas_faltantes", []))

        total_req = len(encontradas) + len(mapeadas)
        self._fila_columnas_req._lbl_cantidad.setText(f"{total_req} presentes")
        self._fila_columnas_req._lbl_desc.setText(
            "Todas las columnas requeridas fueron encontradas."
            if not faltantes
            else f"Faltan {len(faltantes)} columnas requeridas."
        )
        self._fila_columnas_req._badge.establecer_estado(
            "OK" if not faltantes else "!",
            "correcto" if not faltantes else "advertencia",
        )

        self._fila_aliases._lbl_cantidad.setText(f"{len(mapeadas)} columnas")
        self._fila_aliases._lbl_desc.setText(
            "Se detectaron alias y fueron mapeados correctamente."
            if mapeadas
            else "No se detectaron alias adicionales."
        )

        self._fila_desconocidas._lbl_cantidad.setText(f"{len(desconocidas)} columnas")
        self._fila_desconocidas._lbl_desc.setText(
            "Estas columnas no se utilizan en la clasificacion."
            if desconocidas
            else "No hay columnas desconocidas."
        )

        self._card_validacion.setVisible(True)

    def _actualizar_tabla_preview(self, resultado: ResultadoCarga) -> None:
        df = resultado.dataframe
        if df is None or df.empty:
            self._card_preview.setVisible(False)
            return

        filas_preview = df.head(_MAX_FILAS_PREVIEW)
        columnas = list(filas_preview.columns)[:_MAX_COLS_PREVIEW]

        self._tabla_preview.setColumnCount(len(columnas))
        self._tabla_preview.setRowCount(len(filas_preview))
        self._tabla_preview.setHorizontalHeaderLabels(columnas)

        for i, (_, fila) in enumerate(filas_preview.iterrows()):
            for j, col in enumerate(columnas):
                valor = str(fila[col]) if col in fila else "-"
                item = QTableWidgetItem(valor)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self._tabla_preview.setItem(i, j, item)

        self._card_preview.setVisible(True)
        self._boton_ver_detalles.setVisible(True)

    # ------------------------------------------------------------------
    # Barra inferior y utilidades
    # ------------------------------------------------------------------

    def _actualizar_barra(self, mensaje: str, progreso: int, tipo: str) -> None:
        iconos = {
            "correcto": "OK",
            "error": "X",
            "advertencia": "!",
            "info": "i",
            "neutro": "-",
        }
        nombres_mensaje = {
            "correcto": "mensajeEstado",
            "error": "mensajeEstadoError",
            "advertencia": "mensajeEstadoAdvertencia",
            "info": "mensajeCargaInfo",
            "neutro": "mensajeEstadoNeutro",
        }
        nombres_icono = {
            "correcto": "iconoEstadoCorrecto",
            "error": "iconoEstadoError",
            "advertencia": "iconoEstadoAdvertencia",
            "info": "iconoEstadoInfo",
            "neutro": "iconoEstadoNeutro",
        }

        self._icono_estado.setText(iconos.get(tipo, "-"))
        self._icono_estado.setObjectName(nombres_icono.get(tipo, "iconoEstadoNeutro"))
        self._lbl_estado_barra.setText(mensaje)
        self._lbl_estado_barra.setObjectName(nombres_mensaje.get(tipo, "mensajeEstadoNeutro"))
        self._aplicar_estilo(self._icono_estado)
        self._aplicar_estilo(self._lbl_estado_barra)
        self._barra_progreso.setValue(max(0, min(100, progreso)))

    def _toggle_validacion(self) -> None:
        visible = self._contenido_validacion.isVisible()
        self._contenido_validacion.setVisible(not visible)
        self._boton_colapsar.setText("v" if visible else "^")

    def _inferir_tipo(self, mensaje: str) -> str:
        mensaje_normalizado = mensaje.lower()
        if "error" in mensaje_normalizado or "no fue posible" in mensaje_normalizado:
            return "error"
        if "invalida" in mensaje_normalizado or "invalido" in mensaje_normalizado:
            return "advertencia"
        if "exportado" in mensaje_normalizado or "cargado correctamente" in mensaje_normalizado:
            return "correcto"
        if "procesando" in mensaje_normalizado or "seleccionado" in mensaje_normalizado:
            return "info"
        return "neutro"

    def _set_meta(self, contenedor: QWidget, valor: str) -> None:
        item = contenedor.layout().itemAt(1) if contenedor.layout() else None
        if item and item.widget():
            item.widget().setText(valor)

    def _formatear_entero(self, valor: int) -> str:
        return f"{valor:,}".replace(",", ".") if valor else "-"

    def _animar_entrada(self, widget: QWidget) -> None:
        efecto = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(efecto)
        animacion = QPropertyAnimation(efecto, b"opacity", widget)
        animacion.setDuration(240)
        animacion.setStartValue(0.0)
        animacion.setEndValue(1.0)
        animacion.setEasingCurve(QEasingCurve.OutCubic)
        animacion.finished.connect(lambda: widget.setGraphicsEffect(None))
        animacion.start()
        self._animaciones.append(animacion)

    def _aplicar_estilo(self, widget: QWidget) -> None:
        if self.style():
            self.style().unpolish(widget)
            self.style().polish(widget)
