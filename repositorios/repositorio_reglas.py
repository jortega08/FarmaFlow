"""Repositorio de reglas de clasificacion."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select

from persistencia.modelos_orm import CondicionRegla, ReglaClasificacion
from repositorios.repositorio_base import RepositorioBase
from utilidades.texto import normalizar_nombre_columna


class RepositorioReglas(RepositorioBase[ReglaClasificacion]):
    """Operaciones especificas para reglas de clasificacion."""

    modelo = ReglaClasificacion

    def crear_con_condiciones(
        self,
        *,
        condiciones: Iterable[dict[str, object]],
        **campos: object,
    ) -> ReglaClasificacion:
        regla = self.crear(**campos)
        for indice, condicion in enumerate(condiciones):
            datos_condicion = dict(condicion)
            if "campo" in datos_condicion:
                datos_condicion["campo"] = normalizar_nombre_columna(datos_condicion["campo"])
            datos_condicion.setdefault("orden", indice)
            regla.condiciones.append(CondicionRegla(**datos_condicion))
        self.sesion.flush()
        self.sesion.refresh(regla)
        return regla

    def listar_activas_ordenadas_por_prioridad(self) -> list[ReglaClasificacion]:
        consulta = (
            select(ReglaClasificacion)
            .where(ReglaClasificacion.activa.is_(True))
            .order_by(ReglaClasificacion.prioridad, ReglaClasificacion.id)
        )
        return list(self.sesion.scalars(consulta).all())

