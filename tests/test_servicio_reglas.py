"""Pruebas del servicio de reglas."""

from __future__ import annotations

from sqlalchemy.orm import Session

from dto.lista_dto import ItemListaCrearDTO, ListaConfigurableCrearDTO
from dto.regla_dto import CondicionReglaCrearDTO, ReglaClasificacionCrearDTO, ReglaClasificacionDTO
from servicios.servicio_listas import ServicioListas
from servicios.servicio_reglas import ServicioReglas


def test_crear_regla_asociada_a_lista_y_convertir_para_motor(sesion_temporal: Session) -> None:
    servicio_listas = ServicioListas(sesion_temporal)
    lista = servicio_listas.crear_lista(
        ListaConfigurableCrearDTO(codigo="ORG_DESTINO", nombre="Organizaciones destino", tipo_lista="ORGANIZACIONES")
    )
    servicio_listas.agregar_item(ItemListaCrearDTO(lista_id=lista.id, valor="16_Farma Farmacia Interna CRS"))

    servicio_reglas = ServicioReglas(sesion_temporal)
    regla = servicio_reglas.crear_regla(
        ReglaClasificacionCrearDTO(
            nombre="dispensacion_interna",
            tipologia_resultado="DISPENSACION_AL_PACIENTE",
            prioridad=10,
            condiciones=[
                CondicionReglaCrearDTO(campo="ORG_DESTINO", operador="EN_LISTA", lista_id=lista.id),
                CondicionReglaCrearDTO(
                    campo="TIPO_TRANSACCION",
                    operador="IGUAL",
                    valor_texto="SALES_ORDER_ISSUE",
                ),
            ],
        )
    )
    reglas_motor = servicio_reglas.obtener_reglas_para_motor()

    assert isinstance(regla, ReglaClasificacionDTO)
    assert not hasattr(regla, "_sa_instance_state")
    assert reglas_motor == [
        {
            "nombre_regla": "dispensacion_interna",
            "prioridad": 10,
            "condiciones": {
                "ORG_DESTINO": ["16_FARMA_FARMACIA_INTERNA_CRS"],
                "TIPO_TRANSACCION": ["SALES_ORDER_ISSUE"],
            },
            "resultado": "DISPENSACION_AL_PACIENTE",
        }
    ]


def test_duplicar_y_eliminar_regla_copia_condiciones(sesion_temporal: Session) -> None:
    servicio = ServicioReglas(sesion_temporal)
    regla = servicio.crear_regla(
        ReglaClasificacionCrearDTO(
            nombre="original",
            tipologia_resultado="TIPO_A",
            prioridad=10,
            condiciones=[
                CondicionReglaCrearDTO(campo="TIPO_TRANSACCION", operador="IGUAL", valor_texto="A"),
                CondicionReglaCrearDTO(campo="MOTIVO", operador="CONTIENE", valor_texto="B"),
            ],
        )
    )

    copia = servicio.duplicar_regla(regla.id, "original_copia")
    servicio.eliminar_regla(regla.id)

    assert copia.nombre == "original_copia"
    assert copia.origen == "CREADA_UI"
    assert len(copia.condiciones) == 2
    assert [r.nombre for r in servicio.listar_reglas()] == ["original_copia"]


def test_importar_reglas_json_solo_si_no_existen_reglas_activas(sesion_temporal: Session) -> None:
    servicio = ServicioReglas(sesion_temporal)
    reglas = [
        {
            "nombre_regla": "conteo",
            "prioridad": 1,
            "condiciones": {"TIPO_TRANSACCION": ["CYCLE_COUNT_ADJUST"]},
            "resultado": "CONTEO_CICLICO",
        }
    ]

    creadas = servicio.importar_reglas_json(reglas)

    assert len(creadas) == 1
    assert servicio.importar_reglas_json(reglas) == []
    assert servicio.obtener_reglas_para_motor()[0]["condiciones"]["TIPO_TRANSACCION"] == ["CYCLE_COUNT_ADJUST"]


