"""Pruebas de la Fase 5: procesamiento en segundo plano con progreso."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logica.lector_excel import LectorExcel
from modelos.progreso_proceso import EtapaProceso, ProgresoProceso

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
RUTA_MOVIMIENTOS = RAIZ_PROYECTO / "datos_prueba" / "movimientos_simulados.xlsx"
_CONFIG_BASE = {"hoja_por_defecto": "Movimientos"}


# ---------------------------------------------------------------------------
# Fixture: QApplication compartida para tests de worker Qt
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def q_app():
    """QApplication minima para poder instanciar QObject/QRunnable y widgets."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# Tests: LectorExcel con callbacks (sin Qt)
# ---------------------------------------------------------------------------


def test_lector_excel_sin_callback_sigue_funcionando() -> None:
    """cargar_archivo(ruta) sin argumentos extra mantiene la misma interfaz."""
    lector = LectorExcel(configuracion=_CONFIG_BASE)
    resultado = lector.cargar_archivo(RUTA_MOVIMIENTOS)

    assert resultado.exito
    assert resultado.estructura_valida


def test_lector_excel_emite_todas_las_etapas_esperadas() -> None:
    """progreso_callback recibe las etapas del pipeline en un archivo valido."""
    etapas: list[EtapaProceso] = []

    def registrar(progreso: ProgresoProceso) -> None:
        etapas.append(progreso.etapa)

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    resultado = lector.cargar_archivo(RUTA_MOVIMIENTOS, progreso_callback=registrar)

    assert resultado.exito
    etapas_esperadas = [
        EtapaProceso.INICIANDO,
        EtapaProceso.LEYENDO_ARCHIVO,
        EtapaProceso.VALIDANDO_ESTRUCTURA,
        EtapaProceso.NORMALIZANDO_DATOS,
        EtapaProceso.DETECTANDO_FARMACIAS,
        EtapaProceso.CLASIFICANDO,
        EtapaProceso.GENERANDO_RESUMEN,
        EtapaProceso.FINALIZADO,
    ]
    for etapa in etapas_esperadas:
        assert etapa in etapas, f"Etapa {etapa} no emitida"


def test_lector_excel_porcentajes_crecientes() -> None:
    """Los porcentajes emitidos por progreso_callback son monotonicamente crecientes."""
    porcentajes: list[int] = []

    def registrar(progreso: ProgresoProceso) -> None:
        porcentajes.append(progreso.porcentaje)

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    lector.cargar_archivo(RUTA_MOVIMIENTOS, progreso_callback=registrar)

    assert porcentajes, "No se emitio ningun progreso"
    assert porcentajes == sorted(porcentajes), "Los porcentajes no son crecientes"
    assert porcentajes[-1] == 100, "El ultimo porcentaje debe ser 100"


def test_lector_excel_progreso_callback_recibe_ProgresoProceso() -> None:
    """Cada llamada al callback recibe una instancia de ProgresoProceso valida."""
    progresos: list[ProgresoProceso] = []

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    lector.cargar_archivo(RUTA_MOVIMIENTOS, progreso_callback=progresos.append)

    for p in progresos:
        assert isinstance(p, ProgresoProceso)
        assert isinstance(p.etapa, EtapaProceso)
        assert 0 <= p.porcentaje <= 100
        assert isinstance(p.mensaje, str) and p.mensaje


def test_lector_excel_cancelacion_temprana_retorna_resultado_controlado() -> None:
    """cancelado_callback=True detiene el pipeline y retorna exito=False con mensaje de cancelacion."""
    etapas: list[EtapaProceso] = []

    def registrar(p: ProgresoProceso) -> None:
        etapas.append(p.etapa)

    llamadas = {"n": 0}

    def cancelar_desde_primera_verificacion() -> bool:
        llamadas["n"] += 1
        return llamadas["n"] >= 1  # cancela en la primera comprobacion

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    resultado = lector.cargar_archivo(
        RUTA_MOVIMIENTOS,
        progreso_callback=registrar,
        cancelado_callback=cancelar_desde_primera_verificacion,
    )

    assert not resultado.exito
    assert "cancelado" in resultado.mensaje.lower()
    assert EtapaProceso.FINALIZADO not in etapas


