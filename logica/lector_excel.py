"""Lectura basica de archivos Excel."""

from __future__ import annotations

import logging
from pathlib import Path
from collections.abc import Callable
from typing import Any

import pandas as pd

from logica.clasificador_tipologia import ClasificadorTipologia
from logica.detector_farmacias import DetectorFarmacias
from logica.generador_resumen import generar_resumen_dataframe
from logica.generador_resumen import generar_resumen_preclasificacion, generar_resumen_validacion
from logica.normalizador_datos import NormalizadorDatos
from logica.validador_estructura import ValidadorEstructura
from modelos.progreso_proceso import EtapaProceso, ProgresoProceso
from modelos.resultado_carga import ResultadoCarga
from servicios.servicio_reglas import obtener_reglas_motor_desde_bd
from utilidades.mensajes import MensajesInterfaz

_MENSAJE_CANCELADO = "Procesamiento cancelado por el usuario."


class LectorExcel:
    """Realiza la validacion y lectura de archivos Excel."""

    EXTENSIONES_VALIDAS = {".xlsx", ".xls"}

    def __init__(
        self,
        configuracion: dict[str, Any],
        proveedor_reglas: Callable[[], list[dict[str, Any]]] | None = None,
        motor_avanzado: Any | None = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._hoja_por_defecto = configuracion.get("hoja_por_defecto", "")
        self._validador_estructura = ValidadorEstructura()
        self._normalizador_datos = NormalizadorDatos()
        self._detector_farmacias = DetectorFarmacias()
        self._motor = motor_avanzado or ClasificadorTipologia(
            proveedor_reglas=proveedor_reglas or obtener_reglas_motor_desde_bd,
        )

    def cargar_archivo(
        self,
        ruta_archivo: Path,
        progreso_callback: Callable[[ProgresoProceso], None] | None = None,
        cancelado_callback: Callable[[], bool] | None = None,
    ) -> ResultadoCarga:
        """Lee un archivo Excel y devuelve un resultado estructurado.

        Los parametros opcionales progreso_callback y cancelado_callback
        permiten uso asincrono desde un worker Qt sin romper llamadas existentes.
        """
        self._logger.info("Iniciando carga de archivo: %s", ruta_archivo)
        self._emitir(progreso_callback, EtapaProceso.INICIANDO, 0, "Iniciando procesamiento...")

        if not ruta_archivo.exists():
            mensaje = MensajesInterfaz.ERROR_ARCHIVO_NO_EXISTE
            self._logger.error("%s: %s", mensaje, ruta_archivo)
            return ResultadoCarga(exito=False, mensaje=mensaje, ruta_archivo=str(ruta_archivo))

        if ruta_archivo.suffix.lower() not in self.EXTENSIONES_VALIDAS:
            mensaje = MensajesInterfaz.ERROR_ARCHIVO_INVALIDO
            self._logger.error("%s: %s", mensaje, ruta_archivo)
            return ResultadoCarga(exito=False, mensaje=mensaje, ruta_archivo=str(ruta_archivo))

        self._emitir(progreso_callback, EtapaProceso.LEYENDO_ARCHIVO, 10, "Leyendo archivo Excel...")
        try:
            libro_excel = pd.ExcelFile(ruta_archivo)
            hoja_utilizada = self._seleccionar_hoja(libro_excel.sheet_names)
            dataframe = pd.read_excel(ruta_archivo, sheet_name=hoja_utilizada)
            cantidad_filas, cantidad_columnas, columnas = generar_resumen_dataframe(dataframe)
        except FileNotFoundError:
            mensaje = MensajesInterfaz.ERROR_ARCHIVO_NO_EXISTE
            self._logger.exception("El archivo desaparecio durante la lectura: %s", ruta_archivo)
            return ResultadoCarga(exito=False, mensaje=mensaje, ruta_archivo=str(ruta_archivo))
        except ValueError:
            mensaje = MensajesInterfaz.ERROR_ARCHIVO_INVALIDO
            self._logger.exception("El archivo no tiene una estructura Excel valida: %s", ruta_archivo)
            return ResultadoCarga(exito=False, mensaje=mensaje, ruta_archivo=str(ruta_archivo))
        except Exception as error:  # noqa: BLE001
            mensaje = f"{MensajesInterfaz.ERROR_APERTURA}: {error}"
            self._logger.exception("Error inesperado al leer el archivo: %s", ruta_archivo)
            return ResultadoCarga(exito=False, mensaje=mensaje, ruta_archivo=str(ruta_archivo))

        if cancelado_callback is not None and cancelado_callback():
            return ResultadoCarga(exito=False, mensaje=_MENSAJE_CANCELADO, ruta_archivo=str(ruta_archivo))

        self._logger.info(
            "Archivo cargado correctamente. Hoja: %s, filas: %s, columnas: %s",
            hoja_utilizada,
            cantidad_filas,
            cantidad_columnas,
        )

        self._emitir(
            progreso_callback,
            EtapaProceso.VALIDANDO_ESTRUCTURA,
            30,
            "Validando estructura del archivo...",
            total_registros=cantidad_filas,
        )
        resultado_validacion = self._validador_estructura.validar(columnas)
        resumen_validacion = generar_resumen_validacion(resultado_validacion)

        if not resultado_validacion.exito:
            mensaje = f"{MensajesInterfaz.ERROR_VALIDACION}: {resultado_validacion.mensaje}"
            self._logger.error("La validacion estructural no pudo ejecutarse: %s", resultado_validacion.mensaje)
            return ResultadoCarga(
                exito=False,
                mensaje=mensaje,
                ruta_archivo=str(ruta_archivo),
                nombre_archivo=ruta_archivo.name,
                hoja_utilizada=hoja_utilizada,
                cantidad_filas=cantidad_filas,
                cantidad_columnas=cantidad_columnas,
                columnas=columnas,
                dataframe=dataframe,
                resultado_validacion=resultado_validacion,
                resumen_validacion=resumen_validacion,
                estructura_valida=False,
            )

        if not resultado_validacion.estructura_valida:
            self._logger.warning(
                "La estructura del archivo es invalida. Columnas faltantes: %s",
                resultado_validacion.columnas_faltantes,
            )
            return ResultadoCarga(
                exito=True,
                mensaje=MensajesInterfaz.ESTRUCTURA_INVALIDA,
                ruta_archivo=str(ruta_archivo),
                nombre_archivo=ruta_archivo.name,
                hoja_utilizada=hoja_utilizada,
                cantidad_filas=cantidad_filas,
                cantidad_columnas=cantidad_columnas,
                columnas=columnas,
                dataframe=dataframe,
                resultado_validacion=resultado_validacion,
                resumen_validacion=resumen_validacion,
                estructura_valida=False,
            )

        if cancelado_callback is not None and cancelado_callback():
            return ResultadoCarga(exito=False, mensaje=_MENSAJE_CANCELADO, ruta_archivo=str(ruta_archivo))

        self._emitir(
            progreso_callback,
            EtapaProceso.NORMALIZANDO_DATOS,
            50,
            "Normalizando datos...",
            total_registros=cantidad_filas,
        )
        dataframe_normalizado = self._normalizador_datos.normalizar(
            dataframe=dataframe,
            columnas_mapeadas=resultado_validacion.columnas_mapeadas,
        )

        if cancelado_callback is not None and cancelado_callback():
            return ResultadoCarga(exito=False, mensaje=_MENSAJE_CANCELADO, ruta_archivo=str(ruta_archivo))

        self._emitir(
            progreso_callback,
            EtapaProceso.DETECTANDO_FARMACIAS,
            65,
            "Detectando farmacias...",
            total_registros=cantidad_filas,
        )
        dataframe_con_farmacias, _ = self._detector_farmacias.detectar(dataframe_normalizado)

        if cancelado_callback is not None and cancelado_callback():
            return ResultadoCarga(exito=False, mensaje=_MENSAJE_CANCELADO, ruta_archivo=str(ruta_archivo))

        self._emitir(
            progreso_callback,
            EtapaProceso.CLASIFICANDO,
            80,
            "Clasificando movimientos...",
            total_registros=cantidad_filas,
        )
        resultado_preclasificacion = self._motor.clasificar(dataframe_con_farmacias)

        self._emitir(
            progreso_callback,
            EtapaProceso.GENERANDO_RESUMEN,
            90,
            "Generando resumen...",
            registros_procesados=resultado_preclasificacion.cantidad_clasificados,
            total_registros=cantidad_filas,
        )
        resumen_preclasificacion = generar_resumen_preclasificacion(resultado_preclasificacion)

        self._emitir(
            progreso_callback,
            EtapaProceso.FINALIZADO,
            100,
            "Procesamiento completado.",
            registros_procesados=resultado_preclasificacion.cantidad_registros,
            total_registros=cantidad_filas,
        )

        return ResultadoCarga(
            exito=True,
            mensaje=MensajesInterfaz.RESUMEN_VALIDADO_GENERADO,
            ruta_archivo=str(ruta_archivo),
            nombre_archivo=ruta_archivo.name,
            hoja_utilizada=hoja_utilizada,
            cantidad_filas=cantidad_filas,
            cantidad_columnas=cantidad_columnas,
            columnas=columnas,
            dataframe=dataframe,
            dataframe_procesado=resultado_preclasificacion.dataframe_resultado,
            resultado_validacion=resultado_validacion,
            resultado_preclasificacion=resultado_preclasificacion,
            resumen_validacion=resumen_validacion,
            resumen_preclasificacion=resumen_preclasificacion,
            estructura_valida=True,
        )

    def _seleccionar_hoja(self, hojas_disponibles: list[str]) -> str:
        """Selecciona la hoja preferida o la primera disponible."""
        if self._hoja_por_defecto and self._hoja_por_defecto in hojas_disponibles:
            return self._hoja_por_defecto
        return hojas_disponibles[0]

    @staticmethod
    def _emitir(
        callback: Callable[[ProgresoProceso], None] | None,
        etapa: EtapaProceso,
        porcentaje: int,
        mensaje: str,
        registros_procesados: int = 0,
        total_registros: int = 0,
    ) -> None:
        if callback is not None:
            callback(
                ProgresoProceso(
                    etapa=etapa,
                    porcentaje=porcentaje,
                    mensaje=mensaje,
                    registros_procesados=registros_procesados,
                    total_registros=total_registros,
                )
            )
