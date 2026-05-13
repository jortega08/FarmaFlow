"""Pruebas de migraciones Alembic."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config


RAIZ_PROYECTO = Path(__file__).resolve().parents[1]


def crear_config_alembic(url: str) -> Config:
    configuracion = Config(str(RAIZ_PROYECTO / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ_PROYECTO / "persistencia" / "migraciones"))
    configuracion.set_main_option("sqlalchemy.url", url)
    return configuracion


def test_upgrade_head_seed_y_downgrade_base() -> None:
    ruta_temporal = RAIZ_PROYECTO / ".tmp_tests" / "migraciones"
    ruta_temporal.mkdir(parents=True, exist_ok=True)
    ruta_db = ruta_temporal / f"clasificador_test_{uuid4().hex}.db"
    configuracion = crear_config_alembic(f"sqlite:///{ruta_db.as_posix()}")

    command.upgrade(configuracion, "head")

    with sqlite3.connect(ruta_db) as conexion:
        codigos = {
            fila[0]
            for fila in conexion.execute("SELECT codigo FROM tipos_farmacia ORDER BY codigo").fetchall()
        }
        listas = {
            fila[0]
            for fila in conexion.execute("SELECT codigo FROM listas_configurables ORDER BY codigo").fetchall()
        }
        liquidos = conexion.execute(
            "SELECT nombre, descripcion FROM listas_configurables WHERE codigo = 'LIQUIDOS'"
        ).fetchone()
        mce_items = conexion.execute(
            """
            SELECT COUNT(*)
            FROM lista_items li
            JOIN listas_configurables lc ON lc.id = li.lista_id
            WHERE lc.codigo = 'MCE_CIRUGIA'
            """
        ).fetchone()[0]

    assert codigos == {
        "ALMACEN",
        "BODEGA",
        "CEDI",
        "CENTRAL_PREPARACION",
        "DEVOLUCIONES",
        "EXTERNA",
        "INTERNA",
        "NO_CLASIFICABLE",
        "REEMPAQUE",
    }
    assert {"LIQUIDOS", "MCE_CIRUGIA"} <= listas
    assert liquidos == ("Liquidos Cirugia", "Articulos liquidos de cirugia")
    assert mce_items >= 27

    command.downgrade(configuracion, "base")

    with sqlite3.connect(ruta_db) as conexion:
        tablas = {
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }

    assert tablas <= {"alembic_version"}
