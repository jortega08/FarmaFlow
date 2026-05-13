"""Factory de composicion para construir LectorExcel con el motor adecuado.

Centraliza la logica de wiring entre la capa de servicios y la capa logica,
manteniendo la UI libre de dependencias ORM.
"""

from __future__ import annotations

import logging
from typing import Any

from logica.lector_excel import LectorExcel
from reglas.motor_reglas_avanzado import MotorReglasAvanzado
from servicios.servicio_reglas import obtener_contexto_motor, obtener_reglas_motor_avanzado

_logger = logging.getLogger(__name__)


def crear_lector_excel_con_motor_avanzado(configuracion: dict[str, Any]) -> LectorExcel:
    """Construye LectorExcel con MotorReglasAvanzado conectado a la BD.

    Realiza un preflight que verifica si existen reglas activas (sembrando desde
    JSON legacy si es necesario) y si el contexto de farmacias/listas es accesible.
    Lanza RuntimeError si no hay reglas disponibles para que el caller pueda
    aplicar el fallback al clasificador legacy.
    """
    reglas = obtener_reglas_motor_avanzado()
    if not reglas:
        raise RuntimeError(
            "No hay reglas activas disponibles en la BD para el motor avanzado. "
            "Verifique que la base de datos este inicializada y contenga reglas."
        )

    contexto = obtener_contexto_motor()
    _logger.info(
        "Motor avanzado habilitado: %d reglas, %d farmacias en catalogo, %d listas configuradas.",
        len(reglas),
        len(contexto.farmacias),
        len(contexto.listas),
    )

    motor = MotorReglasAvanzado(
        proveedor_reglas=obtener_reglas_motor_avanzado,
        proveedor_contexto=obtener_contexto_motor,
    )
    return LectorExcel(configuracion=configuracion, motor_avanzado=motor)


def crear_lector_excel_con_fallback(configuracion: dict[str, Any]) -> LectorExcel:
    """Intenta construir LectorExcel con motor avanzado; usa legacy si falla.

    Garantiza que la aplicacion siempre arranca correctamente aunque la BD no
    este disponible o no contenga reglas.
    """
    try:
        lector = crear_lector_excel_con_motor_avanzado(configuracion)
        return lector
    except Exception as error:  # noqa: BLE001
        _logger.warning(
            "Motor legacy usado por fallback: no fue posible habilitar el motor avanzado. Causa: %s",
            error,
        )
        return LectorExcel(configuracion=configuracion)
