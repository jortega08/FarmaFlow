"""Repositorio de clinicas."""

from __future__ import annotations

from sqlalchemy import select

from persistencia.modelos_orm import Clinica
from repositorios.repositorio_base import RepositorioBase
from utilidades.texto import normalizar_texto


class RepositorioClinicas(RepositorioBase[Clinica]):
    """Operaciones especificas para clinicas."""

    modelo = Clinica

    def crear(self, **campos: object) -> Clinica:
        if "nombre" in campos and "nombre_normalizado" not in campos:
            campos["nombre_normalizado"] = normalizar_texto(campos["nombre"])
        return super().crear(**campos)

    def actualizar(self, id: int, **campos: object) -> Clinica | None:
        if "nombre" in campos and "nombre_normalizado" not in campos:
            campos["nombre_normalizado"] = normalizar_texto(campos["nombre"])
        return super().actualizar(id, **campos)

    def buscar_por_nombre_normalizado(self, texto: object) -> Clinica | None:
        nombre_normalizado = normalizar_texto(texto)
        consulta = select(Clinica).where(Clinica.nombre_normalizado == nombre_normalizado)
        return self.sesion.scalars(consulta).first()

    def buscar_por_codigo(self, codigo: str) -> Clinica | None:
        consulta = select(Clinica).where(Clinica.codigo == codigo)
        return self.sesion.scalars(consulta).first()

