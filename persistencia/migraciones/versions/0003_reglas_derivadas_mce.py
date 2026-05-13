"""reglas derivadas y correccion MCE

Revision ID: 0003_reglas_derivadas_mce
Revises: 0002_farmacias_codigo_unico_defaults_listas
Create Date: 2026-05-07 00:00:00.000000

"""
from __future__ import annotations

from alembic import op


revision = "0003_reglas_derivadas_mce"
down_revision = "0002_farmacias_codigo_unico_defaults_listas"
branch_labels = None
depends_on = None


MCE_ARTICULOS = (
    "21817",
    "71837",
    "73796",
    "383679",
    "386588",
    "162397",
    "390482",
    "388907",
    "109046",
    "548339",
    "555234",
    "109491",
    "393397",
    "60744",
    "388908",
    "37785",
    "561531",
    "534011",
    "106876",
    "169534",
    "167725",
    "123778",
    "106877",
    "135679",
    "525052",
    "137151",
    "384851",
)

LIQUIDOS_ARTICULOS = (
    "63192",
    "19891",
    "388835",
    "19929",
    "388839",
    "388828",
    "388832",
    "19949",
    "100479",
    "19967",
    "140663",
    "388840",
    "32219",
    "388856",
)


def upgrade() -> None:
    bind = op.get_bind()
    _renombrar_mcs_a_mce(bind)
    _asegurar_lista(bind, "LIQUIDOS", "Liquidos Cirugia", "Articulos liquidos de cirugia")
    _asegurar_lista(bind, "MCE_CIRUGIA", "MCE Cirugia", "Articulos MCE Cirugia")
    _sembrar_items_lista(bind, "LIQUIDOS", LIQUIDOS_ARTICULOS)
    _sembrar_items_lista(bind, "MCE_CIRUGIA", MCE_ARTICULOS)


def downgrade() -> None:
    pass


def _renombrar_mcs_a_mce(bind) -> None:
    mcs = bind.exec_driver_sql("SELECT id FROM listas_configurables WHERE codigo = 'MCS_CIRUGIA'").mappings().first()
    mce = bind.exec_driver_sql("SELECT id FROM listas_configurables WHERE codigo = 'MCE_CIRUGIA'").mappings().first()
    if mcs is None:
        return
    if mce is None:
        bind.exec_driver_sql(
            """
            UPDATE listas_configurables
            SET codigo = 'MCE_CIRUGIA',
                nombre = 'MCE Cirugia',
                descripcion = 'Articulos MCE Cirugia',
                fecha_modificacion = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (mcs["id"],),
        )
        return

    bind.exec_driver_sql("UPDATE lista_items SET lista_id = ? WHERE lista_id = ?", (mce["id"], mcs["id"]))
    bind.exec_driver_sql("DELETE FROM listas_configurables WHERE id = ?", (mcs["id"],))


def _asegurar_lista(bind, codigo: str, nombre: str, descripcion: str) -> None:
    bind.exec_driver_sql(
        """
        INSERT INTO listas_configurables
            (codigo, nombre, tipo_lista, descripcion, activa, fecha_creacion, fecha_modificacion)
        SELECT ?, ?, 'ARTICULOS', ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM listas_configurables WHERE codigo = ?)
        """,
        (codigo, nombre, descripcion, codigo),
    )


def _sembrar_items_lista(bind, codigo_lista: str, codigos: tuple[str, ...]) -> None:
    lista = bind.exec_driver_sql("SELECT id FROM listas_configurables WHERE codigo = ?", (codigo_lista,)).mappings().first()
    if lista is None:
        return
    lista_id = int(lista["id"])
    for codigo in codigos:
        bind.exec_driver_sql(
            """
            INSERT INTO lista_items
                (lista_id, codigo, valor, valor_normalizado, activo, fecha_creacion)
            SELECT ?, ?, ?, ?, 1, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1 FROM lista_items WHERE lista_id = ? AND valor_normalizado = ?
            )
            """,
            (lista_id, codigo, codigo, codigo, lista_id, codigo),
        )