def test_lector_excel_cancelacion_sin_progreso_callback() -> None:
    """cancelado_callback funciona correctamente incluso sin progreso_callback."""
    def cancelar_siempre() -> bool:
        return True

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    resultado = lector.cargar_archivo(RUTA_MOVIMIENTOS, cancelado_callback=cancelar_siempre)

    assert not resultado.exito
    assert "cancelado" in resultado.mensaje.lower()


def test_lector_excel_archivo_inexistente_retorna_error() -> None:
    """Un archivo inexistente retorna exito=False sin necesidad de callback."""
    lector = LectorExcel(configuracion=_CONFIG_BASE)
    resultado = lector.cargar_archivo(Path("/ruta/inexistente/archivo.xlsx"))

    assert not resultado.exito


def test_lector_excel_callback_no_invocado_en_error_inicial() -> None:
    """Si el archivo no existe, progreso_callback solo recibe INICIANDO."""
    etapas: list[EtapaProceso] = []
    lector = LectorExcel(configuracion=_CONFIG_BASE)
    lector.cargar_archivo(
        Path("/ruta/inexistente/archivo.xlsx"),
        progreso_callback=lambda p: etapas.append(p.etapa),
    )

    # Solo se emite INICIANDO antes de verificar la existencia
    assert EtapaProceso.INICIANDO in etapas
    assert EtapaProceso.FINALIZADO not in etapas


# ---------------------------------------------------------------------------
# Tests: WorkerProcesamiento (requiere QCoreApplication)
# ---------------------------------------------------------------------------


def test_worker_emite_finalizado_con_resultado_valido(q_app) -> None:
    """WorkerProcesamiento emite finalizado con exito=True para un archivo valido."""
    from interfaz.workers.worker_procesamiento import WorkerProcesamiento

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    resultados: list = []

    worker = WorkerProcesamiento(lector, RUTA_MOVIMIENTOS)
    worker.senales.finalizado.connect(resultados.append)
    worker.run()

    assert len(resultados) == 1
    assert resultados[0].exito
    assert resultados[0].estructura_valida


def test_worker_emite_finalizado_con_exito_false_para_archivo_inexistente(q_app) -> None:
    """WorkerProcesamiento emite finalizado(exito=False) para archivo inexistente, no error."""
    from interfaz.workers.worker_procesamiento import WorkerProcesamiento

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    resultados: list = []
    errores: list = []

    worker = WorkerProcesamiento(lector, Path("/inexistente/archivo.xlsx"))
    worker.senales.finalizado.connect(resultados.append)
    worker.senales.error.connect(errores.append)
    worker.run()

    assert len(resultados) == 1, "Debe emitir finalizado, no error"
    assert not resultados[0].exito
    assert len(errores) == 0


def test_worker_emite_progreso(q_app) -> None:
    """WorkerProcesamiento propaga las etapas del lector al exterior."""
    from interfaz.workers.worker_procesamiento import WorkerProcesamiento

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    progresos: list[ProgresoProceso] = []

    worker = WorkerProcesamiento(lector, RUTA_MOVIMIENTOS)
    worker.senales.progreso.connect(progresos.append)
    worker.run()

    assert len(progresos) > 0
    etapas = {p.etapa for p in progresos}
    assert EtapaProceso.INICIANDO in etapas
    assert EtapaProceso.FINALIZADO in etapas


