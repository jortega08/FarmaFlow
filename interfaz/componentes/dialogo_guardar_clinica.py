"""Dialogo post-importacion para asociar farmacias detectadas a una clinica."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dto.clinica_dto import ClinicaCrearDTO, ClinicaDTO
from interfaz.componentes.combo_scroll_safe import ComboScrollSafe
from persistencia.conexion import sesion_scope
from servicios.excepciones import ErrorDominio
from servicios.servicio_clinicas import ServicioClinicas
from servicios.servicio_farmacias import ServicioFarmacias
from utilidades.texto import normalizar_codigo, normalizar_nombre_columna


@dataclass(slots=True)
class ResultadoGuardarClinica:
    """Resultado de la confirmacion del dialogo."""

    confirmado: bool
    clinica_id: int | None = None
    clinica_nombre: str = ""
    farmacias_creadas: int = 0
    farmacias_asociadas: int = 0


@dataclass(slots=True)
class FarmaciaRevision:
    """Decision editable sobre una farmacia detectada en el archivo."""

    codigo: str
    origen: str
    tipo_codigo: str
    conocida: bool
    puede_prestar: bool
    guardar: bool = True
    farmacia_id: int | None = None


def extraer_valores_organizacion(dataframe: pd.DataFrame | None, columna: str) -> list[str]:
    """Devuelve los valores unicos no vacios de una columna organizacional."""
    if dataframe is None:
        return []
    columnas_por_nombre = {normalizar_nombre_columna(col): col for col in dataframe.columns}
    columna_real = columnas_por_nombre.get(normalizar_nombre_columna(columna))
    if columna_real is None:
        return []
    serie = dataframe[columna_real].dropna().astype(str).str.strip()
    valores = sorted({normalizar_codigo(valor) for valor in serie if normalizar_codigo(valor)})
    return valores


def extraer_farmacias_org_destino(dataframe: pd.DataFrame | None) -> list[str]:
    """Devuelve los valores unicos no vacios de la columna ORG_DESTINO."""
    return extraer_valores_organizacion(dataframe, "ORG_DESTINO")


def extraer_farmacias_org_origen(dataframe: pd.DataFrame | None) -> list[str]:
    """Devuelve los valores unicos no vacios de la columna ORG_ORIGEN."""
    return extraer_valores_organizacion(dataframe, "ORG_ORIGEN")


class DialogoGuardarClinica(QDialog):
    """Pregunta al usuario si desea persistir farmacias detectadas y la clinica asociada."""

    def __init__(
        self,
        farmacias_detectadas: list[str],
        farmacias_origen: list[str] | None = None,
        clinicas_existentes: list[ClinicaDTO] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._farmacias_destino = list(farmacias_detectadas)
        self._farmacias_origen = list(farmacias_origen or [])
        self._farmacias = self._construir_revisiones_farmacias()
        self._clinicas_existentes = list(clinicas_existentes or [])
        self._resultado = ResultadoGuardarClinica(confirmado=False)

        self.setWindowTitle("Guardar datos en el sistema")
        self.setMinimumWidth(560)
        self.setMinimumHeight(520)

        self._construir_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _construir_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        titulo = QLabel("Guardar farmacias y clinica en el sistema")
        titulo.setObjectName("tituloSubpanel")
        layout.addWidget(titulo)

        descripcion = QLabel(
            "Detectamos organizaciones en ORG_DESTINO y ORG_ORIGEN. "
            "Las de ORG_DESTINO se sugieren como internas; las que aparecen solo en ORG_ORIGEN "
            "se sugieren como externas para revision antes de guardarlas."
        )
        descripcion.setObjectName("textoSecundario")
        descripcion.setWordWrap(True)
        layout.addWidget(descripcion)

        layout.addWidget(self._crear_seleccion_clinica())
        layout.addWidget(self._crear_tabla_farmacias(), 1)
        layout.addWidget(self._crear_botones())

        self._actualizar_estado_combo()

    def _crear_seleccion_clinica(self) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        encabezado = QLabel("Clinica a asociar")
        encabezado.setObjectName("tituloBloque")
        layout.addWidget(encabezado)

        fila = QHBoxLayout()
        fila.setSpacing(10)

        self._combo_clinica = ComboScrollSafe()
        self._combo_clinica.setMinimumHeight(36)
        self._combo_clinica.addItem("- Crear nueva clinica -", None)
        for clinica in self._clinicas_existentes:
            self._combo_clinica.addItem(clinica.nombre, clinica.id)
        self._combo_clinica.currentIndexChanged.connect(self._actualizar_estado_combo)
        fila.addWidget(self._combo_clinica, 1)

        self._entrada_nombre = QLineEdit()
        self._entrada_nombre.setPlaceholderText("Nombre de la nueva clinica (ej. Clinica del Country)")
        self._entrada_nombre.setMinimumHeight(36)
        fila.addWidget(self._entrada_nombre, 1)

        layout.addLayout(fila)
        ayuda = QLabel(
            "Si la clinica ya existe, seleccionela del listado. "
            "Para crear una nueva, deje seleccionado \"Crear nueva clinica\" e ingrese su nombre."
        )
        ayuda.setObjectName("textoSecundario")
        ayuda.setWordWrap(True)
        layout.addWidget(ayuda)
        return card

    def _crear_tabla_farmacias(self) -> QFrame:
        card = QFrame()
        card.setObjectName("subbloquePanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        cab = QHBoxLayout()
        encabezado = QLabel(f"Farmacias detectadas ({len(self._farmacias)})")
        encabezado.setObjectName("tituloBloque")
        cab.addWidget(encabezado)
        cab.addStretch(1)
        seleccionar_todo = QCheckBox("Marcar todas")
        seleccionar_todo.setChecked(True)
        seleccionar_todo.toggled.connect(self._toggle_todas)
        cab.addWidget(seleccionar_todo)
        layout.addLayout(cab)

        self._tabla = QTableWidget(len(self._farmacias), 6)
        self._tabla.setHorizontalHeaderLabels(
            ["GUARDAR", "CODIGO / NOMBRE", "ORIGEN", "TIPO", "HISTORIAL", "PRESTA"]
        )
        encabezado_tabla = self._tabla.horizontalHeader()
        encabezado_tabla.setSectionResizeMode(0, QHeaderView.Fixed)
        self._tabla.setColumnWidth(0, 72)
        encabezado_tabla.setSectionResizeMode(1, QHeaderView.Stretch)
        for columna, ancho in {2: 100, 3: 140, 4: 92, 5: 86}.items():
            encabezado_tabla.setSectionResizeMode(columna, QHeaderView.Fixed)
            self._tabla.setColumnWidth(columna, ancho)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionMode(QAbstractItemView.NoSelection)
        self._tabla.setAlternatingRowColors(True)

        for fila, revision in enumerate(self._farmacias):
            checkbox = QCheckBox()
            checkbox.setChecked(revision.guardar)
            cont = QWidget()
            cont_layout = QHBoxLayout(cont)
            cont_layout.setContentsMargins(8, 0, 0, 0)
            cont_layout.addWidget(checkbox)
            self._tabla.setCellWidget(fila, 0, cont)
            item = QTableWidgetItem(revision.codigo)
            self._tabla.setItem(fila, 1, item)
            self._tabla.setItem(fila, 2, QTableWidgetItem(revision.origen))
            self._tabla.setCellWidget(fila, 3, self._combo_tipo(revision.tipo_codigo))
            self._tabla.setItem(fila, 4, QTableWidgetItem("Conocida" if revision.conocida else "Nueva"))
            self._tabla.setCellWidget(fila, 5, self._combo_presta(revision.puede_prestar))
            self._tabla.setRowHeight(fila, 34)

        if not self._farmacias:
            self._tabla.setRowCount(1)
            mensaje = QTableWidgetItem(
                "No se encontraron valores en ORG_DESTINO ni ORG_ORIGEN."
            )
            mensaje.setFlags(Qt.ItemIsEnabled)
            self._tabla.setItem(0, 1, mensaje)

        layout.addWidget(self._tabla)
        return card

    def _crear_botones(self) -> QDialogButtonBox:
        botones = QDialogButtonBox()
        cancelar = botones.addButton("Cancelar", QDialogButtonBox.RejectRole)
        cancelar.setObjectName("botonSecundario")
        cancelar.setMinimumHeight(38)
        cancelar.clicked.connect(self.reject)

        guardar = botones.addButton("Guardar en el sistema", QDialogButtonBox.AcceptRole)
        guardar.setObjectName("botonPrincipal")
        guardar.setMinimumHeight(38)
        guardar.setDefault(True)
        guardar.clicked.connect(self._al_aceptar)
        return botones

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _actualizar_estado_combo(self) -> None:
        crear_nueva = self._combo_clinica.currentData() is None
        self._entrada_nombre.setEnabled(crear_nueva)
        if not crear_nueva:
            self._entrada_nombre.clear()

    def _toggle_todas(self, marcar: bool) -> None:
        for fila in range(self._tabla.rowCount()):
            cont = self._tabla.cellWidget(fila, 0)
            if cont is None:
                continue
            checkbox = cont.findChild(QCheckBox)
            if checkbox is not None:
                checkbox.setChecked(marcar)

    def _combo_tipo(self, tipo_actual: str) -> QComboBox:
        combo = ComboScrollSafe()
        for codigo, etiqueta in (
            ("INTERNA", "Interna"),
            ("EXTERNA", "Externa"),
            ("CEDI", "CEDI"),
            ("ALMACEN", "Almacen"),
            ("REEMPAQUE", "Reempaque/Reenvase"),
            ("DEVOLUCIONES", "Devoluciones"),
            ("NO_CLASIFICABLE", "No clasificable"),
        ):
            combo.addItem(etiqueta, codigo)
        indice = combo.findData(tipo_actual)
        combo.setCurrentIndex(indice if indice >= 0 else combo.findData("NO_CLASIFICABLE"))
        return combo

    def _combo_presta(self, puede_prestar: bool) -> QComboBox:
        combo = ComboScrollSafe()
        combo.addItem("Si", True)
        combo.addItem("No", False)
        combo.setCurrentIndex(0 if puede_prestar else 1)
        return combo

    def _farmacias_marcadas(self) -> list[FarmaciaRevision]:
        seleccionadas: list[FarmaciaRevision] = []
        for fila in range(self._tabla.rowCount()):
            cont = self._tabla.cellWidget(fila, 0)
            if cont is None:
                continue
            checkbox = cont.findChild(QCheckBox)
            item = self._tabla.item(fila, 1)
            if checkbox is not None and checkbox.isChecked() and item is not None:
                texto = item.text().strip()
                if texto:
                    base = self._farmacias[fila]
                    combo_tipo = self._tabla.cellWidget(fila, 3)
                    combo_presta = self._tabla.cellWidget(fila, 5)
                    tipo_codigo = (
                        combo_tipo.currentData()
                        if isinstance(combo_tipo, QComboBox)
                        else base.tipo_codigo
                    )
                    puede_prestar = (
                        bool(combo_presta.currentData())
                        if isinstance(combo_presta, QComboBox)
                        else base.puede_prestar
                    )
                    seleccionadas.append(
                        FarmaciaRevision(
                            codigo=texto,
                            origen=base.origen,
                            tipo_codigo=str(tipo_codigo or "NO_CLASIFICABLE"),
                            conocida=base.conocida,
                            puede_prestar=puede_prestar,
                            guardar=True,
                            farmacia_id=base.farmacia_id,
                        )
                    )
        return seleccionadas

    def _al_aceptar(self) -> None:
        clinica_id = self._combo_clinica.currentData()
        nombre_clinica = ""
        if clinica_id is None:
            nombre_clinica = self._entrada_nombre.text().strip()
            if not nombre_clinica:
                QMessageBox.warning(
                    self,
                    "Nombre requerido",
                    "Ingrese el nombre de la nueva clinica o seleccione una existente.",
                )
                return
        else:
            seleccionada = next(
                (c for c in self._clinicas_existentes if c.id == clinica_id), None
            )
            nombre_clinica = seleccionada.nombre if seleccionada else ""

        farmacias = self._farmacias_marcadas()
        if not farmacias:
            confirmar = QMessageBox.question(
                self,
                "Sin farmacias seleccionadas",
                "No marco ninguna farmacia. ¿Desea registrar solo la clinica sin asociar farmacias?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirmar != QMessageBox.Yes:
                return

        try:
            resultado = self._persistir(clinica_id, nombre_clinica, farmacias)
        except ErrorDominio as error:
            QMessageBox.critical(self, "Error", str(error))
            return
        except Exception as error:  # noqa: BLE001
            self._logger.exception("Fallo al guardar clinica/farmacias: %s", error)
            QMessageBox.critical(
                self,
                "Error",
                "No fue posible guardar los datos. Revise el log para mas detalles.",
            )
            return

        self._resultado = resultado
        self.accept()

    def _persistir(
        self,
        clinica_id: int | None,
        nombre_clinica: str,
        farmacias: list[str] | list[FarmaciaRevision],
    ) -> ResultadoGuardarClinica:
        """Crea/asocia clinica y farmacias en una sola transaccion."""
        creadas = 0
        asociadas = 0
        nombre_final = nombre_clinica

        with sesion_scope() as sesion:
            servicio_clinicas = ServicioClinicas(sesion)
            servicio_farmacias = ServicioFarmacias(sesion)

            if clinica_id is None:
                clinica_dto = servicio_clinicas.crear_clinica(
                    ClinicaCrearDTO(nombre=nombre_clinica)
                )
                clinica_id_final = clinica_dto.id
                nombre_final = clinica_dto.nombre
            else:
                clinica_id_final = clinica_id

            farmacias_clinica = {
                f.codigo: f
                for f in servicio_clinicas.listar_farmacias_de_clinica(clinica_id_final)
            }

            for farmacia in farmacias:
                revision = self._normalizar_revision(farmacia)
                existente_previo = servicio_farmacias.buscar_por_codigo_o_nombre(codigo=revision.codigo)
                farmacia_dto = servicio_farmacias.crear_desde_deteccion(
                    codigo_detectado=revision.codigo,
                    nombre_detectado=revision.codigo,
                    tipo_codigo=revision.tipo_codigo,
                    puede_prestar=revision.puede_prestar,
                    es_interna=revision.tipo_codigo == "INTERNA",
                    es_externa=revision.tipo_codigo == "EXTERNA",
                )
                if revision.codigo in farmacias_clinica:
                    continue
                servicio_farmacias.asociar_a_clinica(
                    farmacia_dto.id, clinica_id_final, relacion=revision.tipo_codigo
                )
                if not existente_previo:
                    creadas += 1
                asociadas += 1

        return ResultadoGuardarClinica(
            confirmado=True,
            clinica_id=clinica_id_final,
            clinica_nombre=nombre_final,
            farmacias_creadas=creadas,
            farmacias_asociadas=asociadas,
        )

    def resultado(self) -> ResultadoGuardarClinica:
        """Retorna el resultado de la interaccion (vacio si se cancelo)."""
        return self._resultado

    def _construir_revisiones_farmacias(self) -> list[FarmaciaRevision]:
        destino = set(self._farmacias_destino)
        origen = set(self._farmacias_origen)
        conocidas = self._farmacias_conocidas()
        revisiones: list[FarmaciaRevision] = []

        for codigo in sorted(destino | origen):
            conocida = conocidas.get(codigo)
            en_destino = codigo in destino
            en_origen = codigo in origen
            tipo = self._tipo_sugerido(codigo, en_destino=en_destino, conocida=conocida)
            revisiones.append(
                FarmaciaRevision(
                    codigo=codigo,
                    origen=self._origen_detectado(en_destino, en_origen),
                    tipo_codigo=tipo,
                    conocida=conocida is not None,
                    puede_prestar=conocida.puede_prestar if conocida is not None else tipo != "NO_CLASIFICABLE",
                    farmacia_id=conocida.id if conocida is not None else None,
                )
            )
        return revisiones

    def _farmacias_conocidas(self):
        try:
            with sesion_scope() as sesion:
                return {
                    farmacia.codigo: farmacia
                    for farmacia in ServicioFarmacias(sesion).listar_farmacias()
                }
        except Exception as error:  # noqa: BLE001
            self._logger.warning("No fue posible cargar farmacias conocidas: %s", error)
            return {}

    @staticmethod
    def _tipo_sugerido(codigo: str, *, en_destino: bool, conocida) -> str:
        if conocida is not None:
            if conocida.es_interna:
                return "INTERNA"
            if conocida.es_externa:
                return "EXTERNA"
        if en_destino:
            return "INTERNA"
        texto = codigo.upper()
        if "CEDI" in texto:
            return "CEDI"
        if "REEMPAQUE" in texto or "REENVASE" in texto:
            return "REEMPAQUE"
        if "DEVOL" in texto:
            return "DEVOLUCIONES"
        if "ALMACEN" in texto:
            return "ALMACEN"
        return "EXTERNA"

    @staticmethod
    def _origen_detectado(en_destino: bool, en_origen: bool) -> str:
        if en_destino and en_origen:
            return "Origen y destino"
        if en_destino:
            return "ORG_DESTINO"
        return "ORG_ORIGEN"

    @staticmethod
    def _normalizar_revision(farmacia: str | FarmaciaRevision) -> FarmaciaRevision:
        if isinstance(farmacia, FarmaciaRevision):
            return farmacia
        return FarmaciaRevision(
            codigo=farmacia,
            origen="ORG_DESTINO",
            tipo_codigo="INTERNA",
            conocida=False,
            puede_prestar=True,
        )
