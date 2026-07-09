"""Tests de la interfaz visual - Fase 6: sidebar y navegacion."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

# Garantiza que QApplication exista antes de instanciar widgets
from PySide6.QtWidgets import QApplication, QStackedWidget

_app: QApplication | None = None


def _get_app() -> QApplication:
    global _app
    existing = QApplication.instance()
    if existing is not None:
        _app = existing
    elif _app is None:
        _app = QApplication(sys.argv[:1])
    return _app


@pytest.fixture(scope="module", autouse=True)
def qapp_fixture():
    app = _get_app()
    yield app


# ---------------------------------------------------------------------------
# Configuracion minima para VentanaPrincipal
# ---------------------------------------------------------------------------

_CONFIG_MINIMA: dict = {
    "nombre_aplicacion": "FarmaFlow",
    "ancho_ventana": 1280,
    "alto_ventana": 800,
    "ruta_logs": "logs",
    "ruta_salidas": "salidas",
    "hoja_excel": "Movimientos",
    "columnas_requeridas": [],
    "alias_columnas": {},
    "max_filas_preview": 5,
    "usar_lector_legacy": False,
}


def _resultado_carga_exportable():
    import pandas as pd
    from modelos.resultado_carga import ResultadoCarga
    from modelos.resultado_preclasificacion import ResultadoPreclasificacion

    df = pd.DataFrame(
        {
            "ORG_ORIGEN": ["16_FARMA"],
            "ORG_DESTINO": ["47_FARMA"],
            "TIPOLOGIA_PRELIMINAR": ["TIPO_OK"],
            "REGLA_APLICADA": ["regla"],
        }
    )
    preclasificacion = ResultadoPreclasificacion(
        exito=True,
        mensaje="ok",
        cantidad_registros=1,
        cantidad_clasificados=1,
        cantidad_sin_clasificar=0,
        dataframe_resultado=df,
    )
    return ResultadoCarga(
        exito=True,
        mensaje="ok",
        nombre_archivo="archivo.xlsx",
        cantidad_filas=1,
        cantidad_columnas=len(df.columns),
        dataframe=df,
        dataframe_procesado=df.copy(),
        resultado_preclasificacion=preclasificacion,
        estructura_valida=True,
    )


# ---------------------------------------------------------------------------
# Tests de VentanaPrincipal
# ---------------------------------------------------------------------------


class TestVentanaPrincipal:
    """Tests de instanciacion y estructura de VentanaPrincipal."""

    @pytest.fixture(autouse=True)
    def _crear_ventana(self):
        from interfaz.ventana_principal import VentanaPrincipal

        self._ventana = VentanaPrincipal(configuracion=_CONFIG_MINIMA)

    def test_instancia_correctamente(self):
        from interfaz.ventana_principal import VentanaPrincipal

        assert isinstance(self._ventana, VentanaPrincipal)

    def test_tiene_sidebar(self):
        from interfaz.componentes.sidebar_navegacion import SidebarNavegacion

        assert hasattr(self._ventana, "_sidebar")
        assert isinstance(self._ventana._sidebar, SidebarNavegacion)

    def test_tiene_stack(self):
        assert hasattr(self._ventana, "_stack")
        assert isinstance(self._ventana._stack, QStackedWidget)

    def test_stack_tiene_nueve_pantallas(self):
        assert self._ventana._stack.count() == 9

    def test_stack_inicia_en_carga(self):
        assert self._ventana._stack.currentIndex() == 0

    def test_navegacion_cambia_pantalla(self):
        self._ventana._navegar_a_pantalla("clinica")
        assert self._ventana._stack.currentIndex() == 2

        self._ventana._navegar_a_pantalla("exportar")
        assert self._ventana._stack.currentIndex() == 5

        self._ventana._navegar_a_pantalla("carga")
        assert self._ventana._stack.currentIndex() == 0

    def test_indices_cubren_todas_las_pantallas(self):
        claves_esperadas = {
            "carga", "novedades", "clinica", "reglas", "resultado",
            "exportar", "clinicas", "catalogos", "historial",
        }
        assert set(self._ventana._indices.keys()) == claves_esperadas

    def test_titulo_ventana_contiene_nombre_app(self):
        assert "FarmaFlow" in self._ventana.windowTitle()

    def test_cambio_lista_marca_reproceso_sin_ejecutarlo(self, monkeypatch):
        self._ventana._resultado_carga_actual = _resultado_carga_exportable()
        llamadas = []
        monkeypatch.setattr(self._ventana, "_reprocesar_clasificacion_actual", lambda *a, **k: llamadas.append(True))

        self._ventana._al_cambio_configuracion("listas")

        assert self._ventana._clasificacion_requiere_reproceso is True
        assert llamadas == []
        assert not self._ventana._btn_aplicar_reproceso.isHidden()

    def test_boton_aplicar_cambios_reprocesa_y_limpia_estado(self, monkeypatch):
        self._ventana._resultado_carga_actual = _resultado_carga_exportable()
        self._ventana._clasificacion_requiere_reproceso = True

        def reproceso_fake(*_args, **_kwargs):
            self._ventana._clasificacion_requiere_reproceso = False
            self._ventana._actualizar_estado_operativo()
            return True

        monkeypatch.setattr(self._ventana, "_reprocesar_clasificacion_actual", reproceso_fake)

        self._ventana._aplicar_cambios_y_reprocesar()

        assert self._ventana._clasificacion_requiere_reproceso is False

    def test_exportar_con_cambios_pendientes_muestra_advertencia(self, monkeypatch):
        import interfaz.ventana_principal as modulo

        self._ventana._resultado_carga_actual = _resultado_carga_exportable()
        self._ventana._clasificacion_requiere_reproceso = True
        eventos = []

        class FakeMessageBox:
            Warning = 1
            AcceptRole = 0
            DestructiveRole = 1
            RejectRole = 2

            def __init__(self, *_args, **_kwargs):
                self._botones = []
                self._seleccionado = None

            def setIcon(self, *_args):
                pass

            def setWindowTitle(self, titulo):
                eventos.append(("titulo", titulo))

            def setText(self, texto):
                eventos.append(("texto", texto))

            def addButton(self, texto, _rol):
                boton = object()
                self._botones.append((texto, boton))
                if texto == "Cancelar":
                    self._seleccionado = boton
                return boton

            def exec(self):
                return None

            def clickedButton(self):
                return self._seleccionado

            @staticmethod
            def information(*_args, **_kwargs):
                eventos.append(("info", "resumen"))

        monkeypatch.setattr(modulo, "QMessageBox", FakeMessageBox)

        assert self._ventana._confirmar_exportacion_segura() is False
        assert any("cambios pendientes" in texto.lower() for tipo, texto in eventos if tipo == "texto")


# ---------------------------------------------------------------------------
# Tests de SidebarNavegacion
# ---------------------------------------------------------------------------


class TestSidebarNavegacion:
    """Tests del componente sidebar."""

    @pytest.fixture(autouse=True)
    def _crear_sidebar(self):
        from interfaz.componentes.sidebar_navegacion import SidebarNavegacion

        self._sidebar = SidebarNavegacion("FarmaFlow")

    def test_tiene_claves_principales(self):
        claves = self._sidebar.claves_pantallas()
        for clave in ("carga", "novedades", "clinica", "reglas", "resultado", "exportar"):
            assert clave in claves, f"Clave faltante: {clave}"

    def test_tiene_claves_configuracion(self):
        claves = self._sidebar.claves_pantallas()
        for clave in ("clinicas", "catalogos", "historial"):
            assert clave in claves, f"Clave faltante: {clave}"

    def test_total_nueve_items(self):
        assert len(self._sidebar.claves_pantallas()) == 9

    def test_activar_pantalla_no_lanza_error(self):
        self._sidebar.activar_pantalla("carga")
        self._sidebar.activar_pantalla("exportar")
        self._sidebar.activar_pantalla("carga")

    def test_activar_pantalla_desconocida_no_lanza_error(self):
        self._sidebar.activar_pantalla("pantalla_inexistente")


# ---------------------------------------------------------------------------
# Tests de VistaCargaArchivo
# ---------------------------------------------------------------------------


class TestVistaCargaArchivo:
    """Tests de la vista de carga con el nuevo diseno."""

    @pytest.fixture(autouse=True)
    def _crear_vista(self):
        from interfaz.vistas.vista_carga_archivo import VistaCargaArchivo

        self._vista = VistaCargaArchivo(configuracion=_CONFIG_MINIMA)

    def test_instancia_correctamente(self):
        from interfaz.vistas.vista_carga_archivo import VistaCargaArchivo

        assert isinstance(self._vista, VistaCargaArchivo)

    def test_tiene_senales_requeridas(self):
        assert hasattr(self._vista, "archivo_cargado")
        assert hasattr(self._vista, "exportacion_solicitada")
        assert hasattr(self._vista, "estado_actualizado")
        assert hasattr(self._vista, "vista_limpiada")

    def test_tiene_metodos_publicos(self):
        assert callable(getattr(self._vista, "seleccionar_archivo", None))
        assert callable(getattr(self._vista, "cargar_archivo", None))
        assert callable(getattr(self._vista, "limpiar", None))
        assert callable(getattr(
            self._vista, "establecer_exportacion_disponible", None
        ))
        assert callable(getattr(
            self._vista, "mostrar_resultado_exportacion", None
        ))
        assert callable(getattr(self._vista, "actualizar_estado_flujo", None))

    def test_limpiar_no_lanza_error(self):
        self._vista.limpiar()

    def test_establecer_exportacion_disponible(self):
        self._vista.establecer_exportacion_disponible(True)
        self._vista.establecer_exportacion_disponible(False)

    def test_mostrar_resultado_exportacion(self):
        self._vista.mostrar_resultado_exportacion("Exportacion completada.", exito=True)
        self._vista.mostrar_resultado_exportacion("Error al exportar.", exito=False)

    def test_actualizar_estado_flujo(self):
        self._vista.actualizar_estado_flujo("Archivo cargado correctamente.")
        self._vista.actualizar_estado_flujo("Error en la carga.")

    def test_cargar_sin_archivo_no_lanza_error(self):
        self._vista.cargar_archivo()


# ---------------------------------------------------------------------------
# Tests de vistas placeholder
# ---------------------------------------------------------------------------


class TestVistasPlaceholder:
    """Verifica que todas las vistas placeholder instancian sin error."""

    def test_vista_clinica_farmacias(self):
        from interfaz.vistas.vista_clinica_farmacias import VistaClinicaFarmacias

        v = VistaClinicaFarmacias()
        assert v is not None

    def test_vista_clinica_farmacias_botones_filtran_tabla(self):
        from interfaz.vistas.vista_clinica_farmacias import VistaClinicaFarmacias, _FilaFarmacia

        v = VistaClinicaFarmacias()
        v._filas = [
            _FilaFarmacia("16", "Interna", 10, "EXISTENTE", "INTERNA", 1, True, True, False, True),
            _FilaFarmacia("20", "Externa", 8, "EXISTENTE", "EXTERNA", 2, True, False, True, False),
            _FilaFarmacia("1058", "CEDI", 6, "EXISTENTE", "CEDI", 3, True, False, False, False),
            _FilaFarmacia("47", "No presta", 4, "EXISTENTE", "INTERNA", 4, False, True, False, True),
        ]

        v._aplicar_filtro()
        assert len(v._filas_filtradas) == 4

        v._botones_filtro_farmacias["INTERNAS"].setChecked(True)
        v._aplicar_filtro()
        assert [v._filas[i].codigo for i in v._filas_filtradas] == ["16", "47"]

        v._botones_filtro_farmacias["NO_PRESTAN"].setChecked(True)
        v._aplicar_filtro()
        assert [v._filas[i].codigo for i in v._filas_filtradas] == ["47"]

        v._botones_filtro_farmacias["INTERNAS"].setChecked(False)
        v._botones_filtro_farmacias["NO_PRESTAN"].setChecked(False)
        v._botones_filtro_farmacias["CEDI"].setChecked(True)
        v._aplicar_filtro()
        assert [v._filas[i].codigo for i in v._filas_filtradas] == ["1058"]

    def test_vista_reglas_clasificacion(self):
        from interfaz.vistas.vista_reglas_clasificacion import VistaReglasClasificacion

        v = VistaReglasClasificacion()
        assert v is not None

    def test_vista_resultado_preclasificacion(self):
        from interfaz.vistas.vista_resultado_preclasificacion import (
            VistaResultadoPreclasificacion,
        )

        v = VistaResultadoPreclasificacion()
        assert v is not None

    def test_vista_novedades_archivo(self):
        from interfaz.vistas.vista_novedades_archivo import VistaNovedadesArchivo

        v = VistaNovedadesArchivo()
        assert v is not None
        assert hasattr(v, "guardar_farmacias_solicitado")

    def test_vista_exportacion(self):
        from interfaz.vistas.vista_exportacion import VistaExportacion

        v = VistaExportacion()
        assert v is not None

    def test_vista_catalogos(self):
        from interfaz.vistas.vista_catalogos import VistaCatalogos

        v = VistaCatalogos()
        assert v is not None

    def test_vista_historial(self):
        from interfaz.vistas.vista_historial import VistaHistorial

        v = VistaHistorial()
        assert v is not None

    def test_vista_clinicas(self):
        from interfaz.vistas.vista_clinicas import VistaClinicas

        v = VistaClinicas()
        assert v is not None
        assert callable(getattr(v, "recargar", None))
        assert hasattr(v, "_tabla_internas")
        assert hasattr(v, "_tabla_externas")
        assert hasattr(v, "_tabla_pendientes")

    def test_vista_catalogos_tiene_tabla_items(self):
        from interfaz.vistas.vista_catalogos import VistaCatalogos

        v = VistaCatalogos()
        assert v is not None
        assert v._tabla.columnCount() == 5
        assert v._tabla.horizontalHeaderItem(0).text() == "CODIGO"
        assert v._tabla.horizontalHeaderItem(1).text() == "DESCRIPCION / NOMBRE"

    def test_vista_catalogos_boton_abrir_muestra_items_lista(self, monkeypatch):
        from PySide6.QtWidgets import QPushButton

        from interfaz.vistas.vista_catalogos import VistaCatalogos

        v = VistaCatalogos()
        v._listas = [
            SimpleNamespace(
                codigo="LIQUIDOS",
                nombre="Articulos liquidos",
                tipo_lista="ARTICULOS",
                descripcion="",
                activa=True,
            )
        ]
        llamadas = []
        monkeypatch.setattr(v, "_cargar_tabla_items_lista", lambda codigo: llamadas.append(codigo))

        v._catalogo_actual = "LISTAS"
        v._cargar_tabla_listas()

        contenedor = v._tabla.cellWidget(0, 4)
        boton = contenedor.findChild(QPushButton) if contenedor is not None else None
        assert boton is not None

        boton.click()

        assert v._catalogo_actual == "LIQUIDOS"
        assert llamadas == ["LIQUIDOS"]

    def test_vista_historial_tiene_columnas_operativas(self):
        from interfaz.vistas.vista_historial import VistaHistorial

        v = VistaHistorial()
        assert v is not None
        assert v._tabla.columnCount() == 10
        assert v._tabla.horizontalHeaderItem(7).text() == "RUTA EXPORTADA"


# ---------------------------------------------------------------------------
# Tests de componentes reutilizables
# ---------------------------------------------------------------------------


class TestComponentes:
    """Tests de los nuevos componentes visuales."""

    def test_badge_estado(self):
        from interfaz.componentes.badge_estado import BadgeEstado

        b = BadgeEstado("Activo", "correcto")
        assert b.text() == "Activo"

    def test_badge_establecer_estado(self):
        from interfaz.componentes.badge_estado import BadgeEstado

        b = BadgeEstado()
        b.establecer_estado("Error", "error")
        assert b.text() == "Error"

    def test_tarjeta_metrica(self):
        from interfaz.componentes.tarjeta_metrica import TarjetaMetrica

        t = TarjetaMetrica("Registros", "150.342")
        t.actualizar("200.000")
        t.actualizar("300", titulo="Nuevo titulo")

    def test_seccion_card(self):
        from interfaz.componentes.seccion_card import SeccionCard

        c = SeccionCard("Mi sección")
        assert c.layout_principal is not None

    def test_boton_icono(self):
        from interfaz.componentes.boton_icono import BotonIcono

        b = BotonIcono("Validar", "✔", "primario")
        assert "Validar" in b.text()

    def test_item_navegacion(self):
        from interfaz.componentes.item_navegacion import ItemNavegacion

        item = ItemNavegacion("carga", "1. Carga", numero=1)
        assert item.clave == "carga"
        item.establecer_activo(True)
        item.establecer_activo(False)
        item.establecer_completado()

    def test_sidebar_navegacion(self):
        from interfaz.componentes.sidebar_navegacion import SidebarNavegacion

        s = SidebarNavegacion()
        assert len(s.claves_pantallas()) == 9


# ---------------------------------------------------------------------------
# Tests del dialogo Guardar Clinica
# ---------------------------------------------------------------------------


class TestDialogoGuardarClinica:
    """Tests del dialogo post-importacion para asociar farmacias a una clinica."""

    def test_extraer_farmacias_org_destino_devuelve_unicos(self):
        import pandas as pd
        from interfaz.componentes.dialogo_guardar_clinica import (
            extraer_farmacias_org_destino,
        )

        df = pd.DataFrame({
            "ORG_DESTINO": [
                "16_FARMA_FARMACIA_INTERNA_CRS",
                "47_FARMA_ALMACEN_CIRUGIA_CRS",
                "16_FARMA_FARMACIA_INTERNA_CRS",
                None,
                "",
                "256_FARMA_URGENCIAS_CRS",
            ],
            "OTRA": [1, 2, 3, 4, 5, 6],
        })
        valores = extraer_farmacias_org_destino(df)
        assert valores == [
            "16_FARMA_FARMACIA_INTERNA_CRS",
            "256_FARMA_URGENCIAS_CRS",
            "47_FARMA_ALMACEN_CIRUGIA_CRS",
        ]

    def test_extraer_farmacias_sin_columna(self):
        import pandas as pd
        from interfaz.componentes.dialogo_guardar_clinica import (
            extraer_farmacias_org_destino,
        )

        df = pd.DataFrame({"OTRA": [1, 2]})
        assert extraer_farmacias_org_destino(df) == []

    def test_extraer_farmacias_dataframe_none(self):
        from interfaz.componentes.dialogo_guardar_clinica import (
            extraer_farmacias_org_destino,
        )

        assert extraer_farmacias_org_destino(None) == []

    def test_extraer_farmacias_org_origen_devuelve_unicos(self):
        import pandas as pd
        from interfaz.componentes.dialogo_guardar_clinica import extraer_farmacias_org_origen

        df = pd.DataFrame(
            {
                "ORG_ORIGEN": [
                    "999_FARMA_EXTERNA_NUEVA",
                    "999_FARMA_EXTERNA_NUEVA",
                    "",
                    "16_FARMA_FARMACIA_INTERNA_CRS",
                ]
            }
        )

        assert extraer_farmacias_org_origen(df) == [
            "16_FARMA_FARMACIA_INTERNA_CRS",
            "999_FARMA_EXTERNA_NUEVA",
        ]

    def test_dialogo_instancia(self):
        from interfaz.componentes.dialogo_guardar_clinica import (
            DialogoGuardarClinica,
        )

        dialogo = DialogoGuardarClinica(
            farmacias_detectadas=["16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA"],
        )
        assert dialogo is not None
        assert dialogo.resultado().confirmado is False
        assert callable(getattr(dialogo, "exec", None))

    def test_dialogo_sugiere_externa_si_solo_aparece_en_org_origen(self):
        from interfaz.componentes.dialogo_guardar_clinica import DialogoGuardarClinica

        dialogo = DialogoGuardarClinica(
            farmacias_detectadas=["16_FARMA_FARMACIA_INTERNA_CRS"],
            farmacias_origen=["999_FARMA_EXTERNA_NUEVA"],
        )

        por_codigo = {farmacia.codigo: farmacia for farmacia in dialogo._farmacias}
        assert por_codigo["16_FARMA_FARMACIA_INTERNA_CRS"].tipo_codigo == "INTERNA"
        assert por_codigo["999_FARMA_EXTERNA_NUEVA"].tipo_codigo == "EXTERNA"
        assert por_codigo["999_FARMA_EXTERNA_NUEVA"].origen == "ORG_ORIGEN"

    def test_persistir_guarda_farmacias_en_base(self, engine_temporal, monkeypatch):
        from contextlib import contextmanager

        from sqlalchemy.orm import sessionmaker

        import interfaz.componentes.dialogo_guardar_clinica as modulo_dialogo
        from interfaz.componentes.dialogo_guardar_clinica import DialogoGuardarClinica
        from servicios.servicio_farmacias import ServicioFarmacias

        Sesion = sessionmaker(bind=engine_temporal, autoflush=False, expire_on_commit=False, future=True)

        @contextmanager
        def sesion_scope_test():
            sesion = Sesion()
            try:
                yield sesion
                sesion.commit()
            except Exception:
                sesion.rollback()
                raise
            finally:
                sesion.close()

        monkeypatch.setattr(modulo_dialogo, "sesion_scope", sesion_scope_test)
        dialogo = DialogoGuardarClinica(farmacias_detectadas=["16_FARMA_FARMACIA_INTERNA_CRS"])

        resultado = dialogo._persistir(None, "Clinica Test", ["16_FARMA_FARMACIA_INTERNA_CRS"])

        with Sesion() as sesion:
            farmacias = ServicioFarmacias(sesion).listar_farmacias()

        assert resultado.confirmado is True
        assert resultado.farmacias_asociadas == 1
        assert [farmacia.codigo for farmacia in farmacias] == ["16_FARMA_FARMACIA_INTERNA_CRS"]
        assert farmacias[0].es_interna is True


class TestDialogoEditarLista:
    """Tests de captura legible para listas de articulos."""

    def test_parsear_items_acepta_codigo_y_descripcion(self):
        from interfaz.componentes.dialogo_editar_lista import DialogoEditarLista

        items = list(DialogoEditarLista._parsear_items("63192 | Agua esteril\n19891"))

        assert items == [("63192", "Agua esteril"), ("19891", "")]


# ---------------------------------------------------------------------------
# Tests del worker de exportacion (rendimiento - sin bloqueo de UI)
# ---------------------------------------------------------------------------


class TestWorkerExportacion:
    """Tests del worker que evita el congelamiento de la UI con archivos grandes."""

    def test_worker_instancia_y_emite_finalizado(self):
        import tempfile
        from pathlib import Path

        import pandas as pd
        from PySide6.QtCore import QEventLoop, QThreadPool, QTimer
        from interfaz.workers.worker_exportacion import WorkerExportacion
        from logica.exportador_excel import ExportadorExcel

        # Dataset minimo pero realista
        df_original = pd.DataFrame({
            "ARTICULO": ["A1", "A2"],
            "ORG_DESTINO": ["F1", "F2"],
            "TIPO_TRANSACCION": ["X", "Y"],
        })
        df_procesado = df_original.assign(
            FARMACIA_DETECTADA=["F1", "F2"],
            TIPOLOGIA_PRELIMINAR=["T1", "SIN_CLASIFICAR"],
            REGLA_APLICADA=["r1", ""],
        )

        with tempfile.TemporaryDirectory() as carpeta:
            worker = WorkerExportacion(
                exportador=ExportadorExcel(),
                dataframe_original=df_original,
                dataframe_procesado=df_procesado,
                ruta_salida=Path(carpeta),
                nombre_base_archivo="test_worker",
            )

            resultados = []
            progresos = []
            errores = []

            loop = QEventLoop()
            worker.senales.finalizado.connect(lambda r: (resultados.append(r), loop.quit()))
            worker.senales.error.connect(lambda m: (errores.append(m), loop.quit()))
            worker.senales.progreso.connect(lambda p, m: progresos.append((p, m)))

            QThreadPool.globalInstance().start(worker)
            QTimer.singleShot(15000, loop.quit)  # safety timeout
            loop.exec()

            assert errores == [], f"Errores inesperados: {errores}"
            assert len(resultados) == 1
            assert resultados[0].exito is True
            assert len(progresos) >= 1
            # Debe haber al menos un evento al 100%
            assert any(p == 100 for p, _ in progresos)

    def test_worker_reclasifica_con_reglas_vigentes_antes_de_exportar(self, monkeypatch):
        import pandas as pd

        from interfaz.workers import worker_exportacion
        from interfaz.workers.worker_exportacion import WorkerExportacion
        from logica.exportador_excel import ExportadorExcel
        from reglas.evaluador_condiciones import ContextoMotor
        from reglas.motor_reglas_avanzado import CondicionMotor, ReglaMotor

        df_procesado = pd.DataFrame(
            {
                "TIPO_TRANSACCION": ["SALE_ORDER_ISSUE"],
                "TIPO_ORIGEN": ["SALES_ORDER"],
                "ORG_DESTINO": ["16_FARMACIA_INTERNA"],
                "ORIGEN": ["CONSUMO"],
                "TIPOLOGIA_PRELIMINAR": ["DISPENSACION_AL_PACIENTE"],
                "REGLA_APLICADA": ["regla_vieja"],
            }
        )
        regla_base = ReglaMotor(
            id=98,
            nombre="dispensacion_al_paciente",
            prioridad=1,
            tipologia_resultado="DISPENSACION_AL_PACIENTE",
            condiciones=[
                CondicionMotor("TIPO_TRANSACCION", "IGUAL", ["SALE_ORDER_ISSUE"]),
                CondicionMotor("TIPO_ORIGEN", "IGUAL", ["SALES_ORDER"]),
            ],
        )
        regla_actualizada = ReglaMotor(
            id=99,
            nombre="dispensacion_consumo",
            prioridad=1,
            tipologia_resultado="DISPENSACION_CONSUMO",
            condiciones=[
                CondicionMotor("TIPOLOGIA", "IGUAL", ["DISPENSACION_AL_PACIENTE"]),
                CondicionMotor("ORG_DESTINO", "IGUAL", ["16_FARMACIA_INTERNA"]),
                CondicionMotor("ORIGEN", "IGUAL", ["CONSUMO"]),
            ],
        )
        monkeypatch.setattr(
            worker_exportacion,
            "obtener_reglas_motor_avanzado",
            lambda: [regla_base, regla_actualizada],
        )
        monkeypatch.setattr(worker_exportacion, "obtener_contexto_motor", lambda: ContextoMotor())

        worker = WorkerExportacion(
            exportador=ExportadorExcel(),
            dataframe_original=df_procesado,
            dataframe_procesado=df_procesado,
            ruta_salida=".",
            nombre_base_archivo="test",
        )

        reclasificado = worker._reclasificar_con_reglas_vigentes(df_procesado)

        assert reclasificado.loc[0, "TIPOLOGIA_PRELIMINAR"] == "DISPENSACION_AL_PACIENTE"
        assert reclasificado.loc[0, "TIPOLOGIA_FINAL"] == "DISPENSACION_CONSUMO"
        assert reclasificado.loc[0, "REGLA_DERIVADA_APLICADA"] == "dispensacion_consumo"
