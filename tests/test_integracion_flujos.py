"""Pruebas de integracion entre servicios y motor de clasificacion."""

from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from dto.clinica_dto import ClinicaCrearDTO
from dto.ejecucion_dto import EjecucionCrearDTO, EjecucionFinalizarDTO
from dto.farmacia_dto import FarmaciaCrearDTO
from dto.lista_dto import ItemListaCrearDTO, ListaConfigurableCrearDTO
from dto.regla_dto import CondicionReglaCrearDTO, ReglaClasificacionCrearDTO
from logica.clasificador_tipologia import ClasificadorTipologia
from servicios.servicio_clinicas import ServicioClinicas
from servicios.servicio_ejecuciones import ServicioEjecuciones
from servicios.servicio_farmacias import ServicioFarmacias
from servicios.servicio_listas import ServicioListas
from servicios.servicio_reglas import ServicioReglas
from servicios.servicio_tipos_farmacia import ServicioTiposFarmacia


def test_flujo_persistido_para_clasificacion_y_ejecucion(sesion_temporal: Session) -> None:
    clinica = ServicioClinicas(sesion_temporal).crear_clinica(
        ClinicaCrearDTO(codigo="CRS", nombre="Clinica del Rosario")
    )
    tipo = ServicioTiposFarmacia(sesion_temporal).obtener_por_codigo("INTERNA")
    farmacia = ServicioFarmacias(sesion_temporal).crear_farmacia(
        FarmaciaCrearDTO(
            codigo="16",
            nombre_original="16_Farma Farmacia Interna CRS",
            tipo_farmacia_id=tipo.id,
            es_interna=True,
        )
    )

    servicio_listas = ServicioListas(sesion_temporal)
    lista = servicio_listas.crear_lista(
        ListaConfigurableCrearDTO(codigo="FARMACIAS_INTERNAS", nombre="Farmacias internas", tipo_lista="FARMACIAS")
    )
    servicio_listas.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor=farmacia.nombre_original))

    servicio_reglas = ServicioReglas(sesion_temporal)
    servicio_reglas.crear_regla(
        ReglaClasificacionCrearDTO(
            nombre="dispensacion_persistida",
            tipologia_resultado="DISPENSACION_AL_PACIENTE",
            prioridad=5,
            condiciones=[
                CondicionReglaCrearDTO(campo="ORG_DESTINO", operador="EN_LISTA", lista_id=lista.id),
                CondicionReglaCrearDTO(
                    campo="TIPO_TRANSACCION",
                    operador="IGUAL",
                    valor_texto="SALES_ORDER_ISSUE",
                ),
                CondicionReglaCrearDTO(campo="TIPO_ORIGEN", operador="IGUAL", valor_texto="SALES_ORDER"),
            ],
        )
    )

    clasificador = ClasificadorTipologia(proveedor_reglas=servicio_reglas.obtener_reglas_para_motor)
    resultado = clasificador.clasificar(
        pd.DataFrame(
            [
                {
                    "ORG_DESTINO": "16_FARMA FARMACIA INTERNA CRS",
                    "TIPO_TRANSACCION": "SALES_ORDER_ISSUE",
                    "TIPO_ORIGEN": "SALES_ORDER",
                    "FARMACIA_DETECTADA": "16_FARMA FARMACIA INTERNA CRS",
                }
            ]
        )
    )

    ejecucion = ServicioEjecuciones(sesion_temporal).registrar_ejecucion_completa(
        EjecucionCrearDTO(
            clinica_id=clinica.id,
            archivo_nombre="movimientos.xlsx",
            hoja="Movimientos",
        ),
        EjecucionFinalizarDTO(
            estado="CLASIFICADA",
            total_registros=resultado.cantidad_registros,
            total_columnas=4,
            total_clasificados=resultado.cantidad_clasificados,
            total_sin_clasificar=resultado.cantidad_sin_clasificar,
            mensaje=resultado.mensaje,
        ),
    )

    assert resultado.dataframe_resultado.loc[0, "TIPOLOGIA_PRELIMINAR"] == "DISPENSACION_AL_PACIENTE"
    assert resultado.cantidad_clasificados == 1
    assert ejecucion.clinica_id == clinica.id
    assert ejecucion.estado == "CLASIFICADA"
