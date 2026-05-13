"""reempaque y liquidos cirugia

Revision ID: 0004_reempaque_liquidos_cirugia
Revises: 0003_reglas_derivadas_mce
Create Date: 2026-05-07 00:00:00.000000

"""
from __future__ import annotations

from alembic import op


revision = "0004_reempaque_liquidos_cirugia"
down_revision = "0003_reglas_derivadas_mce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    _renombrar_tipo_reposicion_a_reempaque(bind)
    bind.exec_driver_sql(
        """
        UPDATE listas_configurables
        SET nombre = 'Liquidos Cirugia',
            descripcion = 'Articulos liquidos de cirugia',
            fecha_modificacion = CURRENT_TIMESTAMP
        WHERE codigo = 'LIQUIDOS'
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    _renombrar_tipo_reempaque_a_reposicion(bind)
    bind.exec_driver_sql(
        """
        UPDATE listas_configurables
        SET nombre = 'Liquidos',
            descripcion = 'Articulos liquidos',
            fecha_modificacion = CURRENT_TIMESTAMP
        WHERE codigo = 'LIQUIDOS'
        """
    )


def _renombrar_tipo_reposicion_a_reempaque(bind) -> None:
    anterior = bind.exec_driver_sql(
        "SELECT id FROM tipos_farmacia WHERE codigo = 'REREPOSICION'"
    ).mappings().first()
    actual = bind.exec_driver_sql(
        "SELECT id FROM tipos_farmacia WHERE codigo = 'REEMPAQUE'"
    ).mappings().first()

    if anterior is None:
        if actual is not None:
            _actualizar_tipo_reempaque(bind, int(actual["id"]))
        return

    anterior_id = int(anterior["id"])
    if actual is None:
        bind.exec_driver_sql(
            """
            UPDATE tipos_farmacia
            SET codigo = 'REEMPAQUE',
                nombre = 'Reempaque',
                descripcion = 'Central de reempaque'
            WHERE id = ?
            """,
            (anterior_id,),
        )
        return

    actual_id = int(actual["id"])
    bind.exec_driver_sql(
        "UPDATE farmacias SET tipo_farmacia_id = ? WHERE tipo_farmacia_id = ?",
        (actual_id, anterior_id),
    )
    bind.exec_driver_sql("DELETE FROM tipos_farmacia WHERE id = ?", (anterior_id,))
    _actualizar_tipo_reempaque(bind, actual_id)


def _renombrar_tipo_reempaque_a_reposicion(bind) -> None:
    actual = bind.exec_driver_sql(
        "SELECT id FROM tipos_farmacia WHERE codigo = 'REEMPAQUE'"
    ).mappings().first()
    anterior = bind.exec_driver_sql(
        "SELECT id FROM tipos_farmacia WHERE codigo = 'REREPOSICION'"
    ).mappings().first()

    if actual is None:
        return

    actual_id = int(actual["id"])
    if anterior is None:
        bind.exec_driver_sql(
            """
            UPDATE tipos_farmacia
            SET codigo = 'REREPOSICION',
                nombre = 'Rereposicion',
                descripcion = 'Central de reempaque y reposicion'
            WHERE id = ?
            """,
            (actual_id,),
        )
        return

    anterior_id = int(anterior["id"])
    bind.exec_driver_sql(
        "UPDATE farmacias SET tipo_farmacia_id = ? WHERE tipo_farmacia_id = ?",
        (anterior_id, actual_id),
    )
    bind.exec_driver_sql("DELETE FROM tipos_farmacia WHERE id = ?", (actual_id,))


def _actualizar_tipo_reempaque(bind, tipo_id: int) -> None:
    bind.exec_driver_sql(
        """
        UPDATE tipos_farmacia
        SET nombre = 'Reempaque',
            descripcion = 'Central de reempaque'
        WHERE id = ?
        """,
        (tipo_id,),
    )
