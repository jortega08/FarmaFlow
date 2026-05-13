"""DTO de progreso para el procesamiento de archivos en segundo plano."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EtapaProceso(str, Enum):
    """Etapas del pipeline de procesamiento de archivos."""

    INICIANDO = "INICIANDO"
    LEYENDO_ARCHIVO = "LEYENDO_ARCHIVO"
    VALIDANDO_ESTRUCTURA = "VALIDANDO_ESTRUCTURA"
    NORMALIZANDO_DATOS = "NORMALIZANDO_DATOS"
    DETECTANDO_FARMACIAS = "DETECTANDO_FARMACIAS"
    CLASIFICANDO = "CLASIFICANDO"
    GENERANDO_RESUMEN = "GENERANDO_RESUMEN"
    FINALIZADO = "FINALIZADO"
    ERROR = "ERROR"
    CANCELADO = "CANCELADO"


@dataclass(slots=True)
class ProgresoProceso:
    """Estado puntual del progreso durante la carga de un archivo."""

    etapa: EtapaProceso
    porcentaje: int
    mensaje: str
    registros_procesados: int = 0
    total_registros: int = 0
