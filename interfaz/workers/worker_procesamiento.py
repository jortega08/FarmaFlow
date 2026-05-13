"""Worker Qt para procesamiento de archivos Excel en segundo plano."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal


class _SenalesWorker(QObject):
    """Contenedor de senales separado requerido por QRunnable (no hereda QObject)."""

    progreso = Signal(object)
    finalizado = Signal(object)
    error = Signal(str)
    cancelado = Signal()


class WorkerProcesamiento(QRunnable):
    """Ejecuta la carga de un archivo Excel en un hilo de QThreadPool.

    Uso tipico::

        worker = WorkerProcesamiento(lector_excel, Path(ruta))
        worker.senales.progreso.connect(manejador_progreso)
        worker.senales.finalizado.connect(manejador_resultado)
        worker.senales.error.connect(manejador_error)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, lector_excel: Any, ruta_archivo: Path) -> None:
        super().__init__()
        self.senales = _SenalesWorker()
        self._lector_excel = lector_excel
        self._ruta_archivo = ruta_archivo
        self._cancelar: bool = False
        self.setAutoDelete(True)

    def solicitar_cancelacion(self) -> None:
        """Marca el procesamiento para detenerse en el proximo punto seguro."""
        self._cancelar = True

    def run(self) -> None:
        """Ejecuta la carga y emite senales segun el resultado."""
        try:
            resultado = self._lector_excel.cargar_archivo(
                self._ruta_archivo,
                progreso_callback=self.senales.progreso.emit,
                cancelado_callback=self._esta_cancelado,
            )
        except Exception as exc:  # noqa: BLE001
            self.senales.error.emit(str(exc))
            return

        if self._cancelar:
            self.senales.cancelado.emit()
        else:
            self.senales.finalizado.emit(resultado)

    def _esta_cancelado(self) -> bool:
        return self._cancelar
