"""Fixtures de pruebas para persistencia."""

from __future__ import annotations

import sys
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROYECTO))

RUTA_TEMPORALES = RAIZ_PROYECTO / ".tmp_tests"
RUTA_TEMPORALES.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = str(RUTA_TEMPORALES)
os.environ["TEMP"] = str(RUTA_TEMPORALES)
tempfile.tempdir = str(RUTA_TEMPORALES)


def _crear_directorio_temporal_seguro() -> Path:
    ruta = RUTA_TEMPORALES / f"test_{uuid.uuid4().hex}"
    ruta.mkdir(parents=True, exist_ok=False)
    return ruta


class DirectorioTemporalWorkspace:
    """Reemplazo de TemporaryDirectory que evita mkdtemp en este sandbox."""

    def __init__(self, *args, **kwargs) -> None:
        self.name = str(_crear_directorio_temporal_seguro())

    def __enter__(self) -> str:
        return self.name

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        shutil.rmtree(self.name, ignore_errors=True)


def mkdtemp_workspace(*args, **kwargs) -> str:
    return str(_crear_directorio_temporal_seguro())


tempfile.TemporaryDirectory = DirectorioTemporalWorkspace
tempfile.mkdtemp = mkdtemp_workspace


def crear_config_alembic(url: str | None = None) -> Config:
    configuracion = Config(str(RAIZ_PROYECTO / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ_PROYECTO / "persistencia" / "migraciones"))
    if url is not None:
        configuracion.set_main_option("sqlalchemy.url", url)
    return configuracion


def activar_claves_foraneas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def aplicar_migraciones(engine: Engine) -> None:
    configuracion = crear_config_alembic()
    with engine.begin() as connection:
        configuracion.attributes["connection"] = connection
        command.upgrade(configuracion, "head")


@pytest.fixture()
def engine_temporal() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", activar_claves_foraneas)
    aplicar_migraciones(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def sesion_temporal(engine_temporal: Engine) -> Iterator[Session]:
    SesionTemporal = sessionmaker(bind=engine_temporal, autoflush=False, expire_on_commit=False, future=True)
    sesion = SesionTemporal()
    try:
        yield sesion
    finally:
        sesion.rollback()
        sesion.close()
