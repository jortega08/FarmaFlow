"""Worker Qt para exportacion de Excel en segundo plano.

Mover la exportacion a un hilo es critico para archivos grandes (>50k filas):
de lo contrario la UI se congela durante segundos o minutos y Windows marca
la app como "no responde".
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import QObject, QRunnable, Signal

from logica.exportador_excel import ExportadorExcel
from logica.generador_resumen import generar_estructuras_exportacion
from modelos.resultado_exportacion import ResultadoExportacion
from persistencia.conexion import sesion_scope
from reglas.motor_reglas_avanzado import MotorReglasAvanzado
from servicios.servicio_listas import ServicioListas
from servicios.servicio_reglas import obtener_contexto_motor, obtener_reglas_motor_avanzado
from utilidades.mensajes import MensajesInterfaz


class _SenalesExportacion(QObject):
    """Senales del worker (un QRunnable no puede emitir senales por si solo)."""

    progreso = Signal(int, str)        # (porcentaje, mensaje)
    finalizado = Signal(object)         # ResultadoExportacion
    error = Signal(str)
    cancelado = Signal()


class WorkerExportacion(QRunnable):
    """Genera el archivo Excel de salida en un hilo de QThreadPool.

    Las estructuras (detalle_clasificado, resumenes, cruce, sin_clasificar) se
    construyen dentro del hilo para no bloquear la UI durante el ``pivot_table``
    ni durante la escritura del Excel.

    Uso tipico::

        worker = WorkerExportacion(
            exportador, dataframe_original, dataframe_procesado,
            ruta_salida, nombre_base, hojas_seleccionadas,
        )
        worker.senales.progreso.connect(...)
        worker.senales.finalizado.connect(...)
        worker.senales.error.connect(...)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(
        self,
        exportador: ExportadorExcel,
        dataframe_original: pd.DataFrame,
        dataframe_procesado: pd.DataFrame,
        ruta_salida: Path | str,
        nombre_base_archivo: str,
        hojas_seleccionadas: set[str] | None = None,
        reclasificar_antes_exportar: bool = True,
    ) -> None:
        super().__init__()
        self.senales = _SenalesExportacion()
        self._exportador = exportador
        self._dataframe_original = dataframe_original
        self._dataframe_procesado = dataframe_procesado
        self._ruta_salida = ruta_salida
        self._nombre_base = nombre_base_archivo
        self._hojas_seleccionadas = hojas_seleccionadas
        self._reclasificar_antes_exportar = reclasificar_antes_exportar
        self._cancelar = False
        self.setAutoDelete(True)

    def solicitar_cancelacion(self) -> None:
        """Marca la exportacion para detenerse en el proximo punto seguro."""
        self._cancelar = True

    def run(self) -> None:  # type: ignore[override]
        """Construye estructuras y exporta. Emite senales segun el resultado."""
        try:
            self.senales.progreso.emit(0, "Preparando reglas vigentes...")
            if self._cancelar:
                self.senales.cancelado.emit()
                return

            dataframe_procesado = self._dataframe_procesado
            if self._reclasificar_antes_exportar:
                self.senales.progreso.emit(5, "Aplicando reglas actualizadas antes de exportar...")
                dataframe_procesado = self._reclasificar_con_reglas_vigentes(dataframe_procesado)

            if self._cancelar:
                self.senales.cancelado.emit()
                return

            self.senales.progreso.emit(15, "Preparando estructuras de salida...")
            estructuras = generar_estructuras_exportacion(
                dataframe_original=self._dataframe_original,
                dataframe_procesado=dataframe_procesado,
                listas_articulos=self._cargar_listas_articulos_reservadas(),
            )

            if self._cancelar:
                self.senales.cancelado.emit()
                return

            resultado = self._exportador.exportar(
                dataframe_original=self._dataframe_original,
                detalle_clasificado=estructuras["detalle_clasificado"],
                resumen_tipologia=estructuras["resumen_tipologia"],
                resumen_farmacia=estructuras["resumen_farmacia"],
                cruce_tipologia_farmacia=estructuras["cruce_tipologia_farmacia"],
                sin_clasificar=estructuras["sin_clasificar"],
                ruta_salida=self._ruta_salida,
                nombre_base_archivo=self._nombre_base,
                hojas_seleccionadas=self._hojas_seleccionadas,
                liquidos=estructuras.get("liquidos"),
                mce_cirugia=estructuras.get("mce_cirugia"),
                progreso_callback=lambda p, m: self.senales.progreso.emit(p, m),
                cancelado_callback=lambda: self._cancelar,
            )
        except Exception as exc:  # noqa: BLE001
            self.senales.error.emit(f"{MensajesInterfaz.ERROR_EXPORTACION}: {exc}")
            return

        if self._cancelar:
            self.senales.cancelado.emit()
        else:
            self.senales.finalizado.emit(resultado)

    @staticmethod
    def _cargar_listas_articulos_reservadas() -> dict[str, list[str]]:
        listas: dict[str, list[str]] = {"LIQUIDOS": [], "MCE_CIRUGIA": []}
        try:
            with sesion_scope() as sesion:
                servicio = ServicioListas(sesion)
                for codigo in listas:
                    listas[codigo] = [item.valor for item in servicio.listar_items_por_codigo(codigo, activos=True)]
        except Exception:  # noqa: BLE001
            return listas
        return listas

    def _reclasificar_con_reglas_vigentes(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Reaplica las reglas activas para que la exportacion no use una foto vieja."""
        reglas = obtener_reglas_motor_avanzado()
        if not reglas:
            self.senales.progreso.emit(
                10,
                "No se encontraron reglas activas nuevas; se conserva la clasificacion actual.",
            )
            return dataframe

        contexto = obtener_contexto_motor()
        motor = MotorReglasAvanzado(
            proveedor_reglas=lambda: reglas,
            proveedor_contexto=lambda: contexto,
        )
        resultado = motor.clasificar(dataframe)
        return resultado.dataframe_resultado
