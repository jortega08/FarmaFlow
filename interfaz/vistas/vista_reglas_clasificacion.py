"""Vista funcional de gestion de reglas de clasificacion."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import pandas as pd
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dto.lista_dto import ListaConfigurableCrearDTO, ListaConfigurableDTO
from dto.regla_dto import (
    CondicionReglaCrearDTO,
    ReglaClasificacionActualizarDTO,
    ReglaClasificacionCrearDTO,
    ReglaClasificacionDTO,
)
from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from interfaz.componentes.dialogo_guardar_clinica import (
    extraer_farmacias_org_destino,
    extraer_farmacias_org_origen,
)
from interfaz.componentes.dialogo_editar_lista import DialogoEditarLista
from persistencia.conexion import sesion_scope
from reglas.operadores import OperadorCondicion
from servicios.excepciones import ErrorDominio
from servicios.servicio_farmacias import ServicioFarmacias
from servicios.servicio_listas import ServicioListas
from servicios.servicio_reglas import ServicioReglas
from utilidades.rutas import resolver_ruta_proyecto
from utilidades.texto import normalizar_codigo


_FILAS_REGLAS = 8

# Catalogo de campos disponibles para condiciones, con descripcion y ejemplo.
# El orden importa: aparece asi en el combo.
_CATALOGO_CAMPOS: tuple[tuple[str, str, str], ...] = (
    ("TIPO_TRANSACCION", "Tipo de transaccion", "Sales order issue, Intransit Receipt, RMA Receipt..."),
    ("TIPO_ORIGEN", "Tipo de origen", "Sales order, Inventory, Account alias..."),
    ("ORG_ORIGEN", "Organizacion de origen", "16_FARMA_FARMACIA_INTERNA_CRS"),
    ("ORG_DESTINO", "Organizacion de destino", "47_FARMA_ALMACEN_CIRUGIA_CRS"),
    ("ORIGEN", "Origen del movimiento", "MOVIMIENTOS BOPOS-EBS, ANEXO 6 SALIDA DESTRUCCION MCE..."),
    ("MOTIVO", "Motivo", "Texto libre del motivo del movimiento"),
    ("SUBINVENTARIO", "Subinventario", "Codigo de subinventario"),
    ("ARTICULO", "Articulo", "Codigo del articulo"),
    ("DESCRIPCION", "Descripcion del articulo", "Texto descriptivo del articulo"),
    ("FARMACIA_ORIGEN", "Farmacia (origen)", "Aplica el catalogo de farmacias"),
    ("FARMACIA_DESTINO", "Farmacia (destino)", "Aplica el catalogo de farmacias"),
    ("AJUSTE", "Ajuste", "Marca de ajuste"),
    ("NUMERO_ENVIO", "Numero de envio", "Codigo del envio"),
    ("PEDIDO", "Pedido", "Numero de pedido"),
    ("REFERENCIA", "Referencia", "Texto de referencia"),
)
_CAMPOS = tuple(item[0] for item in _CATALOGO_CAMPOS)
_DESCRIPCION_CAMPO: dict[str, str] = {item[0]: item[1] for item in _CATALOGO_CAMPOS}
_EJEMPLO_CAMPO: dict[str, str] = {item[0]: item[2] for item in _CATALOGO_CAMPOS}

# Operadores por categoria con etiqueta amigable.
_CATALOGO_OPERADORES: tuple[tuple[str, str], ...] = (
    (OperadorCondicion.IGUAL.value, "es igual a"),
    (OperadorCondicion.DISTINTO.value, "es distinto de"),
    (OperadorCondicion.CONTIENE.value, "contiene"),
    (OperadorCondicion.NO_CONTIENE.value, "no contiene"),
    (OperadorCondicion.EMPIEZA_POR.value, "empieza por"),
    (OperadorCondicion.TERMINA_EN.value, "termina en"),
    (OperadorCondicion.EN_LISTA.value, "esta en la lista"),
    (OperadorCondicion.NO_EN_LISTA.value, "no esta en la lista"),
    (OperadorCondicion.EN_COLUMNA.value, "esta en la columna"),
    (OperadorCondicion.NO_EN_COLUMNA.value, "no esta en la columna"),
    (OperadorCondicion.VACIO.value, "esta vacio"),
    (OperadorCondicion.NO_VACIO.value, "tiene valor"),
    (OperadorCondicion.FARMACIA_PUEDE_PRESTAR.value, "es farmacia que puede prestar"),
    (OperadorCondicion.FARMACIA_NO_PUEDE_PRESTAR.value, "es farmacia que NO puede prestar"),
    (OperadorCondicion.FARMACIA_ES_TIPO.value, "es farmacia de tipo"),
    (OperadorCondicion.FARMACIA_NO_ES_TIPO.value, "no es farmacia de tipo"),
)
_ETIQUETA_OPERADOR: dict[str, str] = {clave: etiqueta for clave, etiqueta in _CATALOGO_OPERADORES}

# Operadores comunes a todos los campos.
_OPERADORES_GENERALES: tuple[str, ...] = (
    OperadorCondicion.IGUAL.value,
    OperadorCondicion.DISTINTO.value,
    OperadorCondicion.CONTIENE.value,
    OperadorCondicion.NO_CONTIENE.value,
    OperadorCondicion.EMPIEZA_POR.value,
    OperadorCondicion.TERMINA_EN.value,
    OperadorCondicion.EN_LISTA.value,
    OperadorCondicion.NO_EN_LISTA.value,
    OperadorCondicion.EN_COLUMNA.value,
    OperadorCondicion.NO_EN_COLUMNA.value,
    OperadorCondicion.VACIO.value,
    OperadorCondicion.NO_VACIO.value,
)
_OPERADORES_FARMACIA: tuple[str, ...] = (
    OperadorCondicion.FARMACIA_PUEDE_PRESTAR.value,
    OperadorCondicion.FARMACIA_NO_PUEDE_PRESTAR.value,
    OperadorCondicion.FARMACIA_ES_TIPO.value,
    OperadorCondicion.FARMACIA_NO_ES_TIPO.value,
)

_OPERADORES_SIN_VALOR: frozenset[str] = frozenset(
    {
        OperadorCondicion.VACIO.value,
        OperadorCondicion.NO_VACIO.value,
        OperadorCondicion.FARMACIA_PUEDE_PRESTAR.value,
        OperadorCondicion.FARMACIA_NO_PUEDE_PRESTAR.value,
    }
)
_OPERADORES_LISTA: frozenset[str] = frozenset(
    {OperadorCondicion.EN_LISTA.value, OperadorCondicion.NO_EN_LISTA.value}
)


def _operadores_para_campo(campo: str) -> tuple[str, ...]:
    """Operadores admitidos segun el tipo del campo."""
    if campo in {"FARMACIA_ORIGEN", "FARMACIA_DESTINO"}:
        return _OPERADORES_GENERALES + _OPERADORES_FARMACIA
    return _OPERADORES_GENERALES


class VistaReglasClasificacion(QWidget):
    """Pantalla de administracion de reglas de clasificacion."""

    cambios_configuracion = Signal(str)

    def __init__(
        self,
        dataframe_provider: Callable[[], pd.DataFrame | None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._dataframe_provider = dataframe_provider
        self._reglas: list[ReglaClasificacionDTO] = []
        self._listas: list[ListaConfigurableDTO] = []
        self._farmacias_bd: list[str] = []
        self._listas_por_id: dict[int, ListaConfigurableDTO] = {}
        self._listas_por_codigo: dict[str, ListaConfigurableDTO] = {}
        self._reglas_filtradas: list[int] = []
        self._pagina_actual = 1
        self._regla_actual_id: int | None = None
        self._editor_visible: bool = False
        self._bloqueando_eventos = False
        self._animaciones: list[QPropertyAnimation] = []

        self._construir_ui()
        self._cargar_datos()

    # ------------------------------------------------------------------
    # Construccion
    # ------------------------------------------------------------------

    def _construir_ui(self) -> None:
        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorVista")
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(16)

        layout.addWidget(self._crear_titulo())
        layout.addWidget(self._crear_panel_explicativo())
        layout.addWidget(self._crear_toolbar())
        layout.addLayout(self._crear_contenido_principal())
        layout.addLayout(self._crear_listas_apoyo())
        layout.addWidget(self._crear_barra_inferior())
        layout.addStretch(1)

        scroll.setWidget(contenedor)
        layout_raiz.addWidget(scroll)

    def _crear_titulo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        icono = QLabel("RL")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(50, 50)
        icono.setAlignment(Qt.AlignCenter)

        textos = QVBoxLayout()
        textos.setSpacing(4)
        titulo = QLabel("3. Reglas de clasificacion")
        titulo.setObjectName("tituloSeccion")
        subtitulo = QLabel(
            "Administre tipologias, listas y prioridades que determinan como se clasifican los movimientos."
        )
        subtitulo.setObjectName("textoSecundario")
        subtitulo.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)

        layout.addWidget(icono)
        layout.addLayout(textos, 1)
        return card

    def _crear_panel_explicativo(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelGuiaReglas")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        titulo = QLabel("Como funcionan las reglas")
        titulo.setObjectName("tituloSubpanel")
        layout.addWidget(titulo)

        pasos = QHBoxLayout()
        pasos.setSpacing(14)
        contenidos = (
            ("1", "Defina la tipologia", "El resultado que recibira el movimiento (ej. DISPENSACION)."),
            ("2", "Agregue condiciones", "Cada condicion filtra por un campo. Todas se combinan con Y (AND)."),
            ("3", "Asigne una prioridad", "Menor numero = se evalua primero. La primera regla que coincida gana."),
        )
        for numero, titulo_paso, texto in contenidos:
            pasos.addWidget(self._crear_tarjeta_paso(numero, titulo_paso, texto), 1)
        layout.addLayout(pasos)

        return card

    def _crear_tarjeta_paso(self, numero: str, titulo: str, descripcion: str) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        badge = QLabel(numero)
        badge.setObjectName("badgePasoGuia")
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(badge)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("valorCampo")
        lbl_desc = QLabel(descripcion)
        lbl_desc.setObjectName("textoSecundario")
        lbl_desc.setWordWrap(True)
        textos.addWidget(lbl_titulo)
        textos.addWidget(lbl_desc)
        layout.addLayout(textos, 1)
        return card

    def _crear_toolbar(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(14)

        acciones = (
            ("+ Nueva regla", self._nueva_regla, "botonPrincipal", 170),
            ("Importar desde Excel", self._importar_reglas_excel, "botonSecundario", 210),
            ("Probar reglas", self._probar_reglas, "botonSecundario", 170),
            ("Restaurar reglas base", self._restaurar_reglas_base, "botonSecundario", 210),
        )
        for texto, slot, estilo, ancho in acciones:
            boton = QPushButton(texto)
            boton.setObjectName(estilo)
            boton.setMinimumHeight(42)
            boton.setFixedWidth(ancho)
            boton.clicked.connect(slot)
            layout.addWidget(boton)

        layout.addStretch(1)
        return card

    def _crear_contenido_principal(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(self._crear_tabla_reglas(), 2)
        layout.addWidget(self._crear_editor_regla(), 3)
        return layout

    def _crear_tabla_reglas(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self._buscador = QLineEdit()
        self._buscador.setPlaceholderText("Buscar regla o tipologia")
        self._buscador.textChanged.connect(self._aplicar_filtro)
        layout.addWidget(self._buscador)

        self._tabla_reglas = QTableWidget(0, 5)
        self._tabla_reglas.setHorizontalHeaderLabels(["ACTIVA", "NOMBRE", "TIPOLOGIA", "PRIO.", "ESTADO"])
        encabezado = self._tabla_reglas.horizontalHeader()
        encabezado.setMinimumSectionSize(52)
        for columna, ancho in {0: 64, 3: 58, 4: 82}.items():
            encabezado.setSectionResizeMode(columna, QHeaderView.Fixed)
            self._tabla_reglas.setColumnWidth(columna, ancho)
        encabezado.setSectionResizeMode(1, QHeaderView.Stretch)
        encabezado.setSectionResizeMode(2, QHeaderView.Stretch)
        self._tabla_reglas.verticalHeader().setVisible(False)
        self._tabla_reglas.verticalHeader().setDefaultSectionSize(44)
        self._tabla_reglas.setAlternatingRowColors(True)
        self._tabla_reglas.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla_reglas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_reglas.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabla_reglas.setMinimumHeight(348)
        self._tabla_reglas.setWordWrap(False)
        self._tabla_reglas.itemSelectionChanged.connect(self._al_seleccionar_regla)
        layout.addWidget(self._tabla_reglas)

        pie = QHBoxLayout()
        self._lbl_paginacion = QLabel("Sin reglas")
        self._lbl_paginacion.setObjectName("textoSecundario")
        self._boton_anterior = self._boton_paginacion("<", self._pagina_anterior)
        self._lbl_pagina = QLabel("1")
        self._lbl_pagina.setObjectName("insigniaInfo")
        self._lbl_pagina.setAlignment(Qt.AlignCenter)
        self._lbl_pagina.setFixedWidth(34)
        self._boton_siguiente = self._boton_paginacion(">", self._pagina_siguiente)
        pie.addWidget(self._lbl_paginacion)
        pie.addStretch(1)
        pie.addWidget(self._boton_anterior)
        pie.addWidget(self._lbl_pagina)
        pie.addWidget(self._boton_siguiente)
        layout.addLayout(pie)
        return card

    def _crear_editor_regla(self) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        self._stack_editor = QStackedWidget()
        self._stack_editor.addWidget(self._crear_estado_vacio())
        self._stack_editor.addWidget(self._crear_formulario_editor())
        layout.addWidget(self._stack_editor)
        return card

    def _crear_estado_vacio(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(10)
        layout.addStretch(1)

        icono = QLabel("RL")
        icono.setObjectName("iconoHeader")
        icono.setFixedSize(60, 60)
        icono.setAlignment(Qt.AlignCenter)
        contenedor_icono = QHBoxLayout()
        contenedor_icono.addStretch(1)
        contenedor_icono.addWidget(icono)
        contenedor_icono.addStretch(1)
        layout.addLayout(contenedor_icono)

        titulo = QLabel("Ninguna regla seleccionada")
        titulo.setObjectName("tituloSubpanel")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)

        descripcion = QLabel(
            "Selecciona una regla en la tabla de la izquierda para editarla,\n"
            "o pulsa \"+ Nueva regla\" para empezar de cero."
        )
        descripcion.setObjectName("textoSecundario")
        descripcion.setAlignment(Qt.AlignCenter)
        descripcion.setWordWrap(True)
        layout.addWidget(descripcion)

        boton = QPushButton("+ Crear nueva regla")
        boton.setObjectName("botonPrincipal")
        boton.setMinimumHeight(42)
        boton.setFixedWidth(220)
        boton.clicked.connect(self._nueva_regla)
        contenedor_btn = QHBoxLayout()
        contenedor_btn.addStretch(1)
        contenedor_btn.addWidget(boton)
        contenedor_btn.addStretch(1)
        layout.addLayout(contenedor_btn)

        layout.addStretch(2)
        return widget

    def _crear_formulario_editor(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        titulo = QLabel("Editar regla seleccionada")
        titulo.setObjectName("tituloSubpanel")
        layout.addWidget(titulo)

        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)

        self._entrada_nombre = QLineEdit()
        self._entrada_nombre.setPlaceholderText("Ej: dispensacion_uci")
        self._entrada_nombre.textChanged.connect(self._actualizar_vista_previa)

        self._combo_tipologia = ComboScrollSafe()
        self._combo_tipologia.setEditable(True)
        self._combo_tipologia.lineEdit().setPlaceholderText("Ej: DISPENSACION_AL_PACIENTE")
        self._combo_tipologia.currentTextChanged.connect(self._actualizar_vista_previa)

        self._spin_prioridad = QSpinBox()
        self._spin_prioridad.setRange(0, 9999)
        self._spin_prioridad.valueChanged.connect(self._actualizar_vista_previa)
        self._check_activa = QCheckBox("Activa")
        self._check_activa.setChecked(True)

        self._agregar_campo_form(
            form, 0, 0, "Nombre interno", self._entrada_nombre,
            ayuda="Identificador unico, sin espacios."
        )
        self._agregar_campo_form(
            form, 0, 1, "Tipologia que asigna", self._combo_tipologia,
            ayuda="Resultado que toma el movimiento si la regla aplica."
        )
        self._agregar_campo_form(
            form, 1, 0, "Prioridad (menor = primero)", self._spin_prioridad,
            ayuda="Sugerido: 10 muy especifica, 50 general, 999 fallback."
        )
        self._agregar_campo_form(form, 1, 1, "Estado", self._check_activa)
        layout.addLayout(form)

        cab_cond = QHBoxLayout()
        lbl_cond = QLabel("Condiciones")
        lbl_cond.setObjectName("tituloSubpanel")
        nota = QLabel("todas deben cumplirse (AND)")
        nota.setObjectName("textoSecundario")
        cab_cond.addWidget(lbl_cond)
        cab_cond.addWidget(nota)
        cab_cond.addStretch(1)
        layout.addLayout(cab_cond)

        self._tabla_condiciones = QTableWidget(0, 4)
        self._tabla_condiciones.setHorizontalHeaderLabels(["CAMPO", "OPERADOR", "VALOR", ""])
        encabezado = self._tabla_condiciones.horizontalHeader()
        encabezado.setSectionResizeMode(0, QHeaderView.Stretch)
        encabezado.setSectionResizeMode(1, QHeaderView.Stretch)
        encabezado.setSectionResizeMode(2, QHeaderView.Stretch)
        encabezado.setSectionResizeMode(3, QHeaderView.Fixed)
        self._tabla_condiciones.setColumnWidth(3, 44)
        self._tabla_condiciones.verticalHeader().setVisible(False)
        self._tabla_condiciones.verticalHeader().setDefaultSectionSize(46)
        self._tabla_condiciones.setAlternatingRowColors(True)
        self._tabla_condiciones.setMinimumHeight(170)
        layout.addWidget(self._tabla_condiciones)

        ayuda_valor = QLabel(
            "Tip: para varios valores en el mismo campo, separelos con coma. "
            "Para listas reutilizables, elija \"esta en la lista\" y seleccione una lista del catalogo."
        )
        ayuda_valor.setObjectName("textoSecundario")
        ayuda_valor.setWordWrap(True)
        layout.addWidget(ayuda_valor)

        fila_condiciones = QHBoxLayout()
        agregar = QPushButton("+ Agregar condicion")
        agregar.setObjectName("botonSecundario")
        agregar.setMinimumHeight(36)
        agregar.clicked.connect(self._agregar_condicion_vacia)
        fila_condiciones.addWidget(agregar)
        fila_condiciones.addStretch(1)
        layout.addLayout(fila_condiciones)

        # Vista previa de la regla en lenguaje natural.
        self._panel_vista_previa = QFrame()
        self._panel_vista_previa.setObjectName("subbloquePanel")
        layout_vp = QVBoxLayout(self._panel_vista_previa)
        layout_vp.setContentsMargins(14, 12, 14, 12)
        layout_vp.setSpacing(4)
        titulo_vp = QLabel("Vista previa de la regla")
        titulo_vp.setObjectName("tituloBloque")
        self._lbl_vista_previa = QLabel("Configure los campos para ver la vista previa.")
        self._lbl_vista_previa.setObjectName("textoSecundario")
        self._lbl_vista_previa.setWordWrap(True)
        layout_vp.addWidget(titulo_vp)
        layout_vp.addWidget(self._lbl_vista_previa)
        layout.addWidget(self._panel_vista_previa)

        botones = QHBoxLayout()
        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("botonSecundario")
        cancelar.setMinimumHeight(42)
        cancelar.clicked.connect(self._cancelar_edicion)
        botones.addWidget(cancelar)
        duplicar = QPushButton("Duplicar")
        duplicar.setObjectName("botonSecundario")
        duplicar.setMinimumHeight(42)
        duplicar.setToolTip("Crea una copia editable de la regla seleccionada.")
        duplicar.clicked.connect(self._duplicar_regla_actual)
        eliminar = QPushButton("Eliminar")
        eliminar.setObjectName("botonPeligro")
        eliminar.setMinimumHeight(42)
        eliminar.setToolTip("Elimina definitivamente la regla seleccionada. Para pausarla, use el switch de la tabla.")
        eliminar.clicked.connect(self._eliminar_regla_actual)
        botones.addWidget(duplicar)
        botones.addWidget(eliminar)
        botones.addStretch(1)
        probar = QPushButton("Probar regla")
        probar.setObjectName("botonSecundario")
        probar.setMinimumHeight(42)
        probar.clicked.connect(self._probar_regla_actual)
        guardar = QPushButton("Guardar regla")
        guardar.setObjectName("botonPrincipal")
        guardar.setMinimumHeight(42)
        guardar.clicked.connect(self._guardar_regla)
        botones.addWidget(probar)
        botones.addWidget(guardar)
        layout.addLayout(botones)
        return widget

    def _crear_listas_apoyo(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(16)
        self._panel_articulos = self._crear_panel_listas("Listas de articulos", "ARTICULOS")
        self._panel_farmacias = self._crear_panel_listas("Listas de farmacias", "FARMACIAS")
        layout.addWidget(self._panel_articulos)
        layout.addWidget(self._panel_farmacias)
        return layout

    def _crear_panel_listas(self, titulo: str, tipo_lista: str) -> QFrame:
        card = QFrame()
        card.setObjectName("panelArchivo")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        cab = QHBoxLayout()
        lbl = QLabel(titulo)
        lbl.setObjectName("tituloSubpanel")
        boton = QPushButton("Nueva lista")
        boton.setObjectName("botonSecundario")
        boton.setMinimumHeight(34)
        boton.clicked.connect(lambda: self._crear_lista(tipo_lista))
        cab.addWidget(lbl)
        cab.addStretch(1)
        cab.addWidget(boton)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        setattr(self, f"_grid_{tipo_lista.lower()}", grid)

        layout.addLayout(cab)
        layout.addLayout(grid)
        return card

    def _crear_barra_inferior(self) -> QFrame:
        barra = QFrame()
        barra.setObjectName("barraInferior")
        barra.setMinimumHeight(68)
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        self._icono_estado = QLabel("i")
        self._icono_estado.setObjectName("iconoEstadoInfo")
        self._icono_estado.setFixedSize(30, 30)
        self._icono_estado.setAlignment(Qt.AlignCenter)

        self._lbl_estado = QLabel(
            "Las reglas se evaluan en orden de prioridad. La primera regla que cumpla sus condiciones se aplica al movimiento."
        )
        self._lbl_estado.setObjectName("mensajeCargaInfo")
        self._lbl_estado.setWordWrap(True)

        guia = QPushButton("Ver guia detallada")
        guia.setObjectName("botonSecundario")
        guia.setMinimumHeight(40)
        guia.clicked.connect(self._mostrar_guia)

        layout.addWidget(self._icono_estado)
        layout.addWidget(self._lbl_estado, 1)
        layout.addWidget(guia)
        return barra

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def _cargar_datos(self) -> None:
        try:
            with sesion_scope() as sesion:
                servicio_reglas = ServicioReglas(sesion)
                if not servicio_reglas.listar_reglas():
                    servicio_reglas.importar_desde_json(
                        resolver_ruta_proyecto("configuracion", "reglas_tipologia.json"),
                        solo_si_vacio=True,
                    )
                self._reglas = sorted(
                    servicio_reglas.listar_reglas(),
                    key=lambda regla: (regla.prioridad, regla.id),
                )
                self._listas = ServicioListas(sesion).listar_listas(activa=True)
                self._farmacias_bd = sorted(
                    {
                        normalizar_codigo(farmacia.codigo)
                        for farmacia in ServicioFarmacias(sesion).listar_farmacias(activa=True)
                        if normalizar_codigo(farmacia.codigo)
                    }
                )
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible cargar reglas: %s", error)
            self._reglas = []
            self._listas = []
            self._farmacias_bd = []
            self._mensaje_estado("No fue posible cargar las reglas.", "error")

        self._listas_por_id = {lista.id: lista for lista in self._listas}
        self._listas_por_codigo = {lista.codigo: lista for lista in self._listas}
        self._refrescar_combo_tipologia()
        self._aplicar_filtro()
        self._actualizar_listas_apoyo()
        if self._reglas and self._regla_actual_id is None and not self._editor_visible:
            # No autoseleccionamos: dejamos el estado vacio para que el usuario sepa que debe elegir.
            self._mostrar_estado_vacio()

    def _refrescar_combo_tipologia(self) -> None:
        if not hasattr(self, "_combo_tipologia"):
            return
        self._combo_tipologia.blockSignals(True)
        actual = self._combo_tipologia.currentText().strip()
        self._combo_tipologia.clear()
        tipologias = sorted({regla.tipologia_resultado for regla in self._reglas if regla.tipologia_resultado})
        for tipologia in tipologias:
            self._combo_tipologia.addItem(tipologia)
        if actual:
            self._combo_tipologia.setEditText(actual)
        self._combo_tipologia.blockSignals(False)

    # ------------------------------------------------------------------
    # Tabla de reglas
    # ------------------------------------------------------------------

    def _aplicar_filtro(self) -> None:
        texto = self._buscador.text().strip().lower() if hasattr(self, "_buscador") else ""
        self._reglas_filtradas = [
            indice
            for indice, regla in enumerate(self._reglas)
            if not texto
            or texto in regla.nombre.lower()
            or texto in regla.tipologia_resultado.lower()
            or texto in (regla.descripcion or "").lower()
        ]
        self._pagina_actual = min(max(self._pagina_actual, 1), self._total_paginas())
        self._actualizar_tabla_reglas()

    def _actualizar_tabla_reglas(self) -> None:
        self._tabla_reglas.blockSignals(True)
        self._tabla_reglas.setRowCount(0)
        inicio = (self._pagina_actual - 1) * _FILAS_REGLAS
        indices = self._reglas_filtradas[inicio : inicio + _FILAS_REGLAS]
        self._tabla_reglas.setRowCount(len(indices))

        for fila_tabla, indice_regla in enumerate(indices):
            regla = self._reglas[indice_regla]
            self._tabla_reglas.setCellWidget(fila_tabla, 0, self._celda_centrada(self._switch_tabla(regla)))
            self._set_item_regla(fila_tabla, 1, regla.nombre, regla.id)
            self._set_item_regla(fila_tabla, 2, regla.tipologia_resultado, regla.id)
            self._set_item_regla(fila_tabla, 3, str(regla.prioridad), regla.id, centro=True)
            self._tabla_reglas.setCellWidget(
                fila_tabla,
                4,
                self._celda_centrada(self._badge("Activa" if regla.activa else "Inactiva", regla.activa)),
            )
            self._tabla_reglas.setRowHeight(fila_tabla, 44)
            if regla.id == self._regla_actual_id:
                self._tabla_reglas.selectRow(fila_tabla)

        self._tabla_reglas.blockSignals(False)
        self._actualizar_paginacion()

    def _set_item_regla(self, fila: int, columna: int, texto: str, regla_id: int, centro: bool = False) -> None:
        item = QTableWidgetItem(texto)
        item.setData(Qt.UserRole, regla_id)
        item.setTextAlignment(Qt.AlignCenter if centro else Qt.AlignVCenter)
        self._tabla_reglas.setItem(fila, columna, item)

    def _switch_tabla(self, regla: ReglaClasificacionDTO) -> QCheckBox:
        switch = QCheckBox()
        switch.setChecked(regla.activa)
        switch.setToolTip("Activar o desactivar regla")
        switch.stateChanged.connect(lambda _estado, regla_id=regla.id: self._toggle_regla(regla_id))
        return switch

    def _badge(self, texto: str, activo: bool) -> QLabel:
        badge = QLabel(texto)
        badge.setObjectName("insigniaCorrecta" if activo else "insigniaNeutra")
        badge.setAlignment(Qt.AlignCenter)
        badge.setMinimumHeight(22)
        return badge

    def _al_seleccionar_regla(self) -> None:
        if self._bloqueando_eventos:
            return
        filas = self._tabla_reglas.selectionModel().selectedRows()
        if not filas:
            return
        item = self._tabla_reglas.item(filas[0].row(), 1)
        if item is not None:
            self._seleccionar_regla_por_id(int(item.data(Qt.UserRole)))

    def _seleccionar_regla_por_id(self, regla_id: int) -> None:
        regla = self._regla_por_id(regla_id)
        if regla is None:
            return
        self._mostrar_formulario()
        self._regla_actual_id = regla.id
        self._bloqueando_eventos = True
        self._entrada_nombre.setText(regla.nombre)
        self._combo_tipologia.setEditText(regla.tipologia_resultado)
        self._spin_prioridad.setValue(regla.prioridad)
        self._check_activa.setChecked(regla.activa)
        self._tabla_condiciones.setRowCount(0)
        for condicion in sorted(regla.condiciones, key=lambda c: c.orden):
            self._agregar_condicion(
                campo=condicion.campo,
                operador=condicion.operador,
                valor=self._valor_condicion(condicion.lista_id, condicion.valor_texto),
            )
        self._bloqueando_eventos = False
        self._actualizar_tabla_reglas()
        self._actualizar_vista_previa()
        self._animar_entrada(self._tabla_condiciones)

    def _regla_por_id(self, regla_id: int) -> ReglaClasificacionDTO | None:
        return next((regla for regla in self._reglas if regla.id == regla_id), None)

    # ------------------------------------------------------------------
    # Editor
    # ------------------------------------------------------------------

    def _mostrar_estado_vacio(self) -> None:
        self._editor_visible = False
        if hasattr(self, "_stack_editor"):
            self._stack_editor.setCurrentIndex(0)

    def _mostrar_formulario(self) -> None:
        self._editor_visible = True
        if hasattr(self, "_stack_editor"):
            self._stack_editor.setCurrentIndex(1)

    def _nueva_regla(self) -> None:
        self._mostrar_formulario()
        self._regla_actual_id = None
        self._bloqueando_eventos = True
        self._entrada_nombre.setText("")
        self._entrada_nombre.setPlaceholderText("Ej: dispensacion_uci")
        self._combo_tipologia.setEditText("")
        self._spin_prioridad.setValue(self._siguiente_prioridad())
        self._check_activa.setChecked(True)
        self._tabla_condiciones.setRowCount(0)
        self._agregar_condicion_vacia()
        self._tabla_reglas.clearSelection()
        self._bloqueando_eventos = False
        self._actualizar_vista_previa()
        self._mensaje_estado(
            "Defina nombre, tipologia, prioridad y al menos una condicion para guardar.",
            "info",
        )

    def _cancelar_edicion(self) -> None:
        self._regla_actual_id = None
        self._tabla_reglas.clearSelection()
        self._mostrar_estado_vacio()
        self._mensaje_estado("Edicion cancelada.", "neutro")

    def _agregar_condicion_vacia(self) -> None:
        self._agregar_condicion("TIPO_TRANSACCION", OperadorCondicion.IGUAL.value, "")

    def _agregar_condicion(self, campo: str, operador: str, valor: str) -> None:
        fila = self._tabla_condiciones.rowCount()
        self._tabla_condiciones.insertRow(fila)
        self._tabla_condiciones.setRowHeight(fila, 46)

        combo_campo = ComboScrollSafe()
        for clave, etiqueta, _ in _CATALOGO_CAMPOS:
            combo_campo.addItem(f"{clave} - {etiqueta}", clave)
        self._restaurar_combo_por_data(combo_campo, campo)
        combo_campo.currentIndexChanged.connect(
            lambda _idx, w=combo_campo: self._al_cambiar_campo(w)
        )

        combo_operador = ComboScrollSafe()
        self._poblar_operadores(combo_operador, campo)
        self._restaurar_combo_por_data(combo_operador, operador)
        combo_operador.currentIndexChanged.connect(
            lambda _idx, w=combo_operador: self._al_cambiar_operador(w)
        )

        combo_valor = self._crear_combo_valor(campo, operador, valor)

        eliminar = QPushButton("X")
        eliminar.setObjectName("botonTabla")
        eliminar.setFixedSize(30, 26)
        eliminar.setToolTip("Eliminar esta condicion")
        eliminar.clicked.connect(lambda: self._eliminar_condicion(eliminar))

        self._tabla_condiciones.setCellWidget(fila, 0, combo_campo)
        self._tabla_condiciones.setCellWidget(fila, 1, combo_operador)
        self._tabla_condiciones.setCellWidget(fila, 2, combo_valor)
        self._tabla_condiciones.setCellWidget(fila, 3, self._celda_centrada(eliminar, margen=4))

        self._actualizar_vista_previa()

    def _crear_combo_valor(self, campo: str, operador: str, valor: str) -> QComboBox:
        combo_valor = ComboScrollSafe()
        combo_valor.setEditable(True)
        combo_valor.lineEdit().setPlaceholderText(_EJEMPLO_CAMPO.get(campo, "Valor (use coma para varios)"))
        combo_valor.addItem("", None)
        for valor_org in self._valores_sugeridos_para_campo(campo):
            combo_valor.addItem(valor_org, None)
        for lista in self._listas:
            combo_valor.addItem(f"Lista: {lista.nombre} ({lista.codigo})", lista.id)
        self._restaurar_valor(combo_valor, valor)
        combo_valor.setEnabled(operador not in _OPERADORES_SIN_VALOR)
        combo_valor.currentTextChanged.connect(self._actualizar_vista_previa)
        return combo_valor

    def _poblar_operadores(self, combo: QComboBox, campo: str) -> None:
        combo.blockSignals(True)
        combo.clear()
        for clave in _operadores_para_campo(campo):
            combo.addItem(_ETIQUETA_OPERADOR.get(clave, clave), clave)
        combo.blockSignals(False)

    def _al_cambiar_campo(self, combo_campo: QComboBox) -> None:
        if self._bloqueando_eventos:
            return
        fila = self._localizar_fila_widget(combo_campo, columna=0)
        if fila is None:
            return
        nuevo_campo = combo_campo.currentData()
        combo_operador = self._tabla_condiciones.cellWidget(fila, 1)
        operador_actual = combo_operador.currentData() if isinstance(combo_operador, QComboBox) else OperadorCondicion.IGUAL.value
        if isinstance(combo_operador, QComboBox):
            self._poblar_operadores(combo_operador, nuevo_campo)
            self._restaurar_combo_por_data(combo_operador, operador_actual)
            operador_actual = combo_operador.currentData()
        combo_valor = self._tabla_condiciones.cellWidget(fila, 2)
        if isinstance(combo_valor, QComboBox):
            valor_actual = combo_valor.currentText().strip()
            nuevo_combo_valor = self._crear_combo_valor(nuevo_campo, operador_actual, valor_actual)
            self._tabla_condiciones.setCellWidget(fila, 2, nuevo_combo_valor)
        self._actualizar_vista_previa()

    def _valores_sugeridos_para_campo(self, campo: str) -> list[str]:
        if campo not in {"ORG_DESTINO", "ORG_ORIGEN"}:
            return []

        valores: set[str] = set(self._farmacias_bd)
        dataframe = self._dataframe_provider() if self._dataframe_provider is not None else None
        if campo == "ORG_DESTINO":
            valores.update(extraer_farmacias_org_destino(dataframe))
        else:
            valores.update(extraer_farmacias_org_origen(dataframe))
        return sorted(valor for valor in valores if valor)

    def recargar_listas_farmacias(self) -> None:
        """Recarga listas/farmacias para combos sin tocar el editor actual."""
        try:
            with sesion_scope() as sesion:
                self._listas = ServicioListas(sesion).listar_listas(activa=True)
                self._farmacias_bd = sorted(
                    {
                        normalizar_codigo(farmacia.codigo)
                        for farmacia in ServicioFarmacias(sesion).listar_farmacias(activa=True)
                        if normalizar_codigo(farmacia.codigo)
                    }
                )
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible recargar listas/farmacias: %s", error)
            return
        self._listas_por_id = {lista.id: lista for lista in self._listas}
        self._listas_por_codigo = {lista.codigo: lista for lista in self._listas}
        self._actualizar_combos_valor_existentes()

    def _actualizar_combos_valor_existentes(self) -> None:
        if not hasattr(self, "_tabla_condiciones"):
            return
        for fila in range(self._tabla_condiciones.rowCount()):
            combo_campo = self._tabla_condiciones.cellWidget(fila, 0)
            combo_operador = self._tabla_condiciones.cellWidget(fila, 1)
            combo_valor = self._tabla_condiciones.cellWidget(fila, 2)
            if not all(isinstance(w, QComboBox) for w in (combo_campo, combo_operador, combo_valor)):
                continue
            campo = str(combo_campo.currentData() or "")
            operador = str(combo_operador.currentData() or OperadorCondicion.IGUAL.value)
            valor = combo_valor.currentText().strip()
            self._tabla_condiciones.setCellWidget(fila, 2, self._crear_combo_valor(campo, operador, valor))
        self._actualizar_vista_previa()

    def _al_cambiar_operador(self, combo_operador: QComboBox) -> None:
        if self._bloqueando_eventos:
            return
        fila = self._localizar_fila_widget(combo_operador, columna=1)
        if fila is None:
            return
        operador = combo_operador.currentData()
        combo_valor = self._tabla_condiciones.cellWidget(fila, 2)
        if isinstance(combo_valor, QComboBox):
            combo_valor.setEnabled(operador not in _OPERADORES_SIN_VALOR)
        self._actualizar_vista_previa()

    def _localizar_fila_widget(self, widget: QWidget, columna: int) -> int | None:
        for fila in range(self._tabla_condiciones.rowCount()):
            if self._tabla_condiciones.cellWidget(fila, columna) is widget:
                return fila
        return None

    def _eliminar_condicion(self, boton: QPushButton) -> None:
        for fila in range(self._tabla_condiciones.rowCount()):
            contenedor = self._tabla_condiciones.cellWidget(fila, 3)
            if contenedor and contenedor.findChild(QPushButton) is boton:
                self._tabla_condiciones.removeRow(fila)
                self._actualizar_vista_previa()
                return

    def _guardar_regla(self) -> None:
        nombre = self._entrada_nombre.text().strip()
        tipologia = self._combo_tipologia.currentText().strip()
        condiciones = self._leer_condiciones_editor()
        if not nombre or not tipologia:
            self._mensaje_estado("Nombre y tipologia son obligatorios.", "advertencia")
            return
        if not condiciones:
            self._mensaje_estado("Agregue al menos una condicion.", "advertencia")
            return

        datos = ReglaClasificacionCrearDTO(
            nombre=nombre,
            descripcion="Editada desde la interfaz.",
            tipologia_resultado=tipologia,
            prioridad=int(self._spin_prioridad.value()),
            activa=self._check_activa.isChecked(),
            origen="CREADA_UI" if self._regla_actual_id is None else "SISTEMA",
            condiciones=condiciones,
        )

        try:
            with sesion_scope() as sesion:
                regla = ServicioReglas(sesion).guardar_regla_con_condiciones(
                    self._regla_actual_id,
                    datos,
                )
        except ErrorDominio as error:
            self._mensaje_estado(str(error), "error")
            QMessageBox.warning(self, "No fue posible guardar", str(error))
            return
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible guardar la regla: %s", error)
            self._mensaje_estado("No fue posible guardar la regla.", "error")
            QMessageBox.critical(
                self,
                "Error al guardar",
                "No fue posible guardar la regla. Revise los datos e intente nuevamente.",
            )
            return

        self._regla_actual_id = regla.id
        self._mensaje_estado("Regla guardada correctamente.", "correcto")
        self._cargar_datos()
        self._seleccionar_regla_por_id(regla.id)
        self.cambios_configuracion.emit("reglas")
        QMessageBox.information(
            self,
            "Regla guardada",
            f"La regla \"{regla.nombre}\" se guardo correctamente.",
        )

    def _leer_condiciones_editor(self) -> list[CondicionReglaCrearDTO]:
        condiciones: list[CondicionReglaCrearDTO] = []
        for fila in range(self._tabla_condiciones.rowCount()):
            combo_campo = self._tabla_condiciones.cellWidget(fila, 0)
            combo_operador = self._tabla_condiciones.cellWidget(fila, 1)
            combo_valor = self._tabla_condiciones.cellWidget(fila, 2)
            if not isinstance(combo_campo, QComboBox) or not isinstance(combo_operador, QComboBox):
                continue
            if not isinstance(combo_valor, QComboBox):
                continue
            campo = str(combo_campo.currentData() or combo_campo.currentText())
            operador = str(combo_operador.currentData() or combo_operador.currentText())
            lista_id = combo_valor.currentData()
            valor_texto = combo_valor.currentText().strip()

            if operador in _OPERADORES_SIN_VALOR:
                lista_id = None
                valor_texto_payload = None
            elif lista_id is not None:
                if operador not in _OPERADORES_LISTA:
                    operador = OperadorCondicion.EN_LISTA.value
                valor_texto_payload = None
            else:
                # Permitir varios valores separados por coma para operadores tipo IGUAL/CONTIENE/etc.
                valores = [v.strip() for v in valor_texto.split(",") if v.strip()]
                if not valores:
                    valores = [valor_texto] if valor_texto else []
                valor_texto_payload = json.dumps(valores, ensure_ascii=False) if valores else json.dumps([""], ensure_ascii=False)

            condiciones.append(
                CondicionReglaCrearDTO(
                    campo=campo,
                    operador=operador,
                    valor_texto=valor_texto_payload,
                    lista_id=int(lista_id) if lista_id is not None else None,
                    orden=fila,
                    activa=True,
                )
            )
        return condiciones

    def _actualizar_vista_previa(self) -> None:
        if not hasattr(self, "_lbl_vista_previa"):
            return
        nombre = self._entrada_nombre.text().strip() or "(sin nombre)"
        tipologia = self._combo_tipologia.currentText().strip() or "(sin tipologia)"
        prioridad = self._spin_prioridad.value()

        partes_condiciones: list[str] = []
        for fila in range(self._tabla_condiciones.rowCount()):
            combo_campo = self._tabla_condiciones.cellWidget(fila, 0)
            combo_operador = self._tabla_condiciones.cellWidget(fila, 1)
            combo_valor = self._tabla_condiciones.cellWidget(fila, 2)
            if not isinstance(combo_campo, QComboBox) or not isinstance(combo_operador, QComboBox):
                continue
            campo = combo_campo.currentData() or combo_campo.currentText()
            operador = combo_operador.currentData() or combo_operador.currentText()
            etiqueta_op = _ETIQUETA_OPERADOR.get(operador, operador.lower())

            if operador in _OPERADORES_SIN_VALOR:
                partes_condiciones.append(f"{campo} {etiqueta_op}")
                continue

            valor = ""
            if isinstance(combo_valor, QComboBox):
                lista_id = combo_valor.currentData()
                if lista_id is not None and lista_id in self._listas_por_id:
                    valor = f"\"{self._listas_por_id[lista_id].nombre}\""
                else:
                    texto = combo_valor.currentText().strip()
                    if texto:
                        valor = f"\"{texto}\""
            if not valor:
                valor = "(sin valor)"
            partes_condiciones.append(f"{campo} {etiqueta_op} {valor}")

        if not partes_condiciones:
            cuerpo = "Aun no hay condiciones."
        else:
            cuerpo = "\n".join(f"  - {parte}" for parte in partes_condiciones)

        texto = (
            f"Si TODAS las condiciones siguientes se cumplen:\n"
            f"{cuerpo}\n"
            f"entonces el movimiento se clasifica como \"{tipologia}\" "
            f"(regla \"{nombre}\", prioridad {prioridad})."
        )
        self._lbl_vista_previa.setText(texto)

    def _toggle_regla(self, regla_id: int) -> None:
        regla = self._regla_por_id(regla_id)
        if regla is None:
            return
        try:
            with sesion_scope() as sesion:
                ServicioReglas(sesion).actualizar_regla(
                    regla_id,
                    ReglaClasificacionActualizarDTO(activa=not regla.activa),
                )
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cambiar estado de regla: %s", error)
            self._mensaje_estado("No fue posible cambiar el estado de la regla.", "error")
            return
        self._cargar_datos()
        self.cambios_configuracion.emit("reglas")

    def _duplicar_regla_actual(self) -> None:
        if self._regla_actual_id is None:
            self._mensaje_estado("Seleccione una regla para duplicarla.", "advertencia")
            return
        regla = self._regla_por_id(self._regla_actual_id)
        nombre_base = f"{regla.nombre}_copia" if regla is not None else "regla_copia"
        nuevo_nombre, aceptado = QInputDialog.getText(
            self,
            "Duplicar regla",
            "Nombre de la copia:",
            text=nombre_base,
        )
        nuevo_nombre = nuevo_nombre.strip()
        if not aceptado or not nuevo_nombre:
            return

        try:
            with sesion_scope() as sesion:
                copia = ServicioReglas(sesion).duplicar_regla(self._regla_actual_id, nuevo_nombre)
        except ErrorDominio as error:
            self._mensaje_estado(str(error), "error")
            QMessageBox.warning(self, "No fue posible duplicar", str(error))
            return
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible duplicar la regla: %s", error)
            self._mensaje_estado("No fue posible duplicar la regla.", "error")
            QMessageBox.critical(self, "Error al duplicar", "No fue posible duplicar la regla.")
            return

        self._regla_actual_id = copia.id
        self._mensaje_estado("Regla duplicada correctamente.", "correcto")
        self._cargar_datos()
        self._seleccionar_regla_por_id(copia.id)
        QMessageBox.information(
            self,
            "Regla duplicada",
            f"La copia \"{copia.nombre}\" se creo correctamente.",
        )

    def _eliminar_regla_actual(self) -> None:
        if self._regla_actual_id is None:
            self._mensaje_estado("Seleccione una regla para eliminarla.", "advertencia")
            return
        regla = self._regla_por_id(self._regla_actual_id)
        nombre = regla.nombre if regla is not None else f"#{self._regla_actual_id}"
        confirmacion = QMessageBox.question(
            self,
            "Eliminar regla",
            f"La regla \"{nombre}\" se eliminara definitivamente. Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return

        try:
            with sesion_scope() as sesion:
                ServicioReglas(sesion).eliminar_regla(self._regla_actual_id)
        except ErrorDominio as error:
            self._mensaje_estado(str(error), "error")
            QMessageBox.warning(self, "No fue posible eliminar", str(error))
            return
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible eliminar la regla: %s", error)
            self._mensaje_estado("No fue posible eliminar la regla.", "error")
            QMessageBox.critical(self, "Error al eliminar", "No fue posible eliminar la regla.")
            return

        self._regla_actual_id = None
        self._mostrar_estado_vacio()
        self._mensaje_estado("Regla eliminada correctamente.", "correcto")
        self._cargar_datos()
        self.cambios_configuracion.emit("reglas")
        QMessageBox.information(
            self,
            "Regla eliminada",
            f"La regla \"{nombre}\" se elimino correctamente.",
        )

    # ------------------------------------------------------------------
    # Acciones superiores
    # ------------------------------------------------------------------

    def _importar_reglas_excel(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Importar reglas desde Excel",
            "",
            "Archivos Excel (*.xlsx *.xls)",
        )
        if not ruta:
            return
        try:
            dataframe = pd.read_excel(ruta)
            reglas = self._reglas_desde_dataframe(dataframe)
            with sesion_scope() as sesion:
                servicio = ServicioReglas(sesion)
                creadas = 0
                for regla in reglas:
                    servicio.guardar_regla_con_condiciones(None, regla)
                    creadas += 1
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible importar reglas: %s", error)
            self._mensaje_estado("No fue posible importar el Excel de reglas.", "error")
            return
        self._mensaje_estado(f"{creadas} reglas importadas correctamente.", "correcto")
        self._cargar_datos()
        self.cambios_configuracion.emit("reglas")

    def _restaurar_reglas_base(self) -> None:
        confirmacion = QMessageBox.question(
            self,
            "Restaurar reglas base",
            "Se cargaran las reglas predeterminadas que no esten ya en el sistema. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        try:
            with sesion_scope() as sesion:
                creadas = ServicioReglas(sesion).importar_desde_json(
                    resolver_ruta_proyecto("configuracion", "reglas_tipologia.json"),
                    solo_si_vacio=False,
                )
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible restaurar reglas base: %s", error)
            self._mensaje_estado("No fue posible restaurar las reglas base.", "error")
            return
        self._mensaje_estado(f"Reglas base revisadas. Nuevas creadas: {len(creadas)}.", "correcto")
        self._cargar_datos()
        self.cambios_configuracion.emit("reglas")

    def _probar_reglas(self) -> None:
        activas = sum(1 for regla in self._reglas if regla.activa)
        QMessageBox.information(
            self,
            "Prueba de reglas",
            f"Hay {activas} reglas activas listas para evaluar movimientos.",
        )

    def _probar_regla_actual(self) -> None:
        condiciones = len(self._leer_condiciones_editor())
        QMessageBox.information(
            self,
            "Prueba de regla",
            f"La regla actual tiene {condiciones} condiciones configuradas.",
        )

    def _crear_lista(self, tipo_lista: str) -> None:
        nombre, aceptado = QInputDialog.getText(self, "Nueva lista", "Nombre de la lista:")
        nombre = nombre.strip()
        if not aceptado or not nombre:
            return
        codigo = normalizar_codigo(nombre)
        try:
            with sesion_scope() as sesion:
                ServicioListas(sesion).crear_lista(
                    ListaConfigurableCrearDTO(codigo=codigo, nombre=nombre, tipo_lista=tipo_lista)
                )
        except ErrorDominio as error:
            self._mensaje_estado(str(error), "error")
            QMessageBox.warning(self, "No fue posible crear la lista", str(error))
            return
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible crear lista: %s", error)
            self._mensaje_estado("No fue posible crear la lista.", "error")
            QMessageBox.critical(self, "Error al crear lista", "No fue posible crear la lista.")
            return
        self._mensaje_estado("Lista creada correctamente.", "correcto")
        self._cargar_datos()
        self.cambios_configuracion.emit("listas")
        QMessageBox.information(
            self,
            "Lista creada",
            f"La lista \"{nombre}\" se creo correctamente.",
        )

    # ------------------------------------------------------------------
    # Listas apoyo
    # ------------------------------------------------------------------

    def _actualizar_listas_apoyo(self) -> None:
        self._llenar_grid_listas(getattr(self, "_grid_articulos"), "ARTICULOS")
        self._llenar_grid_listas(getattr(self, "_grid_farmacias"), "FARMACIAS")

    def _llenar_grid_listas(self, grid: QGridLayout, tipo_lista: str) -> None:
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        listas = [lista for lista in self._listas if lista.tipo_lista == tipo_lista]
        for indice, lista in enumerate(listas[:5]):
            grid.addWidget(self._tarjeta_lista(lista), indice // 3, indice % 3)
        if len(listas) > 5:
            grid.addWidget(self._tarjeta_ver_todas(len(listas)), 1, 2)
        elif not listas:
            vacio = QLabel("Sin listas configuradas")
            vacio.setObjectName("textoSecundario")
            grid.addWidget(vacio, 0, 0)

    def _tarjeta_lista(self, lista: ListaConfigurableDTO) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        card.setMinimumHeight(64)
        card.setCursor(Qt.PointingHandCursor)
        card.setToolTip("Abrir editor de items")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)
        titulo = QLabel(lista.nombre)
        titulo.setObjectName("valorCampo")
        detalle = QLabel(f"{self._contar_items_lista(lista.id)} items")
        detalle.setObjectName("textoSecundario")
        layout.addWidget(titulo)
        layout.addWidget(detalle)
        card.mousePressEvent = lambda _event, lista=lista: self._editar_lista(lista)  # type: ignore[method-assign]
        return card

    def _editar_lista(self, lista: ListaConfigurableDTO) -> None:
        dialogo = DialogoEditarLista(lista, self)
        dialogo.exec()
        self._cargar_datos()
        if dialogo.hubo_cambios():
            self.cambios_configuracion.emit("listas")

    def _tarjeta_ver_todas(self, total: int) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        titulo = QLabel("Ver todas")
        titulo.setObjectName("valorCampo")
        detalle = QLabel(f"{total} listas")
        detalle.setObjectName("textoSecundario")
        layout.addWidget(titulo)
        layout.addWidget(detalle)
        return card

    def _contar_items_lista(self, lista_id: int) -> int:
        try:
            with sesion_scope() as sesion:
                return len(ServicioListas(sesion).listar_items(lista_id, activos=True))
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _agregar_campo_form(
        self,
        form: QGridLayout,
        fila: int,
        columna: int,
        etiqueta: str,
        widget: QWidget,
        ayuda: str | None = None,
    ) -> None:
        contenedor = QVBoxLayout()
        contenedor.setSpacing(2)
        lbl = QLabel(etiqueta)
        lbl.setObjectName("tituloBloque")
        contenedor.addWidget(lbl)
        contenedor.addWidget(widget)
        if ayuda:
            lbl_ayuda = QLabel(ayuda)
            lbl_ayuda.setObjectName("textoSecundario")
            lbl_ayuda.setWordWrap(True)
            contenedor.addWidget(lbl_ayuda)
        form.addLayout(contenedor, fila, columna)

    def _boton_paginacion(self, texto: str, slot) -> QPushButton:
        boton = QPushButton(texto)
        boton.setObjectName("botonTerciario")
        boton.setFixedSize(34, 32)
        boton.clicked.connect(slot)
        return boton

    def _pagina_anterior(self) -> None:
        self._pagina_actual = max(1, self._pagina_actual - 1)
        self._actualizar_tabla_reglas()

    def _pagina_siguiente(self) -> None:
        self._pagina_actual = min(self._total_paginas(), self._pagina_actual + 1)
        self._actualizar_tabla_reglas()

    def _actualizar_paginacion(self) -> None:
        total = len(self._reglas_filtradas)
        total_paginas = self._total_paginas()
        inicio = 0 if total == 0 else (self._pagina_actual - 1) * _FILAS_REGLAS + 1
        fin = min(self._pagina_actual * _FILAS_REGLAS, total)
        self._lbl_paginacion.setText(
            "Sin reglas" if total == 0 else f"Mostrando {inicio} a {fin} de {total} reglas"
        )
        self._lbl_pagina.setText(str(self._pagina_actual))
        self._boton_anterior.setEnabled(self._pagina_actual > 1)
        self._boton_siguiente.setEnabled(self._pagina_actual < total_paginas)

    def _total_paginas(self) -> int:
        if not self._reglas_filtradas:
            return 1
        return ((len(self._reglas_filtradas) - 1) // _FILAS_REGLAS) + 1

    def _siguiente_prioridad(self) -> int:
        return max((regla.prioridad for regla in self._reglas), default=0) + 1

    def _celda_centrada(self, widget: QWidget, margen: int = 6) -> QWidget:
        cont = QWidget()
        layout = QHBoxLayout(cont)
        layout.setContentsMargins(margen, 3, margen, 3)
        layout.setSpacing(0)
        layout.addWidget(widget)
        return cont

    def _restaurar_combo_por_data(self, combo: QComboBox, valor: Any) -> None:
        if valor is None:
            combo.setCurrentIndex(0)
            return
        for indice in range(combo.count()):
            if combo.itemData(indice) == valor or combo.itemText(indice) == str(valor):
                combo.setCurrentIndex(indice)
                return
        # Si el valor no esta en el combo de campos, intentar texto.
        idx = combo.findText(str(valor))
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _restaurar_valor(self, combo: QComboBox, valor: str) -> None:
        for indice in range(combo.count()):
            if str(combo.itemData(indice)) == valor or combo.itemText(indice) == valor:
                combo.setCurrentIndex(indice)
                return
        combo.setCurrentText(valor)

    def _valor_condicion(self, lista_id: int | None, valor_texto: str | None) -> str:
        if lista_id is not None:
            return str(lista_id)
        if not valor_texto:
            return ""
        try:
            valor = json.loads(valor_texto)
            if isinstance(valor, list):
                return ", ".join(str(v) for v in valor)
            return str(valor)
        except json.JSONDecodeError:
            return valor_texto

    def _reglas_desde_dataframe(self, dataframe: pd.DataFrame) -> list[ReglaClasificacionCrearDTO]:
        requeridas = {"NOMBRE", "TIPOLOGIA", "CAMPO", "OPERADOR"}
        columnas = {str(col).strip().upper(): col for col in dataframe.columns}
        if not requeridas.issubset(columnas):
            raise ValueError("El Excel debe tener columnas NOMBRE, TIPOLOGIA, CAMPO y OPERADOR.")

        reglas: list[ReglaClasificacionCrearDTO] = []
        for nombre, grupo in dataframe.groupby(columnas["NOMBRE"]):
            condiciones: list[CondicionReglaCrearDTO] = []
            primera = grupo.iloc[0]
            for orden, (_idx, fila) in enumerate(grupo.iterrows()):
                lista_id = None
                valor = str(fila.get(columnas.get("VALOR"), "") or "").strip()
                codigo_lista = str(fila.get(columnas.get("LISTA_CODIGO"), "") or "").strip()
                if codigo_lista and codigo_lista in self._listas_por_codigo:
                    lista_id = self._listas_por_codigo[codigo_lista].id
                condiciones.append(
                    CondicionReglaCrearDTO(
                        campo=str(fila[columnas["CAMPO"]]),
                        operador=str(fila[columnas["OPERADOR"]]),
                        valor_texto=None if lista_id is not None else json.dumps([valor], ensure_ascii=False),
                        lista_id=lista_id,
                        orden=orden,
                    )
                )
            reglas.append(
                ReglaClasificacionCrearDTO(
                    nombre=str(nombre),
                    tipologia_resultado=str(primera[columnas["TIPOLOGIA"]]),
                    prioridad=int(primera.get(columnas.get("PRIORIDAD"), 100) or 100),
                    activa=bool(primera.get(columnas.get("ACTIVA"), True)),
                    origen="EXCEL_IMPORTADO",
                    condiciones=condiciones,
                )
            )
        return reglas

    def _mensaje_estado(self, mensaje: str, tipo: str) -> None:
        iconos = {"correcto": "OK", "error": "X", "advertencia": "!", "info": "i", "neutro": "-"}
        nombres_icono = {
            "correcto": "iconoEstadoCorrecto",
            "error": "iconoEstadoError",
            "advertencia": "iconoEstadoAdvertencia",
            "info": "iconoEstadoInfo",
            "neutro": "iconoEstadoNeutro",
        }
        nombres_texto = {
            "correcto": "mensajeEstado",
            "error": "mensajeEstadoError",
            "advertencia": "mensajeEstadoAdvertencia",
            "info": "mensajeCargaInfo",
            "neutro": "mensajeEstadoNeutro",
        }
        self._icono_estado.setText(iconos.get(tipo, "i"))
        self._icono_estado.setObjectName(nombres_icono.get(tipo, "iconoEstadoInfo"))
        self._lbl_estado.setText(mensaje)
        self._lbl_estado.setObjectName(nombres_texto.get(tipo, "mensajeCargaInfo"))
        self._aplicar_estilo(self._icono_estado)
        self._aplicar_estilo(self._lbl_estado)

    def _mostrar_guia(self) -> None:
        QMessageBox.information(
            self,
            "Guia de reglas",
            (
                "Como crear una regla:\n\n"
                "1. Defina un nombre interno corto y unico (sin espacios).\n"
                "2. Indique la tipologia que recibira el movimiento (puede elegir una existente o crear una nueva).\n"
                "3. Asigne una prioridad: numeros mas bajos se evaluan primero. La primera regla que coincida gana.\n"
                "4. Agregue condiciones; todas deben cumplirse (operador AND).\n\n"
                "Para varios valores en la misma condicion separelos con coma (ej. \"16_FARMA, 47_FARMA\").\n"
                "Para listas reutilizables use el operador \"esta en la lista\" y selecciono una lista del catalogo.\n\n"
                "La vista previa muestra como se leera la regla en lenguaje natural."
            ),
        )

    def _animar_entrada(self, widget: QWidget) -> None:
        efecto = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(efecto)
        animacion = QPropertyAnimation(efecto, b"opacity", widget)
        animacion.setDuration(220)
        animacion.setStartValue(0.0)
        animacion.setEndValue(1.0)
        animacion.setEasingCurve(QEasingCurve.OutCubic)
        animacion.finished.connect(lambda: widget.setGraphicsEffect(None))
        animacion.start()
        self._animaciones.append(animacion)

    def _aplicar_estilo(self, widget: QWidget) -> None:
        if self.style():
            self.style().unpolish(widget)
            self.style().polish(widget)
