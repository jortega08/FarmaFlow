"""Modelos ORM de la base local del clasificador."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from persistencia.base import Base


class Clinica(Base):
    """Clinica o institucion operativa."""

    __tablename__ = "clinicas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(Text, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )

    farmacias_asociadas: Mapped[list[ClinicaFarmacia]] = relationship(
        back_populates="clinica",
        cascade="all, delete-orphan",
    )
    ejecuciones: Mapped[list[EjecucionProceso]] = relationship(back_populates="clinica")

    __table_args__ = (Index("ix_clinicas_nombre_normalizado", "nombre_normalizado"),)


class TipoFarmacia(Base):
    """Tipo funcional de farmacia."""

    __tablename__ = "tipos_farmacia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    farmacias: Mapped[list[Farmacia]] = relationship(back_populates="tipo_farmacia")


class Farmacia(Base):
    """Farmacia detectada o configurada."""

    __tablename__ = "farmacias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_original: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_farmacia_id: Mapped[int] = mapped_column(ForeignKey("tipos_farmacia.id"), nullable=False)
    puede_prestar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    es_interna: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    es_externa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )

    tipo_farmacia: Mapped[TipoFarmacia] = relationship(back_populates="farmacias")
    clinicas_asociadas: Mapped[list[ClinicaFarmacia]] = relationship(
        back_populates="farmacia",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("codigo", name="uq_farmacias_codigo"),
        Index("ix_farmacias_codigo", "codigo"),
        Index("ix_farmacias_nombre_normalizado", "nombre_normalizado"),
        Index("ix_farmacias_tipo_farmacia_id", "tipo_farmacia_id"),
    )


class ClinicaFarmacia(Base):
    """Relacion entre clinicas y farmacias."""

    __tablename__ = "clinica_farmacia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinicas.id"), nullable=False)
    farmacia_id: Mapped[int] = mapped_column(ForeignKey("farmacias.id"), nullable=False)
    relacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    clinica: Mapped[Clinica] = relationship(back_populates="farmacias_asociadas")
    farmacia: Mapped[Farmacia] = relationship(back_populates="clinicas_asociadas")

    __table_args__ = (UniqueConstraint("clinica_id", "farmacia_id", name="uq_clinica_farmacia"),)


class ListaConfigurable(Base):
    """Lista editable usada por reglas y catalogos."""

    __tablename__ = "listas_configurables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_lista: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )

    items: Mapped[list[ItemLista]] = relationship(
        back_populates="lista",
        cascade="all, delete-orphan",
    )
    condiciones: Mapped[list[CondicionRegla]] = relationship(back_populates="lista")

    __table_args__ = (
        CheckConstraint(
            "tipo_lista IN ('ARTICULOS', 'FARMACIAS', 'MOTIVOS', 'SUBINVENTARIOS', 'ORGANIZACIONES')",
            name="ck_listas_configurables_tipo_lista",
        ),
    )


class ItemLista(Base):
    """Item perteneciente a una lista configurable."""

    __tablename__ = "lista_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lista_id: Mapped[int] = mapped_column(ForeignKey("listas_configurables.id"), nullable=False)
    codigo: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor: Mapped[str] = mapped_column(Text, nullable=False)
    valor_normalizado: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    lista: Mapped[ListaConfigurable] = relationship(back_populates="items")

    __table_args__ = (
        UniqueConstraint("lista_id", "valor_normalizado", name="uq_lista_items_lista_valor_normalizado"),
        Index("ix_lista_items_lista_valor", "lista_id", "valor"),
        Index("ix_lista_items_codigo", "codigo"),
        Index("ix_lista_items_valor_normalizado", "valor_normalizado"),
    )


class ReglaClasificacion(Base):
    """Regla editable para clasificacion de movimientos."""

    __tablename__ = "reglas_clasificacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipologia_resultado: Mapped[str] = mapped_column(Text, nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    origen: Mapped[str] = mapped_column(Text, nullable=False, default="SISTEMA")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )

    condiciones: Mapped[list[CondicionRegla]] = relationship(
        back_populates="regla",
        cascade="all, delete-orphan",
        order_by="CondicionRegla.orden",
    )

    __table_args__ = (
        CheckConstraint(
            "origen IN ('JSON_MIGRADO', 'EXCEL_IMPORTADO', 'CREADA_UI', 'SISTEMA')",
            name="ck_reglas_clasificacion_origen",
        ),
    )


class CondicionRegla(Base):
    """Condicion atomica de una regla de clasificacion."""

    __tablename__ = "condiciones_regla"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    regla_id: Mapped[int] = mapped_column(ForeignKey("reglas_clasificacion.id"), nullable=False)
    campo: Mapped[str] = mapped_column(Text, nullable=False)
    operador: Mapped[str] = mapped_column(Text, nullable=False)
    valor_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    lista_id: Mapped[int | None] = mapped_column(ForeignKey("listas_configurables.id"), nullable=True)
    atributo_farmacia: Mapped[str | None] = mapped_column(Text, nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    regla: Mapped[ReglaClasificacion] = relationship(back_populates="condiciones")
    lista: Mapped[ListaConfigurable | None] = relationship(back_populates="condiciones")

    __table_args__ = (Index("ix_condiciones_regla_regla_orden", "regla_id", "orden"),)


class EjecucionProceso(Base):
    """Registro resumido de una ejecucion de procesamiento."""

    __tablename__ = "ejecuciones_proceso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clinica_id: Mapped[int | None] = mapped_column(ForeignKey("clinicas.id"), nullable=True)
    archivo_nombre: Mapped[str] = mapped_column(Text, nullable=False)
    archivo_ruta: Mapped[str | None] = mapped_column(Text, nullable=True)
    hoja: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_registros: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_columnas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_clasificados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_sin_clasificar: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duracion_segundos: Mapped[float | None] = mapped_column(Float, nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="INICIADA")
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)

    clinica: Mapped[Clinica | None] = relationship(back_populates="ejecuciones")

    __table_args__ = (
        CheckConstraint(
            "estado IN ('INICIADA', 'VALIDADA', 'CLASIFICADA', 'EXPORTADA', 'ERROR', 'CANCELADA')",
            name="ck_ejecuciones_proceso_estado",
        ),
    )
