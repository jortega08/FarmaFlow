"""Tests del servicio local de autenticacion."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from servicios.servicio_autenticacion import ErrorAutenticacion, ServicioAutenticacion


@pytest.fixture()
def directorio_temporal() -> Iterator[Path]:
    ruta = Path(tempfile.mkdtemp())
    try:
        yield ruta
    finally:
        shutil.rmtree(ruta, ignore_errors=True)


def test_registro_y_login_exitoso(directorio_temporal: Path) -> None:
    servicio = ServicioAutenticacion(directorio_temporal / "usuarios.json")

    sesion_registro = servicio.registrar(
        usuario="admin",
        contrasena="secreto1",
        empresa="Farmacia Central",
        nombres="Ana",
        apellidos="Perez",
    )
    sesion_login = servicio.autenticar("ADMIN", "secreto1")

    assert sesion_registro.usuario == "admin"
    assert sesion_login.empresa == "Farmacia Central"
    assert sesion_login.nombres == "Ana"


def test_no_permite_usuario_duplicado(directorio_temporal: Path) -> None:
    servicio = ServicioAutenticacion(directorio_temporal / "usuarios.json")
    datos = {
        "usuario": "admin",
        "contrasena": "secreto1",
        "empresa": "Empresa",
        "nombres": "Nombre",
        "apellidos": "Apellido",
    }

    servicio.registrar(**datos)

    with pytest.raises(ErrorAutenticacion, match="Ya existe"):
        servicio.registrar(**datos)


def test_restablece_contrasena_con_usuario_y_empresa(
    directorio_temporal: Path,
) -> None:
    servicio = ServicioAutenticacion(directorio_temporal / "usuarios.json")
    servicio.registrar(
        usuario="usuario",
        contrasena="inicial1",
        empresa="Mi Empresa",
        nombres="Juan",
        apellidos="Lopez",
    )

    servicio.restablecer_contrasena(
        usuario="usuario",
        empresa="mi empresa",
        nueva_contrasena="nueva123",
    )

    with pytest.raises(ErrorAutenticacion):
        servicio.autenticar("usuario", "inicial1")
    assert servicio.autenticar("usuario", "nueva123").apellidos == "Lopez"
