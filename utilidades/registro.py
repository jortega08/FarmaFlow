"""Configuracion del sistema de logs."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def configurar_registro(nombre_aplicacion: str, ruta_logs: Path) -> None:
    """Configura el registro hacia consola y archivo."""
    ruta_logs.mkdir(parents=True, exist_ok=True)
    ruta_archivo_log = ruta_logs / f"{_normalizar_nombre(nombre_aplicacion)}_{datetime.now():%Y%m%d}.log"

    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(logging.INFO)

    if getattr(logger_raiz, "_configurado_por_clasificador", False):
        return

    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    manejador_archivo = logging.FileHandler(ruta_archivo_log, encoding="utf-8")
    manejador_archivo.setFormatter(formato)

    manejador_consola = logging.StreamHandler()
    manejador_consola.setFormatter(formato)

    logger_raiz.handlers.clear()
    logger_raiz.addHandler(manejador_archivo)
    logger_raiz.addHandler(manejador_consola)
    logger_raiz._configurado_por_clasificador = True


def _normalizar_nombre(texto: str) -> str:
    return texto.lower().replace(" ", "_")
