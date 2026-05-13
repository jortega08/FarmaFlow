"""inicial

Revision ID: 0001_inicial
Revises:
Create Date: 2026-04-30 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_inicial"
down_revision = None
branch_labels = None
depends_on = None


TIPOS_FARMACIA_SEED = [
    {"codigo": "INTERNA", "nombre": "Interna", "descripcion": "Farmacia interna de la clinica"},
    {"codigo": "EXTERNA", "nombre": "Externa", "descripcion": "Farmacia externa o de terceros"},
    {"codigo": "CEDI", "nombre": "CEDI", "descripcion": "Centro de distribucion"},
    {"codigo": "DEVOLUCIONES", "nombre": "Devoluciones", "descripcion": "Operacion de devoluciones"},
    {"codigo": "ALMACEN", "nombre": "Almacen", "descripcion": "Almacen operativo"},
    {"codigo": "BODEGA", "nombre": "Bodega", "descripcion": "Bodega de inventario"},
    {
        "codigo": "CENTRAL_PREPARACION",
        "nombre": "Central de preparacion",
        "descripcion": "Central de preparacion de medicamentos",
    },
    {"codigo": "REEMPAQUE", "nombre": "Reempaque", "descripcion": "Central de reempaque"},
    {"codigo": "NO_CLASIFICABLE", "nombre": "No clasificable", "descripcion": "No clasificable"},
]


def upgrade() -> None:
    op.create_table(
        "clinicas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("nombre_normalizado", sa.Text(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_modificacion", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )
    op.create_index("ix_clinicas_nombre_normalizado", "clinicas", ["nombre_normalizado"], unique=False)

    tipos_farmacia = op.create_table(
        "tipos_farmacia",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )

    op.create_table(
        "listas_configurables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("tipo_lista", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_modificacion", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "tipo_lista IN ('ARTICULOS', 'FARMACIAS', 'MOTIVOS', 'SUBINVENTARIOS', 'ORGANIZACIONES')",
            name="ck_listas_configurables_tipo_lista",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )

    op.create_table(
        "reglas_clasificacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tipologia_resultado", sa.Text(), nullable=False),
        sa.Column("prioridad", sa.Integer(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("origen", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_modificacion", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "origen IN ('JSON_MIGRADO', 'EXCEL_IMPORTADO', 'CREADA_UI', 'SISTEMA')",
            name="ck_reglas_clasificacion_origen",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )

    op.create_table(
        "ejecuciones_proceso",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(), nullable=True),
        sa.Column("clinica_id", sa.Integer(), nullable=True),
        sa.Column("archivo_nombre", sa.Text(), nullable=False),
        sa.Column("archivo_ruta", sa.Text(), nullable=True),
        sa.Column("hoja", sa.Text(), nullable=True),
        sa.Column("total_registros", sa.Integer(), nullable=False),
        sa.Column("total_columnas", sa.Integer(), nullable=False),
        sa.Column("total_clasificados", sa.Integer(), nullable=False),
        sa.Column("total_sin_clasificar", sa.Integer(), nullable=False),
        sa.Column("duracion_segundos", sa.Float(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "estado IN ('INICIADA', 'VALIDADA', 'CLASIFICADA', 'EXPORTADA', 'ERROR', 'CANCELADA')",
            name="ck_ejecuciones_proceso_estado",
        ),
        sa.ForeignKeyConstraint(["clinica_id"], ["clinicas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "farmacias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("nombre_original", sa.Text(), nullable=False),
        sa.Column("nombre_normalizado", sa.Text(), nullable=False),
        sa.Column("tipo_farmacia_id", sa.Integer(), nullable=False),
        sa.Column("puede_prestar", sa.Boolean(), nullable=False),
        sa.Column("es_interna", sa.Boolean(), nullable=False),
        sa.Column("es_externa", sa.Boolean(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_modificacion", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tipo_farmacia_id"], ["tipos_farmacia.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo", "nombre_normalizado", name="uq_farmacias_codigo_nombre_normalizado"),
    )
    op.create_index("ix_farmacias_codigo", "farmacias", ["codigo"], unique=False)
    op.create_index("ix_farmacias_nombre_normalizado", "farmacias", ["nombre_normalizado"], unique=False)
    op.create_index("ix_farmacias_tipo_farmacia_id", "farmacias", ["tipo_farmacia_id"], unique=False)

    op.create_table(
        "lista_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lista_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("valor_normalizado", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lista_id"], ["listas_configurables.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lista_id", "valor_normalizado", name="uq_lista_items_lista_valor_normalizado"),
    )
    op.create_index("ix_lista_items_codigo", "lista_items", ["codigo"], unique=False)
    op.create_index("ix_lista_items_lista_valor", "lista_items", ["lista_id", "valor"], unique=False)
    op.create_index("ix_lista_items_valor_normalizado", "lista_items", ["valor_normalizado"], unique=False)

    op.create_table(
        "condiciones_regla",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("regla_id", sa.Integer(), nullable=False),
        sa.Column("campo", sa.Text(), nullable=False),
        sa.Column("operador", sa.Text(), nullable=False),
        sa.Column("valor_texto", sa.Text(), nullable=True),
        sa.Column("lista_id", sa.Integer(), nullable=True),
        sa.Column("atributo_farmacia", sa.Text(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["lista_id"], ["listas_configurables.id"]),
        sa.ForeignKeyConstraint(["regla_id"], ["reglas_clasificacion.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_condiciones_regla_regla_orden", "condiciones_regla", ["regla_id", "orden"], unique=False)

    op.create_table(
        "clinica_farmacia",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("clinica_id", sa.Integer(), nullable=False),
        sa.Column("farmacia_id", sa.Integer(), nullable=False),
        sa.Column("relacion", sa.Text(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["clinica_id"], ["clinicas.id"]),
        sa.ForeignKeyConstraint(["farmacia_id"], ["farmacias.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinica_id", "farmacia_id", name="uq_clinica_farmacia"),
    )

    op.bulk_insert(tipos_farmacia, TIPOS_FARMACIA_SEED)


def downgrade() -> None:
    op.drop_table("clinica_farmacia")
    op.drop_index("ix_condiciones_regla_regla_orden", table_name="condiciones_regla")
    op.drop_table("condiciones_regla")
    op.drop_index("ix_lista_items_valor_normalizado", table_name="lista_items")
    op.drop_index("ix_lista_items_lista_valor", table_name="lista_items")
    op.drop_index("ix_lista_items_codigo", table_name="lista_items")
    op.drop_table("lista_items")
    op.drop_index("ix_farmacias_tipo_farmacia_id", table_name="farmacias")
    op.drop_index("ix_farmacias_nombre_normalizado", table_name="farmacias")
    op.drop_index("ix_farmacias_codigo", table_name="farmacias")
    op.drop_table("farmacias")
    op.drop_table("ejecuciones_proceso")
    op.drop_table("reglas_clasificacion")
    op.drop_table("listas_configurables")
    op.drop_table("tipos_farmacia")
    op.drop_index("ix_clinicas_nombre_normalizado", table_name="clinicas")
    op.drop_table("clinicas")
