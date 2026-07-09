"""Vista del historial de ejecuciones y exportaciones."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from interfaz.componentes.tarjeta_metrica import TarjetaMetrica
from persistencia.conexion import sesion_scope
from servicios.servicio_clinicas import ServicioClinicas
from servicios.servicio_ejecuciones import ServicioEjecuciones


class VistaHistorial(QWidget):
    """Historial operativo de cargas, clasificaciones y exportaciones."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._ejecuciones = []
        self._clinicas_por_id: dict[int, str] = {}
        self._construir_ui()
        self.recargar()

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorVista")
        layout_c = QVBoxLayout(contenedor)
        layout_c.setContentsMargins(24, 24, 24, 24)
        layout_c.setSpacing(16)

        layout_c.addWidget(self._crear_titulo())
        layout_c.addLayout(self._crear_metricas())
        layout_c.addWidget(self._crear_filtros())
        layout_c.addWidget(self._crear_tabla(), 1)

        scroll.setWidget(contenedor)
        layout.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)
        titulo = QLabel("Historial")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel("Registro de archivos cargados, clasificados y exportados.")
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        return card

    def _crear_metricas(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(14)
        self._tm_total = TarjetaMetrica("Ejecuciones totales", "0")
        self._tm_exportadas = TarjetaMetrica("Exportaciones", "0")
        self._tm_errores = TarjetaMetrica("Con errores", "0")
        self._tm_sin_clasificar = TarjetaMetrica("Sin clasificar acum.", "0")
        for tarjeta in (self._tm_total, self._tm_exportadas, self._tm_errores, self._tm_sin_clasificar):
            fila.addWidget(tarjeta)
        return fila

    def _crear_filtros(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(10)

        self._combo_estado = ComboScrollSafe()
        self._combo_estado.addItem("Todos los estados", None)
        for estado in ("CLASIFICADA", "EXPORTADA", "VALIDADA", "ERROR", "CANCELADA"):
            self._combo_estado.addItem(estado.title(), estado)
        self._combo_estado.currentIndexChanged.connect(self._actualizar_tabla)

        self._buscador = QLineEdit()
        self._buscador.setPlaceholderText("Buscar por archivo, clinica o mensaje")
        self._buscador.textChanged.connect(self._actualizar_tabla)

        btn_limpiar = QPushButton("Limpiar")
        btn_limpiar.setObjectName("botonTerciario")
        btn_limpiar.setMinimumHeight(38)
        btn_limpiar.clicked.connect(self._limpiar_filtros)

        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.setObjectName("botonSecundario")
        btn_actualizar.setMinimumHeight(38)
        btn_actualizar.clicked.connect(self.recargar)

        layout.addWidget(QLabel("Filtros:"))
        layout.addWidget(self._combo_estado)
        layout.addWidget(self._buscador, 1)
        layout.addWidget(btn_limpiar)
        layout.addWidget(btn_actualizar)
        return card

    def _crear_tabla(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        cab = QHBoxLayout()
        titulo = QLabel("Procesos y exportaciones")
        titulo.setObjectName("tituloSubpanel")
        cab.addWidget(titulo)
        cab.addStretch(1)
        layout.addLayout(cab)

        self._tabla = QTableWidget(0, 10)
        self._tabla.setHorizontalHeaderLabels(
            [
                "FECHA",
                "ARCHIVO",
                "CLINICA",
                "TOTAL",
                "CLASIFICADOS",
                "SIN CLASIFICAR",
                "ESTADO",
                "RUTA EXPORTADA",
                "DURACION",
                "MENSAJE / OBSERVACION",
            ]
        )
        encabezado = self._tabla.horizontalHeader()
        for columna in (0, 3, 4, 5, 6, 8):
            encabezado.setSectionResizeMode(columna, QHeaderView.ResizeToContents)
        for columna in (1, 2, 7, 9):
            encabezado.setSectionResizeMode(columna, QHeaderView.Stretch)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.itemDoubleClicked.connect(self._mostrar_detalle)
        self._tabla.setMinimumHeight(360)
        layout.addWidget(self._tabla)
        return card

    def recargar(self) -> None:
        try:
            with sesion_scope() as sesion:
                self._ejecuciones = ServicioEjecuciones(sesion).listar_ejecuciones()
                self._clinicas_por_id = {
                    clinica.id: clinica.nombre
                    for clinica in ServicioClinicas(sesion).listar_clinicas(activa=None)
                }
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar historial: %s", error)
            self._ejecuciones = []
            self._clinicas_por_id = {}
        self._actualizar_metricas()
        self._actualizar_tabla()

    def _actualizar_metricas(self) -> None:
        total = len(self._ejecuciones)
        exportadas = sum(1 for ejecucion in self._ejecuciones if ejecucion.estado == "EXPORTADA")
        errores = sum(1 for ejecucion in self._ejecuciones if ejecucion.estado == "ERROR")
        sin_clasificar = sum(int(ejecucion.total_sin_clasificar or 0) for ejecucion in self._ejecuciones)
        self._tm_total.actualizar(str(total))
        self._tm_exportadas.actualizar(str(exportadas))
        self._tm_errores.actualizar(str(errores))
        self._tm_sin_clasificar.actualizar(self._formatear(sin_clasificar))

    def _actualizar_tabla(self, *_args) -> None:
        estado = self._combo_estado.currentData()
        texto = self._buscador.text().strip().lower()
        filas = []
        for ejecucion in self._ejecuciones:
            clinica = self._clinicas_por_id.get(ejecucion.clinica_id or -1, "")
            contenido = f"{ejecucion.archivo_nombre} {clinica} {ejecucion.mensaje or ''}".lower()
            if estado and ejecucion.estado != estado:
                continue
            if texto and texto not in contenido:
                continue
            filas.append(ejecucion)

        self._tabla.setRowCount(len(filas))
        for fila, ejecucion in enumerate(filas):
            fecha = ejecucion.fecha_inicio.strftime("%Y-%m-%d %H:%M") if ejecucion.fecha_inicio else "-"
            ruta = ejecucion.archivo_ruta or "No registrada"
            duracion = f"{ejecucion.duracion_segundos:.2f} s" if ejecucion.duracion_segundos is not None else "-"
            valores = [
                fecha,
                ejecucion.archivo_nombre,
                self._clinicas_por_id.get(ejecucion.clinica_id or -1, "-"),
                self._formatear(ejecucion.total_registros),
                self._formatear(ejecucion.total_clasificados),
                self._formatear(ejecucion.total_sin_clasificar),
                ejecucion.estado,
                ruta,
                duracion,
                ejecucion.mensaje or "",
            ]
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setToolTip(str(valor))
                item.setData(Qt.UserRole, ejecucion.id)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter if columna in (3, 4, 5) else Qt.AlignVCenter)
                self._tabla.setItem(fila, columna, item)

    def _limpiar_filtros(self) -> None:
        self._combo_estado.setCurrentIndex(0)
        self._buscador.clear()

    def _mostrar_detalle(self, item: QTableWidgetItem) -> None:
        ejecucion_id = item.data(Qt.UserRole)
        ejecucion = next((e for e in self._ejecuciones if e.id == ejecucion_id), None)
        if ejecucion is None:
            return
        clinica = self._clinicas_por_id.get(ejecucion.clinica_id or -1, "-")
        fecha = ejecucion.fecha_inicio.strftime("%Y-%m-%d %H:%M:%S") if ejecucion.fecha_inicio else "-"
        QMessageBox.information(
            self,
            f"Resumen del proceso #{ejecucion.id}",
            (
                f"Archivo procesado: {ejecucion.archivo_nombre}\n"
                f"Fecha: {fecha}\n"
                f"Clinica: {clinica}\n"
                f"Total registros: {ejecucion.total_registros}\n"
                f"Total clasificados: {ejecucion.total_clasificados}\n"
                f"Total sin clasificar: {ejecucion.total_sin_clasificar}\n"
                "Tipologias detectadas: disponible en archivo exportado\n"
                "Farmacias detectadas: disponible en resumen de carga\n"
                f"Exportacion generada: {'Si' if ejecucion.estado == 'EXPORTADA' else 'No'}\n"
                f"Ruta del archivo: {ejecucion.archivo_ruta or 'No registrada'}\n"
                f"Estado final: {ejecucion.estado}\n\n"
                f"Mensaje: {ejecucion.mensaje or '-'}"
            ),
        )

    @staticmethod
    def _formatear(valor: int | None) -> str:
        return f"{int(valor or 0):,}".replace(",", ".")
