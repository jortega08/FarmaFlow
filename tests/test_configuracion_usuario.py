"""Tests de aislamiento de configuracion por usuario."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from main import _configuracion_para_usuario
from utilidades.rutas import obtener_ruta_base_datos


@pytest.fixture()
def localappdata_temporal(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    ruta = Path(tempfile.mkdtemp())
    monkeypatch.setenv("LOCALAPPDATA", str(ruta))
    try:
        yield ruta
    finally:
        shutil.rmtree(ruta, ignore_errors=True)


def test_configuracion_para_usuario_usa_base_y_salidas_propias(
    localappdata_temporal: Path,
) -> None:
    config = _configuracion_para_usuario(
        {"nombre_base_datos": "clasificador_farmacia.db", "ruta_salidas": "salidas"},
        "Usuario Demo",
    )

    assert config["usuario_base_datos"] == "usuario_demo"
    assert config["ruta_salidas"] == "salidas/usuario_demo"
    assert config["copiar_plantilla_base_datos"] is False
    assert obtener_ruta_base_datos(config).name == "clasificador_farmacia_usuario_demo.db"
