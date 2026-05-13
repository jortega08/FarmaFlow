"""Pruebas de Fase 3: catalogos configurables y deteccion de farmacias."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from dto.farmacia_dto import FarmaciaCrearDTO
from dto.lista_dto import ItemListaCrearDTO, ListaConfigurableCrearDTO
from servicios.servicio_deteccion_farmacias import ServicioDeteccionFarmacias
from servicios.servicio_farmacias import ServicioFarmacias
from servicios.servicio_importacion_catalogos import ServicioImportacionCatalogos
from servicios.servicio_listas import ServicioListas
from servicios.servicio_tipos_farmacia import ServicioTiposFarmacia


def escribir_excel(dataframe: pd.DataFrame) -> Path:
    carpeta = Path(tempfile.mkdtemp())
    ruta = carpeta / "catalogo.xlsx"
    dataframe.to_excel(ruta, index=False)
    return ruta


def crear_farmacia(
    sesion: Session,
    *,
    codigo: str,
    nombre: str,
    tipo_codigo: str = "INTERNA",
):
    tipo = ServicioTiposFarmacia(sesion).obtener_por_codigo(tipo_codigo)
    return ServicioFarmacias(sesion).crear_farmacia(
        FarmaciaCrearDTO(codigo=codigo, nombre_original=nombre, tipo_farmacia_id=tipo.id)
    )


def test_extrae_codigo_inicial_desde_texto_concatenado() -> None:
    codigo = ServicioDeteccionFarmacias.extraer_codigo_desde_texto("16_Farma Farmacia Interna CRS")

    assert codigo == "16"


def test_detecta_farmacia_existente_por_codigo(sesion_temporal: Session) -> None:
    farmacia = crear_farmacia(sesion_temporal, codigo="16", nombre="Farmacia Norte")
    dataframe = pd.DataFrame([{"ORG_ORIGEN": "16_Farmacia Norte", "ORG_DESTINO": None}])

    resultado = ServicioDeteccionFarmacias(sesion_temporal).detectar_farmacias(dataframe)

    detectada = resultado.farmacias_detectadas[0]
    assert detectada.estado_deteccion == "EXISTENTE"
    assert detectada.farmacia_id == farmacia.id
    assert detectada.nombre_normalizado == "FARMACIA NORTE"


def test_detecta_farmacia_nueva(sesion_temporal: Session) -> None:
    dataframe = pd.DataFrame([{"ORG_ORIGEN": "99_Farmacia Nueva", "ORG_DESTINO": None}])

    resultado = ServicioDeteccionFarmacias(sesion_temporal).detectar_farmacias(dataframe)

    detectada = resultado.farmacias_detectadas[0]
    assert detectada.estado_deteccion == "NUEVA"
    assert detectada.codigo_detectado == "99"
    assert detectada.tipo_sugerido == "EXTERNA"
    assert detectada.es_interna is False
    assert detectada.es_externa is True
    assert detectada.puede_prestar is True


def test_detecta_farmacia_de_org_destino_como_interna(sesion_temporal: Session) -> None:
    dataframe = pd.DataFrame([{"ORG_ORIGEN": None, "ORG_DESTINO": "16_Farmacia Interna CRS"}])

    resultado = ServicioDeteccionFarmacias(sesion_temporal).detectar_farmacias(dataframe)

    detectada = resultado.farmacias_detectadas[0]
    assert detectada.tipo_sugerido == "INTERNA"
    assert detectada.es_interna is True
    assert detectada.es_externa is False
    assert detectada.puede_prestar is True


def test_detecta_cedi_de_org_origen_sin_marcarlo_como_interno(sesion_temporal: Session) -> None:
    dataframe = pd.DataFrame([{"ORG_ORIGEN": "1058_CEDI Central", "ORG_DESTINO": None}])

    resultado = ServicioDeteccionFarmacias(sesion_temporal).detectar_farmacias(dataframe)

    detectada = resultado.farmacias_detectadas[0]
    assert detectada.tipo_sugerido == "CEDI"
    assert detectada.es_interna is False
    assert detectada.es_externa is False
    assert detectada.puede_prestar is True


def test_detecta_farmacia_ambigua_por_nombre_compartido(sesion_temporal: Session) -> None:
    crear_farmacia(sesion_temporal, codigo="16", nombre="Farmacia Norte")
    crear_farmacia(sesion_temporal, codigo="17", nombre="Farmacia Norte")
    dataframe = pd.DataFrame([{"ORG_ORIGEN": "99_Farmacia Norte", "ORG_DESTINO": None}])

    resultado = ServicioDeteccionFarmacias(sesion_temporal).detectar_farmacias(dataframe)

    detectada = resultado.farmacias_detectadas[0]
    assert detectada.estado_deteccion == "AMBIGUA"
    assert detectada.farmacia_id is None


@pytest.mark.parametrize(
    ("nombre", "tipo_esperado"),
    [
        ("CEDI Medellin", "CEDI"),
        ("Centro de devoluciones", "DEVOLUCIONES"),
        ("Central de reempaque reenvase", "REEMPAQUE"),
        ("Almacen principal", "ALMACEN"),
        ("Farmacia externa", "EXTERNA"),
    ],
)
def test_sugerencia_inicial_de_tipo(nombre: str, tipo_esperado: str) -> None:
    assert ServicioDeteccionFarmacias.sugerir_tipo_farmacia(nombre) == tipo_esperado


def test_sugerencia_inicial_de_tipo_prioriza_org_destino_como_interna() -> None:
    tipo = ServicioDeteccionFarmacias.sugerir_tipo_farmacia(
        "Farmacia seleccionada",
        desde_org_destino=True,
    )

    assert tipo == "INTERNA"


def test_importa_articulos_desde_excel(sesion_temporal: Session) -> None:
    lista = ServicioListas(sesion_temporal).crear_lista(
        ListaConfigurableCrearDTO(codigo="ART_COI", nombre="Liquidos COI", tipo_lista="ARTICULOS")
    )
    ruta = escribir_excel(pd.DataFrame([{"CODIGO": "A1", "DESCRIPCION": "Agua"}, {"CODIGO": "A2", "DESCRIPCION": "Suero"}]))

    resultado = ServicioImportacionCatalogos(sesion_temporal).importar_articulos_desde_excel(
        lista.id,
        ruta,
        columna_codigo="CODIGO",
        columna_descripcion="DESCRIPCION",
    )

    items = ServicioListas(sesion_temporal).listar_items(lista.id)
    assert resultado.creados == 2
    assert resultado.duplicados == 0
    assert [item.valor for item in items] == ["A1", "A2"]
    assert [item.descripcion for item in items] == ["Agua", "Suero"]


def test_importa_farmacias_desde_excel(sesion_temporal: Session) -> None:
    lista = ServicioListas(sesion_temporal).crear_lista(
        ListaConfigurableCrearDTO(codigo="FARM_NO_PRESTAN", nombre="Farmacias que no prestan", tipo_lista="FARMACIAS")
    )
    ruta = escribir_excel(pd.DataFrame([{"CODIGO": "16", "NOMBRE": "Farmacia Norte"}]))

    resultado = ServicioImportacionCatalogos(sesion_temporal).importar_farmacias_desde_excel(
        lista.id,
        ruta,
        columna_codigo="CODIGO",
        columna_nombre="NOMBRE",
    )

    item = ServicioListas(sesion_temporal).listar_items(lista.id)[0]
    assert resultado.creados == 1
    assert item.codigo == "16"
    assert item.valor == "Farmacia Norte"


def test_previene_duplicados_en_importacion_de_listas(sesion_temporal: Session) -> None:
    servicio_listas = ServicioListas(sesion_temporal)
    lista = servicio_listas.crear_lista(
        ListaConfigurableCrearDTO(codigo="ART_MSTS", nombre="MSTS", tipo_lista="ARTICULOS")
    )
    servicio_listas.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor="A1", codigo="A1"))
    ruta = escribir_excel(
        pd.DataFrame(
            [
                {"CODIGO": "A1", "DESCRIPCION": "Existente"},
                {"CODIGO": "A2", "DESCRIPCION": "Nuevo"},
                {"CODIGO": "A2", "DESCRIPCION": "Duplicado en archivo"},
            ]
        )
    )

    resultado = ServicioImportacionCatalogos(sesion_temporal).importar_articulos_desde_excel(
        lista.id,
        ruta,
        columna_codigo="CODIGO",
        columna_descripcion="DESCRIPCION",
    )

    assert resultado.creados == 1
    assert resultado.duplicados == 2
    assert [item.valor for item in servicio_listas.listar_items(lista.id)] == ["A1", "A2"]


def test_previsualiza_importacion_desde_excel(sesion_temporal: Session) -> None:
    ruta = escribir_excel(pd.DataFrame([{"CODIGO": "A1", "NOMBRE": "Uno"}, {"CODIGO": "A2", "NOMBRE": "Dos"}]))

    previsualizacion = ServicioImportacionCatalogos(sesion_temporal).previsualizar_importacion(ruta, limite=1)

    assert previsualizacion.columnas == ["CODIGO", "NOMBRE"]
    assert previsualizacion.total_filas == 2
    assert previsualizacion.filas == [{"CODIGO": "A1", "NOMBRE": "Uno"}]
