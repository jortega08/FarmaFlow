"""Pruebas del repositorio de clinicas."""

from __future__ import annotations

from sqlalchemy.orm import Session

from repositorios.repositorio_clinicas import RepositorioClinicas


def test_crud_y_busqueda_por_nombre_normalizado(sesion_temporal: Session) -> None:
    repo = RepositorioClinicas(sesion_temporal)

    clinica = repo.crear(codigo="CRS", nombre="Clinica del Rosario")

    assert clinica.id is not None
    assert clinica.nombre_normalizado == "CLINICA DEL ROSARIO"
    assert repo.obtener(clinica.id) == clinica
    assert repo.buscar_por_nombre_normalizado(" clinica   del rosario ") == clinica

    actualizada = repo.actualizar(clinica.id, nombre="Clinica Rosario Norte")
    assert actualizada is not None
    assert actualizada.nombre_normalizado == "CLINICA ROSARIO NORTE"

    assert repo.eliminar(clinica.id) is True
    assert repo.obtener(clinica.id) is None

