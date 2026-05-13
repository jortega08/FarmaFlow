"""Ventana principal de la aplicacion."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from dto.ejecucion_dto import EjecucionCrearDTO, EjecucionFinalizarDTO
from interfaz.branding import NOMBRE_APP, RUTA_ICONO_APP, RUTA_ICONO_APP_ICO
from interfaz.componentes.barra_estado import BarraEstado
from interfaz.componentes.dialogo_guardar_clinica import (
    DialogoGuardarClinica,
    extraer_farmacias_org_destino,
)
from interfaz.componentes.sidebar_navegacion import SidebarNavegacion
from interfaz.vistas.vista_carga_archivo import VistaCargaArchivo
from interfaz.vistas.vista_catalogos import VistaCatalogos
from interfaz.vistas.vista_clinica_farmacias import VistaClinicaFarmacias
from interfaz.vistas.vista_clinicas import VistaClinicas
from interfaz.vistas.vista_exportacion import VistaExportacion
from interfaz.vistas.vista_historial import VistaHistorial
from interfaz.vistas.vista_reglas_clasificacion import VistaReglasClasificacion
from interfaz.vistas.vista_resultado_preclasificacion import VistaResultadoPreclasificacion
from interfaz.workers.worker_exportacion import WorkerExportacion
from logica.exportador_excel import ExportadorExcel
from modelos.resultado_carga import ResultadoCarga
from persistencia.conexion import sesion_scope
from servicios.excepciones import ErrorDominio
from servicios.fabrica_procesamiento import crear_lector_excel_con_fallback
from servicios.servicio_autenticacion import UsuarioSesion
from servicios.servicio_clinicas import ServicioClinicas
from servicios.servicio_ejecuciones import ServicioEjecuciones
from utilidades.mensajes import MensajesInterfaz
from utilidades.rutas import obtener_ruta_salidas

_ORDEN_PANTALLAS: tuple[str, ...] = (
    "carga",
    "clinica",
    "reglas",
    "resultado",
    "exportar",
    "clinicas",
    "catalogos",
    "historial",
)

# Pantallas que forman el flujo principal (1 -> 5). Catalogos e historial estan fuera.
_FLUJO_PRINCIPAL: tuple[str, ...] = (
    "carga",
    "clinica",
    "reglas",
    "resultado",
    "exportar",
)

# Titulo y subtitulo mostrados en el header global por pantalla.
_INFO_PANTALLA: dict[str, tuple[str, str]] = {
    "carga": (
        "Paso 1 - Carga de archivo",
        "Suba el Excel con los movimientos a procesar.",
    ),
    "clinica": (
        "Paso 2 - Clinica y farmacias",
        "Seleccione la clinica y revise las farmacias detectadas en el archivo.",
    ),
    "reglas": (
        "Paso 3 - Reglas de clasificacion",
        "Revise o cree reglas para asignar tipologias a los movimientos.",
    ),
    "resultado": (
        "Paso 4 - Resultado de la preclasificacion",
        "Inspeccione el resultado y filtre los movimientos clasificados.",
    ),
    "exportar": (
        "Paso 5 - Exportacion",
        "Genere el archivo Excel final con las hojas seleccionadas.",
    ),
    "clinicas": (
        "Clinicas",
        "Dashboard con resumen e historial de exportaciones por clinica.",
    ),
    "catalogos": (
        "Catalogos",
        "Articulos, tipologias y farmacias mantenidos por el sistema.",
    ),
    "historial": (
        "Historial",
        "Ejecuciones anteriores y su estado.",
    ),
}


class VentanaPrincipal(QMainWindow):
    """Contenedor principal de la aplicacion con navegacion lateral."""

    def __init__(
        self,
        configuracion: dict[str, Any],
        usuario_sesion: UsuarioSesion | None = None,
    ) -> None:
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._configuracion = configuracion
        self._usuario_sesion = usuario_sesion
        self._resultado_carga_actual: ResultadoCarga | None = None
        self._ejecucion_actual_id: int | None = None
        self._exportador_excel = ExportadorExcel()
        self._worker_exportacion_rapida: WorkerExportacion | None = None

        self.setWindowTitle(NOMBRE_APP)
        if RUTA_ICONO_APP_ICO.exists():
            self.setWindowIcon(QIcon(str(RUTA_ICONO_APP_ICO)))
        self.resize(configuracion["ancho_ventana"], configuracion["alto_ventana"])
        self.setMinimumSize(1100, 700)

        self._barra_estado = BarraEstado()
        lector_excel = crear_lector_excel_con_fallback(configuracion)
        self._vista_carga = VistaCargaArchivo(
            configuracion=configuracion, lector_excel=lector_excel
        )
        self._vista_clinica = VistaClinicaFarmacias()
        self._vista_reglas = VistaReglasClasificacion(dataframe_provider=self.dataframe_actual)
        self._vista_resultado = VistaResultadoPreclasificacion()
        self._vista_exportacion = VistaExportacion(configuracion=configuracion)
        self._indices: dict[str, int] = {
            clave: i for i, clave in enumerate(_ORDEN_PANTALLAS)
        }

        self._configurar_interfaz()
        self._conectar_eventos()
        self._sidebar.activar_pantalla("carga")
        self._actualizar_header_y_footer("carga")

    # ------------------------------------------------------------------
    # Construccion de la interfaz
    # ------------------------------------------------------------------

    def _configurar_interfaz(self) -> None:
        widget_raiz = QWidget(self)
        widget_raiz.setObjectName("panelDerecho")

        disposicion_raiz = QHBoxLayout(widget_raiz)
        disposicion_raiz.setContentsMargins(0, 0, 0, 0)
        disposicion_raiz.setSpacing(0)

        # --- Sidebar ---
        self._sidebar = SidebarNavegacion(NOMBRE_APP)
        disposicion_raiz.addWidget(self._sidebar)

        # --- Panel derecho ---
        panel_derecho = QFrame(widget_raiz)
        panel_derecho.setObjectName("panelDerecho")
        disposicion_derecha = QVBoxLayout(panel_derecho)
        disposicion_derecha.setContentsMargins(0, 0, 0, 0)
        disposicion_derecha.setSpacing(0)

        disposicion_derecha.addWidget(self._crear_header_global())

        # --- Stack de pantallas ---
        self._stack = QStackedWidget(panel_derecho)
        self._stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._vista_clinicas_dashboard = VistaClinicas()
        vistas: list[QWidget] = [
            self._vista_carga,
            self._vista_clinica,
            self._vista_reglas,
            self._vista_resultado,
            self._vista_exportacion,
            self._vista_clinicas_dashboard,
            VistaCatalogos(),
            VistaHistorial(),
        ]
        for vista in vistas:
            self._stack.addWidget(vista)

        disposicion_derecha.addWidget(self._stack, stretch=1)
        disposicion_derecha.addWidget(self._crear_footer_navegacion())
        disposicion_raiz.addWidget(panel_derecho, stretch=1)

        # --- Status bar ---
        barra_nativa = QStatusBar(self)
        barra_nativa.setSizeGripEnabled(False)
        barra_nativa.addPermanentWidget(self._barra_estado, 1)
        self.setStatusBar(barra_nativa)

        self.setCentralWidget(widget_raiz)

    def _crear_header_global(self) -> QFrame:
        header = QFrame()
        header.setObjectName("headerGlobal")
        header.setFixedHeight(74)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(14)

        icono = QLabel("FF")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(42, 42)
        icono.setAlignment(Qt.AlignCenter)
        if RUTA_ICONO_APP.exists():
            pixmap = QPixmap(str(RUTA_ICONO_APP))
            if not pixmap.isNull():
                icono.setText("")
                icono.setPixmap(
                    pixmap.scaled(
                        42,
                        42,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )

        textos = QVBoxLayout()
        textos.setSpacing(2)

        titulo_inicial, subtitulo_inicial = _INFO_PANTALLA["carga"]
        self._lbl_titulo_pantalla = QLabel(titulo_inicial)
        self._lbl_titulo_pantalla.setObjectName("appTitleGlobal")

        self._lbl_subtitulo_pantalla = QLabel(subtitulo_inicial)
        self._lbl_subtitulo_pantalla.setObjectName("appSubtitleGlobal")
        self._lbl_subtitulo_pantalla.setWordWrap(True)

        textos.addWidget(self._lbl_titulo_pantalla)
        textos.addWidget(self._lbl_subtitulo_pantalla)

        layout.addWidget(icono)
        layout.addLayout(textos, 1)
        return header

    def _crear_footer_navegacion(self) -> QFrame:
        """Crea la barra inferior con botones Anterior/Siguiente paso."""
        footer = QFrame()
        footer.setObjectName("footerNavegacion")
        footer.setFixedHeight(60)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(12)

        self._lbl_progreso_flujo = QLabel("Paso 1 de 5")
        self._lbl_progreso_flujo.setObjectName("textoSecundario")

        self._btn_anterior = QPushButton("< Paso anterior")
        self._btn_anterior.setObjectName("botonSecundario")
        self._btn_anterior.setMinimumHeight(38)
        self._btn_anterior.clicked.connect(self._ir_paso_anterior)

        self._btn_siguiente = QPushButton("Paso siguiente >")
        self._btn_siguiente.setObjectName("botonPrincipal")
        self._btn_siguiente.setMinimumHeight(38)
        self._btn_siguiente.clicked.connect(self._ir_paso_siguiente)

        layout.addWidget(self._lbl_progreso_flujo)
        layout.addStretch(1)
        layout.addWidget(self._btn_anterior)
        layout.addWidget(self._btn_siguiente)
        return footer

    def _actualizar_header_y_footer(self, clave: str) -> None:
        titulo, subtitulo = _INFO_PANTALLA.get(
            clave, (clave.capitalize(), "")
        )
        if hasattr(self, "_lbl_titulo_pantalla"):
            self._lbl_titulo_pantalla.setText(titulo)
            self._lbl_subtitulo_pantalla.setText(subtitulo)

        if not hasattr(self, "_btn_anterior"):
            return
        if clave in _FLUJO_PRINCIPAL:
            indice = _FLUJO_PRINCIPAL.index(clave)
            total = len(_FLUJO_PRINCIPAL)
            self._lbl_progreso_flujo.setText(f"Paso {indice + 1} de {total}")
            self._btn_anterior.setEnabled(indice > 0)
            self._btn_siguiente.setEnabled(indice < total - 1)
            if indice < total - 1:
                clave_siguiente = _FLUJO_PRINCIPAL[indice + 1]
                etiqueta_siguiente = _INFO_PANTALLA.get(clave_siguiente, ("", ""))[0]
                self._btn_siguiente.setText(f"Siguiente: {etiqueta_siguiente.split(' - ', 1)[-1]} >")
            else:
                self._btn_siguiente.setText("Paso siguiente >")
            if indice > 0:
                clave_anterior = _FLUJO_PRINCIPAL[indice - 1]
                etiqueta_anterior = _INFO_PANTALLA.get(clave_anterior, ("", ""))[0]
                self._btn_anterior.setText(f"< {etiqueta_anterior.split(' - ', 1)[-1]}")
            else:
                self._btn_anterior.setText("< Paso anterior")
        else:
            self._lbl_progreso_flujo.setText(titulo)
            self._btn_anterior.setEnabled(False)
            self._btn_siguiente.setEnabled(False)
            self._btn_anterior.setText("< Paso anterior")
            self._btn_siguiente.setText("Paso siguiente >")

    def _ir_paso_anterior(self) -> None:
        actual = self._clave_actual()
        if actual in _FLUJO_PRINCIPAL:
            indice = _FLUJO_PRINCIPAL.index(actual)
            if indice > 0:
                self._navegar_a_pantalla(_FLUJO_PRINCIPAL[indice - 1])

    def _ir_paso_siguiente(self) -> None:
        actual = self._clave_actual()
        if actual in _FLUJO_PRINCIPAL:
            indice = _FLUJO_PRINCIPAL.index(actual)
            if indice < len(_FLUJO_PRINCIPAL) - 1:
                self._navegar_a_pantalla(_FLUJO_PRINCIPAL[indice + 1])

    def _clave_actual(self) -> str:
        indice = self._stack.currentIndex()
        for clave, idx in self._indices.items():
            if idx == indice:
                return clave
        return "carga"

    # ------------------------------------------------------------------
    # Navegacion
    # ------------------------------------------------------------------

    def _navegar_a_pantalla(self, clave: str) -> None:
        indice = self._indices.get(clave, 0)
        self._stack.setCurrentIndex(indice)
        self._sidebar.activar_pantalla(clave)
        self._actualizar_header_y_footer(clave)
        if clave == "clinicas" and hasattr(self, "_vista_clinicas_dashboard"):
            self._vista_clinicas_dashboard.recargar()

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _conectar_eventos(self) -> None:
        self._sidebar.pantalla_solicitada.connect(self._navegar_a_pantalla)
        self._vista_carga.archivo_cargado.connect(self._al_archivo_cargado)
        self._vista_carga.exportacion_solicitada.connect(self._exportar_resultado_actual)
        self._vista_carga.estado_actualizado.connect(self._actualizar_estado)
        self._vista_carga.vista_limpiada.connect(self._al_limpiar_carga)
        self._vista_exportacion.exportacion_completada.connect(
            self._al_exportacion_completada_desde_vista
        )
        self._vista_exportacion.estado_actualizado.connect(self._actualizar_estado)
        self._vista_exportacion.procesar_otro_archivo.connect(self._procesar_otro_archivo)

    def _al_archivo_cargado(self, resultado: ResultadoCarga) -> None:
        self._resultado_carga_actual = resultado
        self._vista_clinica.establecer_resultado_carga(resultado)
        self._vista_resultado.establecer_resultado_carga(resultado)
        self._vista_exportacion.establecer_resultado_carga(resultado)

        clinica_id = self._prompt_guardar_clinica(resultado) if resultado.estructura_valida else None
        if clinica_id is not None:
            self._refrescar_vistas_post_guardado_clinica()
        self._registrar_ejecucion_carga(resultado, clinica_id=clinica_id)
        self._vista_carga.establecer_exportacion_disponible(
            self._resultado_es_exportable(resultado)
        )
        self._actualizar_estado(
            MensajesInterfaz.ARCHIVO_CARGADO
            if resultado.estructura_valida
            else MensajesInterfaz.ESTRUCTURA_INVALIDA
        )
        self._logger.info("Archivo cargado: %s", resultado.nombre_archivo)

    def dataframe_actual(self):
        """Devuelve el DataFrame vigente para vistas que sugieren valores del archivo."""
        if self._resultado_carga_actual is None:
            return None
        if self._resultado_carga_actual.dataframe_procesado is not None:
            return self._resultado_carga_actual.dataframe_procesado
        return self._resultado_carga_actual.dataframe

    def _refrescar_vistas_post_guardado_clinica(self) -> None:
        if hasattr(self, "_vista_clinicas_dashboard"):
            self._vista_clinicas_dashboard.recargar()
        if hasattr(self, "_vista_clinica"):
            self._vista_clinica.recargar()
        if hasattr(self, "_vista_reglas"):
            self._vista_reglas.recargar_listas_farmacias()

    def _prompt_guardar_clinica(self, resultado: ResultadoCarga) -> int | None:
        """Pregunta al usuario si desea persistir farmacias detectadas y la clinica asociada."""
        dataframe_farmacias = resultado.dataframe_procesado if resultado.dataframe_procesado is not None else resultado.dataframe
        farmacias = extraer_farmacias_org_destino(dataframe_farmacias)
        if not farmacias:
            return None

        respuesta = QMessageBox.question(
            self,
            "Guardar datos en el sistema",
            (
                "Se cargo el archivo correctamente.\n\n"
                f"Detectamos {len(farmacias)} farmacias en la columna ORG_DESTINO. "
                "¿Desea guardar los datos de este archivo en el sistema y asociarlos a una clinica?\n\n"
                "Esto permitira ver el historial de exportaciones por clinica en el dashboard."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if respuesta != QMessageBox.Yes:
            return None

        try:
            with sesion_scope() as sesion:
                clinicas = ServicioClinicas(sesion).listar_clinicas(activa=True)
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible listar clinicas existentes: %s", error)
            clinicas = []

        dialogo = DialogoGuardarClinica(
            farmacias_detectadas=farmacias,
            clinicas_existentes=clinicas,
            parent=self,
        )
        if dialogo.exec() != dialogo.DialogCode.Accepted:
            return None

        resultado_dialogo = dialogo.resultado()
        if not resultado_dialogo.confirmado:
            return None

        QMessageBox.information(
            self,
            "Datos guardados",
            (
                f"Clinica \"{resultado_dialogo.clinica_nombre}\" asociada correctamente.\n"
                f"Farmacias asociadas en esta importacion: {resultado_dialogo.farmacias_asociadas}."
            ),
        )
        return resultado_dialogo.clinica_id

    def _al_limpiar_carga(self) -> None:
        self._resultado_carga_actual = None
        self._ejecucion_actual_id = None
        self._vista_clinica.limpiar_resultado()
        self._vista_resultado.limpiar_resultado()
        self._vista_exportacion.limpiar_resultado()
        self._vista_carga.establecer_exportacion_disponible(False)
        self._actualizar_estado(MensajesInterfaz.LISTO)

    def _actualizar_estado(self, mensaje: str) -> None:
        self._barra_estado.actualizar_mensaje(mensaje)
        self._vista_carga.actualizar_estado_flujo(mensaje)

    def _procesar_otro_archivo(self) -> None:
        self._vista_carga.limpiar()
        self._navegar_a_pantalla("carga")

    # ------------------------------------------------------------------
    # Exportacion
    # ------------------------------------------------------------------

    def _exportar_resultado_actual(self) -> None:
        """Exporta el resultado procesado en segundo plano (no bloquea la UI)."""
        if not self._resultado_es_exportable(self._resultado_carga_actual):
            mensaje = MensajesInterfaz.ERROR_SIN_DATOS_EXPORTAR
            self._vista_carga.mostrar_resultado_exportacion(mensaje, exito=False)
            self._actualizar_estado(MensajesInterfaz.ERROR_EXPORTACION)
            QMessageBox.warning(self, "Exportacion no disponible", mensaje)
            return

        if self._worker_exportacion_rapida is not None:
            QMessageBox.information(
                self,
                "Exportacion en curso",
                "Ya hay una exportacion en proceso. Espere a que termine.",
            )
            return

        resultado_carga = self._resultado_carga_actual
        assert resultado_carga is not None

        ruta_salidas = obtener_ruta_salidas(self._configuracion)
        worker = WorkerExportacion(
            exportador=self._exportador_excel,
            dataframe_original=resultado_carga.dataframe,
            dataframe_procesado=resultado_carga.dataframe_procesado,
            ruta_salida=ruta_salidas,
            nombre_base_archivo=resultado_carga.nombre_archivo,
        )
        worker.senales.progreso.connect(self._al_progreso_exportacion_rapida)
        worker.senales.finalizado.connect(self._al_finalizar_exportacion_rapida)
        worker.senales.error.connect(self._al_error_exportacion_rapida)
        self._worker_exportacion_rapida = worker
        self._actualizar_estado("Exportando archivo Excel en segundo plano...")
        QThreadPool.globalInstance().start(worker)

    def _al_progreso_exportacion_rapida(self, porcentaje: int, mensaje: str) -> None:
        self._actualizar_estado(f"Exportando ({porcentaje}%): {mensaje}")

    def _al_finalizar_exportacion_rapida(self, resultado_export: Any) -> None:
        self._worker_exportacion_rapida = None
        self._vista_carga.mostrar_resultado_exportacion(
            resultado_export.mensaje, exito=resultado_export.exito
        )
        self._vista_exportacion.recargar_historial()

        if resultado_export.exito:
            self._actualizar_ejecucion_exportacion("EXPORTADA", resultado_export.mensaje)
            self._actualizar_estado(MensajesInterfaz.EXPORTACION_EXITOSA)
            self._logger.info("Exportacion completada: %s", resultado_export.ruta_salida)
            QMessageBox.information(
                self,
                "Exportacion completada",
                f"El archivo se genero correctamente.\n\nRuta: {resultado_export.ruta_salida}",
            )
            return

        self._actualizar_ejecucion_exportacion("ERROR", resultado_export.mensaje)
        self._actualizar_estado(MensajesInterfaz.ERROR_EXPORTACION)
        self._logger.error("Exportacion fallida: %s", resultado_export.mensaje)
        QMessageBox.critical(self, "Error de exportacion", resultado_export.mensaje)

    def _al_error_exportacion_rapida(self, mensaje: str) -> None:
        self._worker_exportacion_rapida = None
        self._vista_carga.mostrar_resultado_exportacion(mensaje, exito=False)
        self._actualizar_ejecucion_exportacion("ERROR", mensaje)
        self._actualizar_estado(MensajesInterfaz.ERROR_EXPORTACION)
        self._logger.error("Exportacion fallida: %s", mensaje)
        QMessageBox.critical(self, "Error de exportacion", mensaje)

    def _al_exportacion_completada_desde_vista(self, resultado_export: Any) -> None:
        """Sincroniza estado global cuando la pantalla Exportar genera un archivo."""
        self._vista_carga.mostrar_resultado_exportacion(
            resultado_export.mensaje, exito=resultado_export.exito
        )
        if resultado_export.exito:
            self._actualizar_ejecucion_exportacion("EXPORTADA", resultado_export.mensaje)
            self._actualizar_estado(MensajesInterfaz.EXPORTACION_EXITOSA)
            self._logger.info("Exportacion completada: %s", resultado_export.ruta_salida)
            return

        self._actualizar_ejecucion_exportacion("ERROR", resultado_export.mensaje)
        self._actualizar_estado(MensajesInterfaz.ERROR_EXPORTACION)
        self._logger.error("Exportacion fallida: %s", resultado_export.mensaje)

    # ------------------------------------------------------------------
    # Persistencia
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

    def _registrar_ejecucion_carga(
        self, resultado: ResultadoCarga, clinica_id: int | None = None
    ) -> None:
        estado = "CLASIFICADA" if resultado.estructura_valida else "VALIDADA"
        cierre = self._crear_dto_cierre(resultado, estado=estado, mensaje=resultado.mensaje)
        inicio = EjecucionCrearDTO(
            archivo_nombre=resultado.nombre_archivo or "archivo",
            archivo_ruta=resultado.ruta_archivo or None,
            hoja=resultado.hoja_utilizada or None,
            clinica_id=clinica_id,
            mensaje="Carga iniciada desde la interfaz.",
        )
        try:
            with sesion_scope() as sesion:
                servicio = ServicioEjecuciones(sesion)
                ejecucion = servicio.registrar_ejecucion_completa(inicio, cierre)
                self._ejecucion_actual_id = ejecucion.id
        except ErrorDominio as error:
            self._ejecucion_actual_id = None
            self._logger.warning("No fue posible registrar la ejecucion: %s", error)
        except Exception as error:  # noqa: BLE001
            self._ejecucion_actual_id = None
            self._logger.exception("Fallo inesperado registrando la ejecucion: %s", error)

    def _actualizar_ejecucion_exportacion(self, estado: str, mensaje: str) -> None:
        if self._ejecucion_actual_id is None or self._resultado_carga_actual is None:
            return
        cierre = self._crear_dto_cierre(
            self._resultado_carga_actual, estado=estado, mensaje=mensaje
        )
        try:
            with sesion_scope() as sesion:
                servicio = ServicioEjecuciones(sesion)
                servicio.finalizar_ejecucion(self._ejecucion_actual_id, cierre)
        except ErrorDominio as error:
            self._logger.warning("No fue posible actualizar la ejecucion: %s", error)
        except Exception as error:  # noqa: BLE001
            self._logger.exception("Fallo inesperado actualizando la ejecucion: %s", error)

    def _crear_dto_cierre(
        self, resultado: ResultadoCarga, estado: str, mensaje: str
    ) -> EjecucionFinalizarDTO:
        preclasificacion = resultado.resultado_preclasificacion
        total_clasificados = preclasificacion.cantidad_clasificados if preclasificacion else 0
        total_sin_clasificar = (
            preclasificacion.cantidad_sin_clasificar
            if preclasificacion
            else max(resultado.cantidad_filas - total_clasificados, 0)
        )
        return EjecucionFinalizarDTO(
            estado=estado,
            total_registros=resultado.cantidad_filas,
            total_columnas=resultado.cantidad_columnas,
            total_clasificados=total_clasificados,
            total_sin_clasificar=total_sin_clasificar,
            mensaje=mensaje,
        )
