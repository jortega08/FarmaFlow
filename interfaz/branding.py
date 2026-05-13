"""Recursos de marca de FarmaFlow."""

from __future__ import annotations

from pathlib import Path

from utilidades.rutas import resolver_ruta_proyecto

NOMBRE_APP = "FarmaFlow"
APP_USER_MODEL_ID = "FarmaFlow.Desktop.App"
RUTA_ICONO_APP: Path = resolver_ruta_proyecto(
    "interfaz", "assets", "ICONO_FARMAFLOW.png"
)
RUTA_ICONO_APP_ICO: Path = resolver_ruta_proyecto(
    "interfaz", "assets", "ICONO_FARMAFLOW.ico"
)
RUTA_LOGO_APP: Path = resolver_ruta_proyecto(
    "interfaz", "assets", "LOGO_FARMAFLOW.png"
)
RUTA_FONDO_LOGIN: Path = resolver_ruta_proyecto(
    "interfaz", "assets", "FONDO_LOGIN_FARMAFLOW.png"
)
