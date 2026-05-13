"""Vista funcional de exportacion del resultado clasificado."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QThreadPool, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
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

from interfaz.componentes.tarjeta_metrica import TarjetaMetrica
from interfaz.workers.worker_exportacion import WorkerExportacion
from logica.exportador_excel import ExportadorExcel
from modelos.resultado_carga import ResultadoCarga
from modelos.resultado_exportacion import ResultadoExportacion
from persistencia.conexion import sesion_scope
from servicios.excepciones import ErrorDominio
from servicios.servicio_ejecuciones import ServicioEjecuciones
from utilidades.mensajes import MensajesInterfaz
from utilidades.rutas import limpiar_nombre_archivo, obtener_ruta_salidas


_SALIDAS_EXPORTACION: tuple[tuple[str, str, str], ...] = (
    ("DETALLE_CLASIFICADO", "Detalle clasificado", "Movimientos con tipologia, farmacia y regla aplicada."),
    ("SIN_CLASIFICAR", "Registros sin clasificar", "Movimientos que requieren revision antes del cierre."),
    ("RESUMEN_TIPOLOGIA", "Resumen por tipologia", "Conteo consolidado de movimientos por tipologia."),
    ("RESUMEN_FARMACIA", "Resumen por farmacia", "Conteo consolidado de movimientos por farmacia."),
    ("CRUCE_TIPOLOGIA_FARMACIA", "Cruce tipologia vs farmacia", "Matriz con tipologias en filas y farmacias en columnas."),
    ("LIQUIDOS", "Liquidos Cirugia", "Listado unico de articulos incluidos en la lista LIQUIDOS."),
    ("MCE_CIRUGIA", "MCE Cirugia", "Listado unico de articulos incluidos en la lista MCE_CIRUGIA."),
    ("ORIGINAL", "Original completo", "Copia del archivo de entrada para trazabilidad."),
)


class VistaExportacion(QWidget):
    """Pantalla de configuracion y ejecucion de la exportacion."""

    exportacion_completada = Signal(object)
    estado_actualizado = Signal(str)
    procesar_otro_archivo = Signal()

    def __init__(self, configuracion: dict[str, Any] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._configuracion = configuracion or {}
        self._resultado_carga: ResultadoCarga | None = None
        self._resultado_exportacion: ResultadoExportacion | None = None
        self._ruta_salida = obtener_ruta_salidas(self._configuracion)
        self._exportador = ExportadorExcel()
        self._checks_salida: list[QCheckBox] = []
        self._animaciones: list[QPropertyAnimation] = []
        self._worker_exportacion: WorkerExportacion | None = None

        self._construir_ui()
        self.limpiar_resultado()
        self._cargar_historial()

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
        layout.addWidget(self._crear_resumen_estado())
        layout.addLayout(self._crear_config_exportacion())
        layout.addWidget(self._crear_historial())
        layout.addWidget(self._crear_barra_resultado())
        layout.addStretch(1)

        scroll.setWidget(contenedor)
        layout_raiz.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        icono = QLabel("EX")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(50, 50)
        icono.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setSpacing(4)
        titulo = QLabel("5. Exportar resultado")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Genere el archivo final, revise las salidas incluidas y conserve el historial del proceso."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)

        layout.addWidget(icono)
        layout.addLayout(textos, 1)
        return card

    def _crear_resumen_estado(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(18)

        self._lbl_icono_estado = QLabel("OK")
        self._lbl_icono_estado.setObjectName("iconoEstadoCorrecto")
        self._lbl_icono_estado.setFixedSize(42, 42)
        self._lbl_icono_estado.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setSpacing(3)
        self._lbl_estado_titulo = QLabel("Sin archivo para exportar")
        self._lbl_estado_titulo.setObjectName("mensajeEstadoNeutro")
        self._lbl_estado_subtitulo = QLabel("Cargue y valide un archivo antes de generar la salida Excel.")
        self._lbl_estado_subtitulo.setObjectName("textoSecundario")
        self._lbl_estado_subtitulo.setWordWrap(True)
        textos.addWidget(self._lbl_estado_titulo)
        textos.addWidget(self._lbl_estado_subtitulo)

        layout.addWidget(self._lbl_icono_estado)
        layout.addLayout(textos, 1)
        layout.addWidget(self._divisor_vertical())

        self._kpi_total = TarjetaMetrica(
            "Total registros",
            "0",
            icono="REG",
            tipo="info",
            descripcion="Listos para exportar",
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
        self._kpi_farmacias = TarjetaMetrica(
            "Farmacias detectadas",
            "0",
            icono="FAR",
            tipo="neutro",
            descripcion="Unicas en el archivo",
        )
        for tarjeta in (
            self._kpi_total,
            self._kpi_clasificados,
            self._kpi_sin_clasificar,
            self._kpi_farmacias,
        ):
            tarjeta.setMinimumWidth(150)
            layout.addWidget(tarjeta)
        return card

    def _crear_config_exportacion(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(self._crear_hojas_checklist(), 1)
        layout.addWidget(self._crear_configuracion_archivo(), 1)
        return layout

    def _crear_hojas_checklist(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        cabecera = QVBoxLayout()
        cabecera.setSpacing(4)
        titulo = QLabel("Seleccionar salidas para exportar")
        titulo.setObjectName("tituloSubpanel")
        subtitulo = QLabel("Elija las hojas que deben quedar visibles en el archivo final.")
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        cabecera.addWidget(titulo)
        cabecera.addWidget(subtitulo)
        layout.addLayout(cabecera)

        self._checks_salida = []
        for _, nombre, descripcion in _SALIDAS_EXPORTACION:
            layout.addWidget(self._crear_item_salida(nombre, descripcion))

        self._lbl_salida_resumen = QLabel(f"0 de {len(_SALIDAS_EXPORTACION)} salidas seleccionadas")
        self._lbl_salida_resumen.setObjectName("mensajeEstadoNeutro")
        layout.addWidget(self._lbl_salida_resumen)
        layout.addStretch(1)
        return card

    def _crear_item_salida(self, nombre: str, descripcion: str) -> QFrame:
        item = QFrame()
        item.setObjectName("subbloquePanel")
        layout = QHBoxLayout(item)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(10)

        check = QCheckBox()
        check.setObjectName("checkSalida")
        check.setChecked(True)
        check.stateChanged.connect(self._actualizar_resumen_salidas)
        self._checks_salida.append(check)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        titulo = QLabel(nombre)
        titulo.setObjectName("valorCampo")
        detalle = QLabel(descripcion)
        detalle.setObjectName("textoSecundario")
        detalle.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(detalle)

        layout.addWidget(check)
        layout.addLayout(textos, 1)
        return item

    def _crear_configuracion_archivo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        cabecera = QVBoxLayout()
        cabecera.setSpacing(4)
        titulo = QLabel("Configuracion de exportacion")
        titulo.setObjectName("tituloSubpanel")
        subtitulo = QLabel("Defina la ubicacion y el nombre base del archivo de salida.")
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        cabecera.addWidget(titulo)
        cabecera.addWidget(subtitulo)
        layout.addLayout(cabecera)

        layout.addWidget(self._lbl("Carpeta de salida", "tituloBloque"))
        fila_ruta = QHBoxLayout()
        fila_ruta.setSpacing(12)
        self._entrada_ruta = QLineEdit(str(self._ruta_salida))
        self._entrada_ruta.setReadOnly(True)
        self._entrada_ruta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._boton_cambiar_carpeta = QPushButton("Cambiar carpeta")
        self._boton_cambiar_carpeta.setObjectName("botonSecundario")
        self._boton_cambiar_carpeta.setMinimumHeight(42)
        self._boton_cambiar_carpeta.clicked.connect(self._seleccionar_carpeta)
        fila_ruta.addWidget(self._entrada_ruta, 1)
        fila_ruta.addWidget(self._boton_cambiar_carpeta)
        layout.addLayout(fila_ruta)

        layout.addWidget(self._lbl("Nombre del archivo", "tituloBloque"))
        self._entrada_nombre = QLineEdit("resultado.xlsx")
        self._entrada_nombre.setPlaceholderText("resultado.xlsx")
        self._entrada_nombre.textChanged.connect(self._actualizar_estado_exportar)
        layout.addWidget(self._entrada_nombre)

        ayuda = QFrame()
        ayuda.setObjectName("subbloquePanel")
        ayuda_layout = QHBoxLayout(ayuda)
        ayuda_layout.setContentsMargins(14, 12, 14, 12)
        ayuda_layout.setSpacing(10)
        ayuda_icono = QLabel("i")
        ayuda_icono.setObjectName("iconoEstadoInfo")
        ayuda_icono.setFixedSize(30, 30)
        ayuda_icono.setAlignment(Qt.AlignCenter)
        ayuda_texto = QLabel(
            "El sistema agregara fecha y hora al nombre final para evitar sobrescribir archivos."
        )
        ayuda_texto.setObjectName("textoSecundario")
        ayuda_texto.setWordWrap(True)
        ayuda_layout.addWidget(ayuda_icono)
        ayuda_layout.addWidget(ayuda_texto, 1)
        layout.addWidget(ayuda)

        self._check_reclasificar = QCheckBox("Aplicar reglas actualizadas antes de exportar")
        self._check_reclasificar.setChecked(True)
        self._check_reclasificar.setToolTip(
            "Recalcula la clasificacion con las reglas activas guardadas antes de generar el Excel."
        )
        layout.addWidget(self._check_reclasificar)

        layout.addStretch(1)

        self._boton_exportar = QPushButton("Exportar Excel")
        self._boton_exportar.setObjectName("botonPrincipal")
        self._boton_exportar.setMinimumHeight(52)
        self._boton_exportar.clicked.connect(self._exportar)
        layout.addWidget(self._boton_exportar)

        # Barra de progreso (oculta hasta que comience la exportacion).
        self._barra_progreso = QProgressBar()
        self._barra_progreso.setRange(0, 100)
        self._barra_progreso.setValue(0)
        self._barra_progreso.setTextVisible(False)
        self._barra_progreso.setVisible(False)
        layout.addWidget(self._barra_progreso)

        self._lbl_progreso = QLabel("")
        self._lbl_progreso.setObjectName("textoSecundario")
        self._lbl_progreso.setVisible(False)
        layout.addWidget(self._lbl_progreso)
        return card

    def _crear_historial(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        cabecera = QVBoxLayout()
        cabecera.setSpacing(3)
        titulo = QLabel("Historial reciente")
        titulo.setObjectName("tituloSubpanel")
        subtitulo = QLabel("Ultimas exportaciones y procesos registrados.")
        subtitulo.setObjectName("textoSecundario")
        cabecera.addWidget(titulo)
        cabecera.addWidget(subtitulo)
        layout.addLayout(cabecera)

        self._tabla_historial = QTableWidget(0, 6)
        self._tabla_historial.setHorizontalHeaderLabels(
            ["FECHA", "ARCHIVO", "REGISTROS", "CLASIFICADOS", "SIN CLASIFICAR", "ESTADO"]
        )
        encabezado = self._tabla_historial.horizontalHeader()
        encabezado.setMinimumSectionSize(80)
        for columna, ancho in {0: 150, 2: 105, 3: 115, 4: 120, 5: 120}.items():
            encabezado.setSectionResizeMode(columna, QHeaderView.Fixed)
            self._tabla_historial.setColumnWidth(columna, ancho)
        encabezado.setSectionResizeMode(1, QHeaderView.Stretch)
        self._tabla_historial.verticalHeader().setVisible(False)
        self._tabla_historial.verticalHeader().setDefaultSectionSize(40)
        self._tabla_historial.setAlternatingRowColors(True)
        self._tabla_historial.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_historial.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_historial.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabla_historial.setWordWrap(False)
        self._tabla_historial.setMinimumHeight(165)
        self._tabla_historial.setMaximumHeight(220)
        layout.addWidget(self._tabla_historial)
        return card

    def _crear_barra_resultado(self) -> QFrame:
        self._barra_resultado = QFrame()
        self._barra_resultado.setObjectName("barraResultadoExito")
        layout = QHBoxLayout(self._barra_resultado)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        self._lbl_resultado_icono = QLabel("OK")
        self._lbl_resultado_icono.setObjectName("iconoEstadoCorrecto")
        self._lbl_resultado_icono.setFixedSize(38, 38)
        self._lbl_resultado_icono.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        self._lbl_resultado_titulo = QLabel("Exportacion completada correctamente")
        self._lbl_resultado_titulo.setObjectName("mensajeEstado")
        self._lbl_resultado_detalle = QLabel("El archivo se genero exitosamente.")
        self._lbl_resultado_detalle.setObjectName("textoSecundario")
        self._lbl_resultado_detalle.setWordWrap(True)
        textos.addWidget(self._lbl_resultado_titulo)
        textos.addWidget(self._lbl_resultado_detalle)

        self._boton_abrir_archivo = QPushButton("Abrir archivo")
        self._boton_abrir_archivo.setObjectName("botonSecundario")
        self._boton_abrir_archivo.clicked.connect(self._abrir_archivo_exportado)
        self._boton_abrir_carpeta = QPushButton("Abrir carpeta")
        self._boton_abrir_carpeta.setObjectName("botonSecundario")
        self._boton_abrir_carpeta.clicked.connect(self._abrir_carpeta_exportada)
        self._boton_otro_archivo = QPushButton("Procesar otro archivo")
        self._boton_otro_archivo.setObjectName("botonSecundario")
        self._boton_otro_archivo.clicked.connect(self.procesar_otro_archivo.emit)

        layout.addWidget(self._lbl_resultado_icono)
        layout.addLayout(textos, 1)
        layout.addWidget(self._boton_abrir_archivo)
        layout.addWidget(self._boton_abrir_carpeta)
        layout.addWidget(self._boton_otro_archivo)
        return self._barra_resultado

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def establecer_resultado_carga(self, resultado: ResultadoCarga) -> None:
        """Recibe el resultado cargado y actualiza el resumen exportable."""
        self._resultado_carga = resultado
        self._resultado_exportacion = None
        self._ocultar_barra_resultado()
        self._actualizar_nombre_sugerido()
        self._actualizar_resumen()
        self._actualizar_estado_exportar()
        self._animar_entrada(self._boton_exportar)

    def limpiar_resultado(self) -> None:
        """Reinicia la pantalla cuando el flujo vuelve a carga."""
        self._resultado_carga = None
        self._resultado_exportacion = None
        self._ocultar_barra_resultado()
        self._entrada_nombre.setText("resultado.xlsx")
        self._actualizar_resumen()
        self._actualizar_estado_exportar()
        self._actualizar_resumen_salidas()

    def recargar_historial(self) -> None:
        """Actualiza el historial visible desde persistencia."""
        self._cargar_historial()

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _seleccionar_carpeta(self) -> None:
        ruta = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de salida",
            str(self._ruta_salida),
        )
        if not ruta:
            return
        self._ruta_salida = Path(ruta)
        self._entrada_ruta.setText(str(self._ruta_salida))
        self._actualizar_estado_exportar()

    def _exportar(self) -> None:
        if not self._resultado_es_exportable(self._resultado_carga):
            mensaje = MensajesInterfaz.ERROR_SIN_DATOS_EXPORTAR
            self._mostrar_resultado_exportacion(mensaje, exito=False)
            self.estado_actualizado.emit(MensajesInterfaz.ERROR_EXPORTACION)
            QMessageBox.warning(self, "Exportacion no disponible", mensaje)
            return

        if self._cantidad_salidas_seleccionadas() == 0:
            mensaje = "Seleccione al menos una salida para generar el archivo."
            self._mostrar_resultado_exportacion(mensaje, exito=False)
            self.estado_actualizado.emit(MensajesInterfaz.ERROR_EXPORTACION)
            QMessageBox.warning(self, "Exportacion no disponible", mensaje)
            return

        if self._worker_exportacion is not None:
            QMessageBox.information(
                self,
                "Exportacion en curso",
                "Ya hay una exportacion en proceso. Espere a que termine.",
            )
            return

        resultado_carga = self._resultado_carga
        assert resultado_carga is not None
        assert resultado_carga.dataframe is not None
        assert resultado_carga.dataframe_procesado is not None

        # UI: deshabilitar boton y mostrar progreso
        self._boton_exportar.setEnabled(False)
        self._boton_exportar.setText("Exportando...")
        self._barra_progreso.setValue(0)
        self._barra_progreso.setVisible(True)
        self._lbl_progreso.setVisible(True)
        self._lbl_progreso.setText("Iniciando exportacion...")
        self.estado_actualizado.emit("Generando archivo Excel de salida...")

        # Lanzar worker en QThreadPool para no bloquear la UI
        worker = WorkerExportacion(
            exportador=self._exportador,
            dataframe_original=resultado_carga.dataframe,
            dataframe_procesado=resultado_carga.dataframe_procesado,
            ruta_salida=self._ruta_salida,
            nombre_base_archivo=self._nombre_base_archivo(),
            hojas_seleccionadas=self._hojas_seleccionadas(),
            reclasificar_antes_exportar=self._check_reclasificar.isChecked(),
        )
        worker.senales.progreso.connect(self._al_progreso_exportacion)
        worker.senales.finalizado.connect(self._al_finalizar_exportacion)
        worker.senales.error.connect(self._al_error_exportacion)
        worker.senales.cancelado.connect(self._al_cancelar_exportacion)
        self._worker_exportacion = worker
        QThreadPool.globalInstance().start(worker)

    def _al_progreso_exportacion(self, porcentaje: int, mensaje: str) -> None:
        self._barra_progreso.setValue(int(porcentaje))
        self._lbl_progreso.setText(mensaje)

    def _al_finalizar_exportacion(self, resultado: ResultadoExportacion) -> None:
        self._worker_exportacion = None
        self._barra_progreso.setVisible(False)
        self._lbl_progreso.setVisible(False)
        self._resultado_exportacion = resultado
        self._mostrar_resultado_exportacion(resultado.mensaje, resultado.exito)
        self.exportacion_completada.emit(resultado)
        self._cargar_historial()
        self._actualizar_estado_exportar()

    def _al_error_exportacion(self, mensaje: str) -> None:
        self._worker_exportacion = None
        self._barra_progreso.setVisible(False)
        self._lbl_progreso.setVisible(False)
        self._logger.error("Fallo inesperado exportando desde la vista: %s", mensaje)
        resultado = ResultadoExportacion(exito=False, mensaje=mensaje)
        self._resultado_exportacion = resultado
        self._mostrar_resultado_exportacion(mensaje, exito=False)
        self.exportacion_completada.emit(resultado)
        self._actualizar_estado_exportar()

    def _al_cancelar_exportacion(self) -> None:
        self._worker_exportacion = None
        self._barra_progreso.setVisible(False)
        self._lbl_progreso.setVisible(False)
        self._actualizar_estado_exportar()
        self.estado_actualizado.emit("Exportacion cancelada.")

    def _abrir_archivo_exportado(self) -> None:
        ruta = self._ruta_exportada()
        if ruta is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))

    def _abrir_carpeta_exportada(self) -> None:
        ruta = self._ruta_exportada()
        carpeta = ruta.parent if ruta else self._ruta_salida
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(carpeta)))

    # ------------------------------------------------------------------
    # Estado visual
    # ------------------------------------------------------------------

    def _actualizar_resumen(self) -> None:
        resultado = self._resultado_carga
        preclasificacion = resultado.resultado_preclasificacion if resultado else None

        total = resultado.cantidad_filas if resultado else 0
        clasificados = preclasificacion.cantidad_clasificados if preclasificacion else 0
        sin_clasificar = preclasificacion.cantidad_sin_clasificar if preclasificacion else 0
        farmacias = len(preclasificacion.farmacias_detectadas) if preclasificacion else 0

        if total and not preclasificacion:
            dataframe = resultado.dataframe_procesado if resultado else None
            if dataframe is not None and "TIPOLOGIA_PRELIMINAR" in dataframe.columns:
                sin_clasificar = int((dataframe["TIPOLOGIA_PRELIMINAR"].fillna("") == "SIN_CLASIFICAR").sum())
                clasificados = max(total - sin_clasificar, 0)
            else:
                clasificados = total

        self._kpi_total.actualizar(self._formato_numero(total), descripcion="Listos para exportar")
        self._kpi_clasificados.actualizar(
            self._formato_numero(clasificados),
            descripcion=f"{self._porcentaje(clasificados, total)} del total",
            estilo_valor="valorMetricaCorrecto",
        )
        self._kpi_sin_clasificar.actualizar(
            self._formato_numero(sin_clasificar),
            descripcion=f"{self._porcentaje(sin_clasificar, total)} del total",
            estilo_valor="valorMetricaAdvertencia" if sin_clasificar else "valorMetrica",
        )
        self._kpi_farmacias.actualizar(
            self._formato_numero(farmacias),
            descripcion="Unicas en el archivo",
        )

        exportable = self._resultado_es_exportable(resultado)
        if exportable:
            self._lbl_icono_estado.setObjectName("iconoEstadoCorrecto")
            self._lbl_icono_estado.setText("OK")
            self._lbl_estado_titulo.setObjectName("mensajeEstado")
            self._lbl_estado_titulo.setText("Preclasificacion completada")
            self._lbl_estado_subtitulo.setText("El archivo esta listo para exportar en formato Excel.")
        elif resultado:
            self._lbl_icono_estado.setObjectName("iconoEstadoAdvertencia")
            self._lbl_icono_estado.setText("REV")
            self._lbl_estado_titulo.setObjectName("mensajeEstadoAdvertencia")
            self._lbl_estado_titulo.setText("Exportacion pendiente")
            self._lbl_estado_subtitulo.setText("Complete la carga y validacion antes de generar la salida.")
        else:
            self._lbl_icono_estado.setObjectName("iconoEstadoNeutro")
            self._lbl_icono_estado.setText("ND")
            self._lbl_estado_titulo.setObjectName("mensajeEstadoNeutro")
            self._lbl_estado_titulo.setText("Sin archivo para exportar")
            self._lbl_estado_subtitulo.setText("Cargue y valide un archivo antes de generar la salida Excel.")

        self._lbl_icono_estado.style().unpolish(self._lbl_icono_estado)
        self._lbl_icono_estado.style().polish(self._lbl_icono_estado)
        self._lbl_estado_titulo.style().unpolish(self._lbl_estado_titulo)
        self._lbl_estado_titulo.style().polish(self._lbl_estado_titulo)

    def _actualizar_resumen_salidas(self) -> None:
        seleccionadas = self._cantidad_salidas_seleccionadas()
        total = len(self._checks_salida)
        self._lbl_salida_resumen.setText(f"{seleccionadas} de {total} salidas seleccionadas")
        self._lbl_salida_resumen.setObjectName(
            "mensajeEstado" if seleccionadas else "mensajeEstadoAdvertencia"
        )
        self._lbl_salida_resumen.style().unpolish(self._lbl_salida_resumen)
        self._lbl_salida_resumen.style().polish(self._lbl_salida_resumen)
        self._actualizar_estado_exportar()

    def _actualizar_estado_exportar(self) -> None:
        habilitado = (
            self._resultado_es_exportable(self._resultado_carga)
            and self._cantidad_salidas_seleccionadas() > 0
            and bool(self._nombre_base_archivo())
        )
        self._boton_exportar.setEnabled(habilitado)
        self._boton_exportar.setText("Exportar Excel")

    def _mostrar_resultado_exportacion(self, mensaje: str, exito: bool) -> None:
        self._barra_resultado.setVisible(True)
        if exito:
            self._barra_resultado.setObjectName("barraResultadoExito")
            self._lbl_resultado_icono.setText("OK")
            self._lbl_resultado_icono.setObjectName("iconoEstadoCorrecto")
            self._lbl_resultado_titulo.setText("Exportacion completada correctamente")
            self._lbl_resultado_titulo.setObjectName("mensajeEstado")
            self._lbl_resultado_detalle.setText(self._detalle_exportacion_exitosa(mensaje))
            self._boton_abrir_archivo.setEnabled(self._ruta_exportada() is not None)
            self._boton_abrir_carpeta.setEnabled(True)
        else:
            self._barra_resultado.setObjectName("barraResultadoError")
            self._lbl_resultado_icono.setText("ERR")
            self._lbl_resultado_icono.setObjectName("iconoEstadoError")
            self._lbl_resultado_titulo.setText("No fue posible exportar")
            self._lbl_resultado_titulo.setObjectName("mensajeEstadoError")
            self._lbl_resultado_detalle.setText(mensaje)
            self._boton_abrir_archivo.setEnabled(False)
            self._boton_abrir_carpeta.setEnabled(False)

        for widget in (self._barra_resultado, self._lbl_resultado_icono, self._lbl_resultado_titulo):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self._animar_entrada(self._barra_resultado)

    def _ocultar_barra_resultado(self) -> None:
        if hasattr(self, "_barra_resultado"):
            self._barra_resultado.setVisible(False)

    def _actualizar_nombre_sugerido(self) -> None:
        resultado = self._resultado_carga
        if not resultado or not resultado.nombre_archivo:
            self._entrada_nombre.setText("resultado.xlsx")
            return
        base = limpiar_nombre_archivo(resultado.nombre_archivo)
        self._entrada_nombre.setText(f"{base}.xlsx")

    # ------------------------------------------------------------------
    # Historial
    # ------------------------------------------------------------------

    def _cargar_historial(self) -> None:
        try:
            with sesion_scope() as sesion:
                servicio = ServicioEjecuciones(sesion)
                ejecuciones = servicio.listar_recientes(limite=5)
        except ErrorDominio as error:
            self._logger.warning("No fue posible leer el historial de exportacion: %s", error)
            ejecuciones = []
        except Exception as error:  # noqa: BLE001
            self._logger.warning("Historial no disponible: %s", error)
            ejecuciones = []

        self._tabla_historial.setRowCount(0)
        if not ejecuciones:
            self._tabla_historial.setRowCount(1)
            self._tabla_historial.setSpan(0, 0, 1, 6)
            item = QTableWidgetItem("Aun no hay exportaciones registradas.")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(Qt.gray)
            self._tabla_historial.setItem(0, 0, item)
            return

        for fila, ejecucion in enumerate(ejecuciones):
            self._tabla_historial.insertRow(fila)
            fecha = ejecucion.fecha_fin or ejecucion.fecha_inicio
            valores = (
                fecha.strftime("%d/%m/%Y %H:%M"),
                ejecucion.archivo_nombre,
                self._formato_numero(ejecucion.total_registros),
                self._formato_numero(ejecucion.total_clasificados),
                self._formato_numero(ejecucion.total_sin_clasificar),
            )
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setTextAlignment(Qt.AlignCenter if columna != 1 else Qt.AlignVCenter | Qt.AlignLeft)
                self._tabla_historial.setItem(fila, columna, item)
            self._tabla_historial.setCellWidget(
                fila,
                5,
                self._badge_estado(ejecucion.estado),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resultado_es_exportable(self, resultado: ResultadoCarga | None) -> bool:
        return bool(
            resultado
            and resultado.exito
            and resultado.estructura_valida
            and resultado.dataframe is not None
            and resultado.dataframe_procesado is not None
            and not resultado.dataframe_procesado.empty
        )

    def _cantidad_salidas_seleccionadas(self) -> int:
        return sum(1 for check in self._checks_salida if check.isChecked())

    def _hojas_seleccionadas(self) -> set[str]:
        return {
            clave
            for check, (clave, _, _) in zip(self._checks_salida, _SALIDAS_EXPORTACION, strict=False)
            if check.isChecked()
        }

    def _nombre_base_archivo(self) -> str:
        return limpiar_nombre_archivo(self._entrada_nombre.text())

    def _ruta_exportada(self) -> Path | None:
        if not self._resultado_exportacion or not self._resultado_exportacion.ruta_salida:
            return None
        ruta = Path(self._resultado_exportacion.ruta_salida)
        return ruta if ruta.exists() else None

    def _detalle_exportacion_exitosa(self, mensaje: str) -> str:
        resultado = self._resultado_exportacion
        if not resultado:
            return mensaje
        hojas = ", ".join(resultado.hojas_generadas) if resultado.hojas_generadas else "hojas estandar"
        archivo = resultado.nombre_archivo or Path(resultado.ruta_salida or "").name
        return f"{archivo} generado con {len(resultado.hojas_generadas)} hojas: {hojas}."

    @staticmethod
    def _formato_numero(valor: int | float | None) -> str:
        numero = int(valor or 0)
        return f"{numero:,}".replace(",", ".")

    @staticmethod
    def _porcentaje(parte: int, total: int) -> str:
        if total <= 0:
            return "0,00%"
        return f"{(parte / total) * 100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _lbl(texto: str, objeto: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setObjectName(objeto)
        return etiqueta

    @staticmethod
    def _divisor_vertical() -> QFrame:
        divisor = QFrame()
        divisor.setObjectName("divisorVertical")
        divisor.setFixedHeight(58)
        return divisor

    @staticmethod
    def _badge_estado(estado: str) -> QWidget:
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        badge = QLabel(estado.title())
        objeto = {
            "EXPORTADA": "insigniaCorrecta",
            "CLASIFICADA": "insigniaInfo",
            "VALIDADA": "insigniaInfo",
            "ERROR": "insigniaError",
            "CANCELADA": "insigniaAdvertencia",
        }.get(estado, "insigniaNeutra")
        badge.setObjectName(objeto)
        badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(badge)
        return contenedor

    def _animar_entrada(self, widget: QWidget) -> None:
        efecto = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(efecto)
        animacion = QPropertyAnimation(efecto, b"opacity", self)
        animacion.setDuration(220)
        animacion.setStartValue(0.35)
        animacion.setEndValue(1.0)
        animacion.setEasingCurve(QEasingCurve.OutCubic)
        animacion.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._animaciones.append(animacion)
        animacion.start()
