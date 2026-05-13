"""farmacias codigo unico, defaults y listas reservadas

Revision ID: 0002_farmacias_codigo_unico_defaults_listas
Revises: 0001_inicial
Create Date: 2026-05-05 00:00:00.000000

"""
from __future__ import annotations

from alembic import op


revision = "0002_farmacias_codigo_unico_defaults_listas"
down_revision = "0001_inicial"
branch_labels = None
depends_on = None


LISTAS_ARTICULOS_RESERVADAS = (
    ("LIQUIDOS", "Liquidos Cirugia", "Articulos liquidos de cirugia"),
    ("MCE_CIRUGIA", "MCE Cirugia", "Articulos MCE Cirugia"),
)


def upgrade() -> None:
    bind = op.get_bind()
    _fusionar_codigos_farmacia_duplicados(bind)
    op.execute("UPDATE farmacias SET puede_prestar = 1 WHERE puede_prestar = 0 OR puede_prestar IS NULL")

    with op.batch_alter_table("farmacias") as batch_op:
        batch_op.drop_constraint("uq_farmacias_codigo_nombre_normalizado", type_="unique")
        batch_op.create_unique_constraint("uq_farmacias_codigo", ["codigo"])

    for codigo, nombre, descripcion in LISTAS_ARTICULOS_RESERVADAS:
        op.execute(
            f"""
            INSERT INTO listas_configurables
                (codigo, nombre, tipo_lista, descripcion, activa, fecha_creacion, fecha_modificacion)
            SELECT
                '{codigo}', '{nombre}', 'ARTICULOS', '{descripcion}', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1 FROM listas_configurables WHERE codigo = '{codigo}'
            )
            """
        )


def downgrade() -> None:
    with op.batch_alter_table("farmacias") as batch_op:
        batch_op.drop_constraint("uq_farmacias_codigo", type_="unique")
        batch_op.create_unique_constraint(
            "uq_farmacias_codigo_nombre_normalizado",
            ["codigo", "nombre_normalizado"],
        )

    op.execute(
        """
        DELETE FROM listas_configurables
        WHERE codigo IN ('LIQUIDOS', 'MCE_CIRUGIA')
        AND id NOT IN (SELECT DISTINCT lista_id FROM lista_items)
        """
    )


def _fusionar_codigos_farmacia_duplicados(bind) -> None:
    duplicados = bind.exec_driver_sql(
        """
        SELECT codigo, MIN(id) AS sobreviviente_id, COUNT(*) AS cantidad
        FROM farmacias
        GROUP BY codigo
        HAVING COUNT(*) > 1
        """
    ).mappings().all()

    for grupo in duplicados:
        codigo = grupo["codigo"]
        sobreviviente_id = int(grupo["sobreviviente_id"])
        filas = bind.exec_driver_sql(
            "SELECT id FROM farmacias WHERE codigo = ? AND id <> ? ORDER BY id",
            (codigo, sobreviviente_id),
        ).mappings().all()
        for fila in filas:
            duplicado_id = int(fila["id"])
            _transferir_asociaciones_farmacia(bind, duplicado_id, sobreviviente_id)
            bind.exec_driver_sql(
                """
                UPDATE farmacias
                SET codigo = ?, activa = 0, fecha_modificacion = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (f"{codigo}__DUPLICADO_{duplicado_id}", duplicado_id),
            )


def _transferir_asociaciones_farmacia(bind, origen_id: int, destino_id: int) -> None:
    asociaciones = bind.exec_driver_sql(
        "SELECT id, clinica_id, relacion, activa FROM clinica_farmacia WHERE farmacia_id = ?",
        (origen_id,),
    ).mappings().all()

    for asociacion in asociaciones:
        existente = bind.exec_driver_sql(
            "SELECT id, activa FROM clinica_farmacia WHERE clinica_id = ? AND farmacia_id = ?",
            (asociacion["clinica_id"], destino_id),
        ).mappings().first()
        if existente is None:
            bind.exec_driver_sql(
                "UPDATE clinica_farmacia SET farmacia_id = ? WHERE id = ?",
                (destino_id, asociacion["id"]),
            )
            continue

        if bool(asociacion["activa"]) and not bool(existente["activa"]):
            bind.exec_driver_sql(
                "UPDATE clinica_farmacia SET activa = 1 WHERE id = ?",
                (existente["id"],),
            )
        bind.exec_driver_sql("DELETE FROM clinica_farmacia WHERE id = ?", (asociacion["id"],))
