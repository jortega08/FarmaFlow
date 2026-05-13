"""Funciones auxiliares para rutas, salidas y carga de configuracion."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

NOMBRE_APLICACION = "FarmaFlow"
NOMBRE_ARCHIVO_BASE_DATOS = "clasificador_farmacia.db"


def obtener_ruta_proyecto() -> Path:
    """Retorna la ruta raiz del proyecto."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def resolver_ruta_proyecto(*segmentos: str) -> Path:
    """Construye una ruta absoluta dentro del proyecto."""
    return obtener_ruta_proyecto().joinpath(*segmentos)


def obtener_directorio_datos_app() -> Path:
    """Retorna el directorio escribible de datos de usuario para la aplicacion."""
    if sys.platform.startswith("win"):
        raiz = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        raiz = Path.home() / "Library" / "Application Support"
    else:
        raiz = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")

    return asegurar_directorio(raiz / NOMBRE_APLICACION)


def obtener_directorio_base_datos() -> Path:
    """Retorna y asegura el directorio escribible donde vive SQLite."""
    return asegurar_directorio(obtener_directorio_datos_app() / "base_datos")


def obtener_ruta_base_datos(configuracion: dict[str, Any] | None = None) -> Path:
    """Retorna la ruta escribible del archivo SQLite local."""
    nombre_archivo = NOMBRE_ARCHIVO_BASE_DATOS
    if configuracion:
        nombre_archivo = str(configuracion.get("nombre_base_datos", nombre_archivo))
        usuario_base_datos = str(configuracion.get("usuario_base_datos", "")).strip()
        if usuario_base_datos:
            base = Path(nombre_archivo).stem
            extension = Path(nombre_archivo).suffix or ".db"
            usuario_limpio = limpiar_nombre_archivo(usuario_base_datos).lower()
            nombre_archivo = f"{base}_{usuario_limpio}{extension}"
    return obtener_directorio_base_datos() / Path(nombre_archivo).name


def _resolver_ruta_datos_app(nombre_directorio: str) -> Path:
    ruta_configurada = Path(str(nombre_directorio).strip() or ".")
    if ruta_configurada.is_absolute():
        ruta_configurada = Path(ruta_configurada.name)
    partes = [parte for parte in ruta_configurada.parts if parte not in ("", ".", "..")]
    return obtener_directorio_datos_app().joinpath(*partes)


def obtener_ruta_salidas(configuracion: dict[str, Any] | None = None) -> Path:
    """Retorna la ruta configurada para archivos de salida."""
    nombre_directorio = "salidas"
    if configuracion:
        nombre_directorio = str(configuracion.get("ruta_salidas", nombre_directorio))
    return asegurar_directorio(_resolver_ruta_datos_app(nombre_directorio))


def obtener_ruta_datos(configuracion: dict[str, Any] | None = None) -> Path:
    """Retorna y asegura la ruta configurada para datos locales."""
    nombre_directorio = "datos"
    if configuracion:
        nombre_directorio = str(configuracion.get("ruta_datos", nombre_directorio))
    return asegurar_directorio(_resolver_ruta_datos_app(nombre_directorio))


def obtener_ruta_logs(configuracion: dict[str, Any] | None = None) -> Path:
    """Retorna y asegura la ruta escribible para logs locales."""
    nombre_directorio = "logs"
    if configuracion:
        nombre_directorio = str(configuracion.get("ruta_logs", nombre_directorio))
    return asegurar_directorio(_resolver_ruta_datos_app(nombre_directorio))


def asegurar_directorio(ruta_directorio: Path | str) -> Path:
    """Crea un directorio si no existe y retorna su ruta absoluta."""
    ruta = Path(ruta_directorio)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def limpiar_nombre_archivo(nombre_archivo: str) -> str:
    """Elimina caracteres invalidos y simplifica espacios para nombres de archivo."""
    nombre_limpio = Path(str(nombre_archivo).strip() or "archivo").stem
    nombre_limpio = re.sub(r'[<>:"/\\|?*]+', "_", nombre_limpio)
    nombre_limpio = re.sub(r"\s+", "_", nombre_limpio)
    nombre_limpio = re.sub(r"_+", "_", nombre_limpio).strip("._")
    return nombre_limpio or "archivo"


def construir_nombre_archivo_salida(
    nombre_base: str = "",
    extension: str = ".xlsx",
) -> str:
    """Construye un nombre de archivo de salida con timestamp para evitar colisiones."""
    marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_limpia = limpiar_nombre_archivo(nombre_base) if nombre_base else ""
    prefijo = "clasificado"

    if base_limpia:
        return f"{prefijo}_{base_limpia}_{marca_tiempo}{extension}"
    return f"{prefijo}_{marca_tiempo}{extension}"


def cargar_json(ruta_archivo: Path) -> Any:
    """Carga un archivo JSON y devuelve su contenido."""
    with ruta_archivo.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)
