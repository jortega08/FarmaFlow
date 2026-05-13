"""Boton con simbolo prefijado y variante de estilo semantico."""

from __future__ import annotations

from PySide6.QtWidgets import QPushButton

_TIPO_A_NOMBRE: dict[str, str] = {
    "primario": "botonPrincipal",
    "secundario": "botonSecundario",
    "exito": "botonExito",
    "terciario": "botonTerciario",
}


class BotonIcono(QPushButton):
    """Boton con simbolo prefijado para acciones principales."""

    def __init__(
        self,
        texto: str,
        simbolo: str = "",
        tipo: str = "primario",
        parent=None,
    ) -> None:
        etiqueta = f"{simbolo}  {texto}" if simbolo else texto
        super().__init__(etiqueta, parent)
        self.setObjectName(_TIPO_A_NOMBRE.get(tipo, "botonSecundario"))
        self.setMinimumHeight(44)
