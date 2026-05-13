"""Utilidades seguras para aplicar migraciones de la base local."""

from __future__ import annotations

from pathlib import Path
from shutil import copy2
from typing import Any

from alembic import command
from alembic.config import Config

from utilidades.rutas import obtener_ruta_base_datos, resolver_ruta_proyecto


def crear_configuracion_alembic(url: str | None = None) -> Config:
    """Construye la configuracion Alembic usando las rutas del proyecto."""
    ruta_alembic = resolver_ruta_proyecto("alembic.ini")
    configuracion = Config(str(ruta_alembic) if ruta_alembic.exists() else None)
    configuracion.set_main_option(
        "script_location",
        str(resolver_ruta_proyecto("persistencia", "migraciones")),
    )
    if url is not None:
        configuracion.set_main_option("sqlalchemy.url", url)
    return configuracion


def copiar_base_datos_inicial_si_existe(ruta_base_datos: Path) -> bool:
    """Copia una plantilla SQLite de solo lectura al directorio escribible si existe."""
    ruta_base_datos.parent.mkdir(parents=True, exist_ok=True)
    if ruta_base_datos.exists():
        return False

    for ruta_plantilla in _rutas_plantilla_base_datos():
        if not ruta_plantilla.exists() or _misma_ruta(ruta_plantilla, ruta_base_datos):
            continue
        copy2(ruta_plantilla, ruta_base_datos)
        return True

    return False


def _rutas_plantilla_base_datos() -> tuple[Path, ...]:
    return (
        resolver_ruta_proyecto("datos", "clasificador_farmacia.db"),
        resolver_ruta_proyecto("base_datos", "clasificador_farmacia.db"),
    )


def _misma_ruta(ruta_origen: Path, ruta_destino: Path) -> bool:
    try:
        return ruta_origen.resolve() == ruta_destino.resolve()
    except OSError:
        return False


def asegurar_base_datos_actualizada(configuracion_app: dict[str, Any] | None = None) -> None:
    """Aplica ``upgrade head`` sin recrear ni borrar la base existente."""
    ruta_base_datos = obtener_ruta_base_datos(configuracion_app)
    copiar_plantilla = True
    if configuracion_app is not None:
        copiar_plantilla = bool(configuracion_app.get("copiar_plantilla_base_datos", True))
    if copiar_plantilla:
        copiar_base_datos_inicial_si_existe(ruta_base_datos)
    url = f"sqlite:///{ruta_base_datos.as_posix()}"
    configuracion_alembic = crear_configuracion_alembic(url)

    try:
        command.upgrade(configuracion_alembic, "head")
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(
            "No fue posible actualizar la base de datos local. "
            "Revise permisos, que el archivo SQLite no este bloqueado y que las migraciones sean validas."
        ) from error
