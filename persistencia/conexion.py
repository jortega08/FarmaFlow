"""Configuracion de conexion SQLite y sesiones SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from utilidades.rutas import obtener_ruta_base_datos


def _activar_claves_foraneas(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def crear_engine(configuracion: dict[str, Any] | None = None, echo: bool = False) -> Engine:
    """Crea un engine SQLite con soporte de claves foraneas."""
    ruta_base_datos = obtener_ruta_base_datos(configuracion)
    engine_sqlite = create_engine(
        f"sqlite:///{ruta_base_datos.as_posix()}",
        echo=echo,
        future=True,
    )
    event.listen(engine_sqlite, "connect", _activar_claves_foraneas)
    return engine_sqlite


engine = crear_engine()
SesionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def configurar_conexion(configuracion: dict[str, Any] | None = None) -> None:
    """Reconfigura la conexion global, por ejemplo para una base por usuario."""
    global engine, SesionLocal
    engine.dispose()
    engine = crear_engine(configuracion)
    SesionLocal.configure(bind=engine)


def obtener_sesion() -> Session:
    """Crea una sesion nueva enlazada al engine por defecto."""
    return SesionLocal()


def get_session() -> Iterator[Session]:
    """Generador de sesion reutilizable por futuros servicios o APIs."""
    sesion = obtener_sesion()
    try:
        yield sesion
    finally:
        sesion.close()


@contextmanager
def sesion_scope() -> Iterator[Session]:
    """Maneja commit, rollback y cierre de una sesion."""
    sesion = obtener_sesion()
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