def test_worker_emite_cancelado_cuando_se_solicita(q_app) -> None:
    """solicitar_cancelacion() provoca que el worker emita cancelado en lugar de finalizado."""
    from interfaz.workers.worker_procesamiento import WorkerProcesamiento

    lector = LectorExcel(configuracion=_CONFIG_BASE)
    cancelados: list = []
    resultados: list = []

    worker = WorkerProcesamiento(lector, RUTA_MOVIMIENTOS)
    worker.senales.cancelado.connect(lambda: cancelados.append(True))
    worker.senales.finalizado.connect(resultados.append)
    worker.solicitar_cancelacion()
    worker.run()

    assert len(cancelados) == 1, "Debe emitir cancelado"
    assert len(resultados) == 0, "No debe emitir finalizado tras cancelacion"


def test_worker_error_signal_ante_excepcion_no_controlada(q_app) -> None:
    """Si el lector lanza una excepcion inesperada, el worker emite error(str)."""
    from interfaz.workers.worker_procesamiento import WorkerProcesamiento

    class LectorRoto:
        def cargar_archivo(self, *args, **kwargs):
            raise RuntimeError("Error simulado en lector")

    errores: list = []
    resultados: list = []

    worker = WorkerProcesamiento(LectorRoto(), RUTA_MOVIMIENTOS)
    worker.senales.error.connect(errores.append)
    worker.senales.finalizado.connect(resultados.append)
    worker.run()

    assert len(errores) == 1
    assert "Error simulado" in errores[0]
    assert len(resultados) == 0


# ---------------------------------------------------------------------------
# Tests: flujo con motor avanzado (requiere sesion_temporal del conftest)
# ---------------------------------------------------------------------------


def test_worker_con_motor_avanzado_clasifica_correctamente(sesion_temporal, q_app) -> None:
    """WorkerProcesamiento con MotorReglasAvanzado produce resultado clasificado."""
    from interfaz.workers.worker_procesamiento import WorkerProcesamiento
    from reglas.motor_reglas_avanzado import MotorReglasAvanzado
    from servicios.servicio_reglas import ServicioReglas

    ruta_reglas = RAIZ_PROYECTO / "configuracion" / "reglas_tipologia.json"
    servicio = ServicioReglas(sesion_temporal)
    servicio.importar_desde_json(ruta_reglas)

    motor = MotorReglasAvanzado(proveedor_reglas=servicio.obtener_reglas_avanzadas)
    lector = LectorExcel(configuracion=_CONFIG_BASE, motor_avanzado=motor)

    resultados: list = []
    worker = WorkerProcesamiento(lector, RUTA_MOVIMIENTOS)
    worker.senales.finalizado.connect(resultados.append)
    worker.run()

    assert len(resultados) == 1
    resultado = resultados[0]
    assert resultado.exito
    assert resultado.estructura_valida
    assert resultado.resultado_preclasificacion.cantidad_clasificados > 0

    df = resultado.dataframe_procesado
    assert "TIPOLOGIA_PRELIMINAR" in df.columns
    assert "REGLA_APLICADA" in df.columns
    assert "REGLA_ID" in df.columns
    assert "EXPLICACION_REGLA" in df.columns


def test_lector_con_callback_y_motor_avanzado_clasifica_correctamente(sesion_temporal) -> None:
    """LectorExcel con motor avanzado clasifica correctamente incluso con progreso_callback activo."""
    from reglas.motor_reglas_avanzado import MotorReglasAvanzado
    from servicios.servicio_reglas import ServicioReglas

    ruta_reglas = RAIZ_PROYECTO / "configuracion" / "reglas_tipologia.json"
    servicio = ServicioReglas(sesion_temporal)
    servicio.importar_desde_json(ruta_reglas)

    motor = MotorReglasAvanzado(proveedor_reglas=servicio.obtener_reglas_avanzadas)
    lector = LectorExcel(configuracion=_CONFIG_BASE, motor_avanzado=motor)

    etapas: list[EtapaProceso] = []
    resultado = lector.cargar_archivo(
        RUTA_MOVIMIENTOS,
        progreso_callback=lambda p: etapas.append(p.etapa),
    )

    assert resultado.exito
    assert resultado.resultado_preclasificacion.cantidad_clasificados > 0
    assert EtapaProceso.FINALIZADO in etapas