def test_sincronizar_reglas_json_actualiza_catalogo_y_respeta_creadas_ui(sesion_temporal: Session) -> None:
    servicio = ServicioReglas(sesion_temporal)
    servicio.crear_regla(
        ReglaClasificacionCrearDTO(
            nombre="aislamiento_pyxis",
            tipologia_resultado="AISLAMIENTO_PYXIS",
            prioridad=999,
            origen="JSON_MIGRADO",
            condiciones=[CondicionReglaCrearDTO(campo="TIPO_TRANSACCION", operador="IGUAL", valor_texto="A")],
        )
    )
    manual = servicio.crear_regla(
        ReglaClasificacionCrearDTO(
            nombre="manual_usuario",
            tipologia_resultado="NO_CAMBIAR",
            prioridad=10,
            origen="CREADA_UI",
            condiciones=[CondicionReglaCrearDTO(campo="TIPO_TRANSACCION", operador="IGUAL", valor_texto="B")],
        )
    )

    cambios = servicio.sincronizar_reglas_json(
        [
            {
                "nombre_regla": "manual_usuario",
                "prioridad": 1,
                "condiciones": {"TIPO_TRANSACCION": ["C"]},
                "resultado": "CAMBIADA",
            },
            {
                "nombre_regla": "alistamiento_pyxis",
                "prioridad": 999,
                "condiciones": {"TIPOLOGIA": ["ENTRADAS_PRESTAMOS_INTERNOS"]},
                "resultado": "ALISTAMIENTO_PYXIS",
            },
        ]
    )

    reglas = {regla.nombre: regla for regla in servicio.listar_reglas()}
    assert cambios == 2
    assert reglas["aislamiento_pyxis"].activa is False
    assert reglas["alistamiento_pyxis"].tipologia_resultado == "ALISTAMIENTO_PYXIS"
    assert servicio.obtener_regla(manual.id).tipologia_resultado == "NO_CAMBIAR"


def test_importar_reglas_json_respeta_operador_de_condicion(sesion_temporal: Session) -> None:
    servicio = ServicioReglas(sesion_temporal)

    servicio.importar_reglas_json(
        [
            {
                "nombre_regla": "dispensacion_por_consumo",
                "prioridad": 998,
                "condiciones": {
                    "ORIGEN": {
                        "operador": "CONTIENE",
                        "valores": ["CONSUMO", "MASIVO_CONSUMO.ORDER"],
                    },
                },
                "resultado": "DISPENSACION_POR_CONSUMO",
            }
        ]
    )

    regla = servicio.obtener_reglas_avanzadas()[0]

    assert regla.condiciones[0].campo == "ORIGEN"
    assert regla.condiciones[0].operador == "CONTIENE"
    assert regla.condiciones[0].valores == ["CONSUMO", "MASIVO_CONSUMO.ORDER"]


def test_importar_reglas_json_respeta_operador_vacio(sesion_temporal: Session) -> None:
    servicio = ServicioReglas(sesion_temporal)

    servicio.importar_reglas_json(
        [
            {
                "nombre_regla": "otros_ajustes",
                "prioridad": 900,
                "condiciones": {
                    "ORG_ORIGEN": {
                        "operador": "VACIO",
                    },
                },
                "resultado": "OTROS_AJUSTES",
            }
        ]
    )

    regla = servicio.obtener_reglas_avanzadas()[0]
    regla_legacy = servicio.obtener_reglas_para_motor()[0]

    assert regla.condiciones[0].campo == "ORG_ORIGEN"
    assert regla.condiciones[0].operador == "VACIO"
    assert regla.condiciones[0].valores == []
    assert regla_legacy["condiciones"]["ORG_ORIGEN"] == {"operador": "VACIO", "valores": []}


def test_buscar_reglas_con_paginacion(sesion_temporal: Session) -> None:
    servicio = ServicioReglas(sesion_temporal)
    servicio.crear_regla(
        ReglaClasificacionCrearDTO(
            nombre="dispensacion",
            tipologia_resultado="DISPENSACION",
            prioridad=10,
            condiciones=[CondicionReglaCrearDTO(campo="TIPO_TRANSACCION", operador="IGUAL", valor_texto="A")],
        )
    )
    servicio.crear_regla(
        ReglaClasificacionCrearDTO(
            nombre="devoluciones",
            tipologia_resultado="DEVOLUCIONES",
            prioridad=20,
            condiciones=[CondicionReglaCrearDTO(campo="TIPO_TRANSACCION", operador="IGUAL", valor_texto="B")],
        )
    )

    pagina_1 = servicio.buscar("d", pagina=1, filas_por_pagina=1)
    pagina_2 = servicio.buscar("d", pagina=2, filas_por_pagina=1)

    assert [regla.nombre for regla in pagina_1] == ["dispensacion"]
    assert [regla.nombre for regla in pagina_2] == ["devoluciones"]
