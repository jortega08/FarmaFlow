"""Repositorio de farmacias."""

from __future__ import annotations

from sqlalchemy import or_, select

from persistencia.modelos_orm import Farmacia, TipoFarmacia
from repositorios.repositorio_base import RepositorioBase
from utilidades.texto import normalizar_texto


class RepositorioFarmacias(RepositorioBase[Farmacia]):
    """Operaciones especificas para farmacias."""

    modelo = Farmacia

    def crear(self, **campos: object) -> Farmacia:
        if "nombre_original" in campos and "nombre_normalizado" not in campos:
            campos["nombre_normalizado"] = normalizar_texto(campos["nombre_original"])
        return super().crear(**campos)

    def actualizar(self, id: int, **campos: object) -> Farmacia | None:
        if "nombre_original" in campos and "nombre_normalizado" not in campos:
            campos["nombre_normalizado"] = normalizar_texto(campos["nombre_original"])
        return super().actualizar(id, **campos)

    def buscar_por_codigo(self, codigo: str) -> list[Farmacia]:
        consulta = select(Farmacia).where(Farmacia.codigo == codigo)
        return list(self.sesion.scalars(consulta).all())

    def obtener_por_codigo(self, codigo: str) -> Farmacia | None:
        consulta = select(Farmacia).where(Farmacia.codigo == codigo)
        return self.sesion.scalars(consulta).first()

    def buscar_por_codigo_o_nombre(self, codigo: str | None, nombre: object | None) -> list[Farmacia]:
        condiciones = []
        if codigo:
            condiciones.append(Farmacia.codigo == codigo)
        nombre_normalizado = normalizar_texto(nombre)
        if nombre_normalizado:
            condiciones.append(Farmacia.nombre_normalizado == nombre_normalizado)
        if not condiciones:
            return []

        consulta = select(Farmacia).where(or_(*condiciones)).order_by(Farmacia.nombre_normalizado, Farmacia.id)
        return list(self.sesion.scalars(consulta).all())

    def listar_por_tipo(self, tipo_codigo: str) -> list[Farmacia]:
        consulta = (
            select(Farmacia)
            .join(Farmacia.tipo_farmacia)
            .where(TipoFarmacia.codigo == tipo_codigo)
            .order_by(Farmacia.nombre_normalizado)
        )
        return list(self.sesion.scalars(consulta).all())
