"""Casos de uso para reglas de clasificacion."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from dto.regla_dto import (
    CondicionReglaCrearDTO,
    ReglaClasificacionActualizarDTO,
    ReglaClasificacionCrearDTO,
    ReglaClasificacionDTO,
)
from persistencia.conexion import sesion_scope
from persistencia.modelos_orm import CondicionRegla
from repositorios.repositorio_lista_items import RepositorioListaItems
from repositorios.repositorio_listas import RepositorioListas
from repositorios.repositorio_reglas import RepositorioReglas
from servicios.excepciones import DatoDuplicadoError, EntidadNoEncontradaError, ValidacionDominioError
from servicios.paginacion import contiene_texto, paginar
from utilidades.rutas import cargar_json, resolver_ruta_proyecto
from utilidades.texto import normalizar_codigo, normalizar_nombre_columna, normalizar_texto, normalizar_valor_por_campo


ORIGENES_REGLAS_SINCRONIZABLES = frozenset({"JSON_MIGRADO", "SISTEMA"})
REGLAS_LEGACY_A_DESACTIVAR = ("aislamiento_pyxis",)


class ServicioReglas:
    """Administra reglas persistidas y las transforma para el motor."""

    def __init__(self, sesion: Session) -> None:
        self._repo = RepositorioReglas(sesion)
        self._repo_listas = RepositorioListas(sesion)
        self._repo_items = RepositorioListaItems(sesion)

    def crear_regla(self, datos: ReglaClasificacionCrearDTO) -> ReglaClasificacionDTO:
        self._validar_regla(datos)
        if self._repo.listar(nombre=datos.nombre):
            raise DatoDuplicadoError(f"Ya existe una regla con nombre {datos.nombre}.")

        condiciones = [condicion.model_dump(exclude_none=True) for condicion in datos.condiciones]
        campos = datos.model_dump(exclude={"condiciones"})
        regla = self._repo.crear_con_condiciones(condiciones=condiciones, **campos)
        return ReglaClasificacionDTO.model_validate(regla)

    def listar_reglas(self, activa: bool | None = None) -> list[ReglaClasificacionDTO]:
        if activa is True:
            reglas = self._repo.listar_activas_ordenadas_por_prioridad()
        else:
            filtros = {} if activa is None else {"activa": activa}
            reglas = self._repo.listar(**filtros)
        return [ReglaClasificacionDTO.model_validate(regla) for regla in reglas]

    def listar_reglas_activas(self) -> list[ReglaClasificacionDTO]:
        return self.listar_reglas(activa=True)

    def buscar(self, texto: str, pagina: int = 1, filas_por_pagina: int = 20) -> list[ReglaClasificacionDTO]:
        """Busca reglas por nombre, descripcion o tipologia y retorna una pagina 1-indexed."""
        reglas = sorted(
            self._repo.listar(),
            key=lambda regla: (regla.prioridad, regla.nombre, regla.id),
        )
        filtradas = [
            ReglaClasificacionDTO.model_validate(regla)
            for regla in reglas
            if contiene_texto(
                texto,
                (regla.nombre, regla.descripcion, regla.tipologia_resultado, regla.origen),
            )
        ]
        return paginar(filtradas, pagina, filas_por_pagina)

    def obtener_regla(self, regla_id: int) -> ReglaClasificacionDTO:
        regla = self._repo.obtener(regla_id)
        if regla is None:
            raise EntidadNoEncontradaError(f"No existe la regla con id {regla_id}.")
        return ReglaClasificacionDTO.model_validate(regla)

    def actualizar_regla(self, regla_id: int, datos: ReglaClasificacionActualizarDTO) -> ReglaClasificacionDTO:
        regla_actual = self._repo.obtener(regla_id)
        if regla_actual is None:
            raise EntidadNoEncontradaError(f"No existe la regla con id {regla_id}.")

        campos = datos.model_dump(exclude_none=True)
        if not campos:
            return ReglaClasificacionDTO.model_validate(regla_actual)

        if "nombre" in campos and not str(campos["nombre"]).strip():
            raise ValidacionDominioError("El nombre de la regla es obligatorio.")
        if "tipologia_resultado" in campos and not str(campos["tipologia_resultado"]).strip():
            raise ValidacionDominioError("La tipologia resultado es obligatoria.")
        if "prioridad" in campos and int(campos["prioridad"]) < 0:
            raise ValidacionDominioError("La prioridad debe ser mayor o igual a cero.")

        if "nombre" in campos:
            existentes = self._repo.listar(nombre=str(campos["nombre"]))
            if any(regla.id != regla_id for regla in existentes):
                raise DatoDuplicadoError(f"Ya existe una regla con nombre {campos['nombre']}.")

        regla = self._repo.actualizar(regla_id, **campos)
        assert regla is not None
        return ReglaClasificacionDTO.model_validate(regla)

    def guardar_regla_con_condiciones(
        self,
        regla_id: int | None,
        datos: ReglaClasificacionCrearDTO,
    ) -> ReglaClasificacionDTO:
        """Crea o actualiza una regla reemplazando sus condiciones editables."""
        if regla_id is None:
            return self.crear_regla(datos)

        self._validar_regla(datos)
        regla_actual = self._repo.obtener(regla_id)
        if regla_actual is None:
            raise EntidadNoEncontradaError(f"No existe la regla con id {regla_id}.")

        existentes = self._repo.listar(nombre=datos.nombre)
        if any(regla.id != regla_id for regla in existentes):
            raise DatoDuplicadoError(f"Ya existe una regla con nombre {datos.nombre}.")

        self._repo.actualizar(
            regla_id,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            tipologia_resultado=datos.tipologia_resultado,
            prioridad=datos.prioridad,
            activa=datos.activa,
            origen=datos.origen,
            version=datos.version,
        )

        regla = self._repo.obtener(regla_id)
        assert regla is not None
        regla.condiciones.clear()
        self._repo.sesion.flush()
        for indice, condicion in enumerate(datos.condiciones):
            campos = condicion.model_dump(exclude_none=True)
            campos["campo"] = normalizar_nombre_columna(str(campos["campo"]))
            campos.setdefault("orden", indice)
            regla.condiciones.append(CondicionRegla(**campos))
        self._repo.sesion.flush()
        self._repo.sesion.refresh(regla)
        return ReglaClasificacionDTO.model_validate(regla)

    def desactivar_regla(self, regla_id: int) -> ReglaClasificacionDTO:
        return self.actualizar_regla(regla_id, ReglaClasificacionActualizarDTO(activa=False))

    def eliminar_regla(self, regla_id: int) -> None:
        """Elimina fisicamente una regla y sus condiciones."""
        if not self._repo.eliminar(regla_id):
            raise EntidadNoEncontradaError(f"No existe la regla con id {regla_id}.")

    def duplicar_regla(self, regla_id: int, nuevo_nombre: str | None = None) -> ReglaClasificacionDTO:
        """Copia una regla con todas sus condiciones."""
        regla = self._repo.obtener(regla_id)
        if regla is None:
            raise EntidadNoEncontradaError(f"No existe la regla con id {regla_id}.")

        nombre_copia = (nuevo_nombre or f"{regla.nombre}_copia").strip()
        if not nombre_copia:
            raise ValidacionDominioError("El nombre de la copia es obligatorio.")
        if self._repo.listar(nombre=nombre_copia):
            raise DatoDuplicadoError(f"Ya existe una regla con nombre {nombre_copia}.")

        condiciones = [
            CondicionReglaCrearDTO(
                campo=condicion.campo,
                operador=condicion.operador,
                valor_texto=condicion.valor_texto,
                lista_id=condicion.lista_id,
                atributo_farmacia=condicion.atributo_farmacia,
                orden=condicion.orden,
                activa=condicion.activa,
            )
            for condicion in sorted(regla.condiciones, key=lambda c: c.orden)
        ]
        return self.crear_regla(
            ReglaClasificacionCrearDTO(
                nombre=nombre_copia,
                descripcion=regla.descripcion,
                tipologia_resultado=regla.tipologia_resultado,
                prioridad=regla.prioridad,
                activa=regla.activa,
                origen="CREADA_UI",
                version=regla.version,
                condiciones=condiciones,
            )
        )

    def importar_desde_json(self, ruta_json: Path, solo_si_vacio: bool = True) -> list[ReglaClasificacionDTO]:
        if solo_si_vacio and self._repo.listar_activas_ordenadas_por_prioridad():
            return []

        contenido = cargar_json(ruta_json)
        if not isinstance(contenido, list):
            raise ValidacionDominioError("El archivo de reglas debe contener una lista JSON.")

        return self.importar_reglas_json(contenido)

    def importar_reglas_json(self, reglas: Sequence[Mapping[str, Any]]) -> list[ReglaClasificacionDTO]:
        creadas: list[ReglaClasificacionDTO] = []
        for regla_json in reglas:
            datos = self._dto_desde_regla_json(regla_json)
            if self._repo.listar(nombre=datos.nombre):
                continue
            creadas.append(self.crear_regla(datos))
        return creadas

    def sincronizar_reglas_json(self, reglas: Sequence[Mapping[str, Any]]) -> int:
        """Crea o actualiza reglas del catalogo JSON sin tocar copias creadas por UI."""
        cambios = 0
        for regla_json in reglas:
            datos = self._dto_desde_regla_json(regla_json)
            existentes = self._repo.listar(nombre=datos.nombre)
            if not existentes:
                self.crear_regla(datos)
                cambios += 1
                continue

            regla_existente = existentes[0]
            if regla_existente.origen not in ORIGENES_REGLAS_SINCRONIZABLES:
                continue
            self.guardar_regla_con_condiciones(regla_existente.id, datos)
            cambios += 1

        for nombre in REGLAS_LEGACY_A_DESACTIVAR:
            for regla in self._repo.listar(nombre=nombre):
                if regla.activa and regla.origen in ORIGENES_REGLAS_SINCRONIZABLES:
                    self.desactivar_regla(regla.id)
                    cambios += 1
        return cambios

    def obtener_reglas_avanzadas(self) -> list:  # list[ReglaMotor] - importacion diferida
        """Devuelve ReglaMotor usando la sesion de esta instancia (util para tests)."""
        from reglas.motor_reglas_avanzado import CondicionMotor, ReglaMotor  # noqa: PLC0415

        reglas_motor: list[ReglaMotor] = []
        for regla in self._repo.listar_activas_ordenadas_por_prioridad():
            condiciones: list[CondicionMotor] = []
            for condicion in regla.condiciones:
                if not condicion.activa:
                    continue
                campo = normalizar_nombre_columna(condicion.campo)
                valores: list[str] = []
                if condicion.valor_texto:
                    valores.extend(self._leer_valores_texto(condicion.valor_texto))
                valores = [
                    normalizar_valor_por_campo(campo, v)
                    for v in valores
                    if normalizar_valor_por_campo(campo, v)
                ]
                condiciones.append(
                    CondicionMotor(
                        campo=campo,
                        operador=condicion.operador or "EN",
                        valores=valores,
                        lista_id=condicion.lista_id,
                        atributo_farmacia=condicion.atributo_farmacia,
                    )
                )
            if condiciones:
                reglas_motor.append(
                    ReglaMotor(
                        id=regla.id,
                        nombre=regla.nombre,
                        prioridad=int(regla.prioridad),
                        tipologia_resultado=normalizar_texto(regla.tipologia_resultado),
                        condiciones=condiciones,
                    )
                )
        return reglas_motor

    def obtener_reglas_para_motor(self) -> list[dict[str, Any]]:
        reglas_motor: list[dict[str, Any]] = []
        for regla in self._repo.listar_activas_ordenadas_por_prioridad():
            condiciones = self._condiciones_para_motor(regla.condiciones)
            if not condiciones:
                continue
            reglas_motor.append(
                {
                    "nombre_regla": regla.nombre,
                    "prioridad": int(regla.prioridad),
                    "condiciones": condiciones,
                    "resultado": normalizar_texto(regla.tipologia_resultado),
                }
            )
        return reglas_motor

    def _validar_regla(self, datos: ReglaClasificacionCrearDTO) -> None:
        if not datos.nombre.strip():
            raise ValidacionDominioError("El nombre de la regla es obligatorio.")
        if not datos.tipologia_resultado.strip():
            raise ValidacionDominioError("La tipologia resultado es obligatoria.")
        if datos.prioridad < 0:
            raise ValidacionDominioError("La prioridad debe ser mayor o igual a cero.")

        for condicion in datos.condiciones:
            if not condicion.campo.strip():
                raise ValidacionDominioError("Toda condicion debe indicar un campo.")
            if not condicion.operador.strip():
                raise ValidacionDominioError("Toda condicion debe indicar un operador.")
            if condicion.lista_id is not None and self._repo_listas.obtener(condicion.lista_id) is None:
                raise EntidadNoEncontradaError(f"No existe la lista con id {condicion.lista_id}.")
            if condicion.valor_texto is None and condicion.lista_id is None and condicion.atributo_farmacia is None:
                raise ValidacionDominioError("La condicion debe tener valor, lista o atributo de farmacia.")

    def _dto_desde_regla_json(self, regla_json: Mapping[str, Any]) -> ReglaClasificacionCrearDTO:
        nombre = str(regla_json.get("nombre_regla") or regla_json.get("nombre") or "").strip()
        resultado = normalizar_texto(regla_json.get("resultado") or regla_json.get("tipologia_resultado") or "")
        prioridad = int(regla_json.get("prioridad", 100))
        condiciones_json = regla_json.get("condiciones", {})

        if not isinstance(condiciones_json, Mapping):
            raise ValidacionDominioError(f"La regla {nombre or '<sin nombre>'} tiene condiciones invalidas.")

        condiciones = [
            self._condicion_desde_regla_json(campo, definicion, orden)
            for orden, (campo, definicion) in enumerate(condiciones_json.items())
        ]

        return ReglaClasificacionCrearDTO(
            nombre=nombre,
            descripcion=str(regla_json.get("descripcion") or "Migrada desde configuracion JSON."),
            tipologia_resultado=resultado,
            prioridad=prioridad,
            activa=bool(regla_json.get("activa", True)),
            origen="JSON_MIGRADO",
            condiciones=condiciones,
        )

    def _condicion_desde_regla_json(
        self,
        campo: str,
        definicion: Any,
        orden: int,
    ) -> CondicionReglaCrearDTO:
        operador = "EN"
        valores = definicion
        lista_id = None
        atributo_farmacia = None

        if isinstance(definicion, Mapping):
            operador = normalizar_nombre_columna(definicion.get("operador", "EN"))
            valores = definicion.get("valores", definicion.get("valor", definicion.get("valor_texto", [])))
            lista_id = definicion.get("lista_id")
            atributo_farmacia = definicion.get("atributo_farmacia")

        return CondicionReglaCrearDTO(
            campo=str(campo),
            operador=operador,
            valor_texto=json.dumps(self._normalizar_valores_regla(campo, valores), ensure_ascii=False),
            lista_id=lista_id,
            atributo_farmacia=atributo_farmacia,
            orden=orden,
        )

    def _normalizar_valores_regla(self, campo: str, valores: Any) -> list[str]:
        valores_lista = valores if isinstance(valores, list) else [valores]
        return [
            normalizar_valor_por_campo(campo, valor)
            for valor in valores_lista
            if normalizar_valor_por_campo(campo, valor)
        ]

    def _condiciones_para_motor(self, condiciones_orm: Sequence[Any]) -> dict[str, Any]:
        condiciones: dict[str, Any] = {}
        for condicion in condiciones_orm:
            if not condicion.activa:
                continue

            campo = normalizar_nombre_columna(condicion.campo)
            operador = normalizar_nombre_columna(condicion.operador or "EN")
            valores: list[str] = []
            if condicion.valor_texto:
                valores.extend(self._leer_valores_texto(condicion.valor_texto))
            if condicion.lista_id is not None:
                valores.extend(
                    item.valor_normalizado
                    for item in self._repo_items.listar_activos_por_lista(condicion.lista_id)
                )

            valores_normalizados = [
                normalizar_valor_por_campo(campo, valor)
                for valor in valores
                if normalizar_valor_por_campo(campo, valor)
            ]

            if operador in {"VACIO", "NO_VACIO"}:
                condiciones[campo] = {"operador": operador, "valores": []}
            elif operador == "EN_LISTA" and valores_normalizados:
                condiciones.setdefault(campo, [])
                condiciones[campo].extend(valores_normalizados)
            elif operador not in {"EN", "IGUAL"} and valores_normalizados:
                condiciones[campo] = {"operador": operador, "valores": valores_normalizados}
            elif valores_normalizados:
                condiciones.setdefault(campo, [])
                condiciones[campo].extend(valores_normalizados)

        return condiciones

    def _leer_valores_texto(self, valor_texto: str) -> list[str]:
        try:
            valor_json = json.loads(valor_texto)
        except json.JSONDecodeError:
            return [valor_texto]

        if isinstance(valor_json, list):
            return [str(valor) for valor in valor_json]
        return [str(valor_json)]


def asegurar_reglas_iniciales_desde_json(ruta_json: Path | None = None) -> int:
    """Migra reglas legacy JSON a la BD cuando aun no existen reglas activas."""
    ruta = ruta_json or resolver_ruta_proyecto("configuracion", "reglas_tipologia.json")
    with sesion_scope() as sesion:
        servicio = ServicioReglas(sesion)
        reglas = servicio.importar_desde_json(ruta, solo_si_vacio=True)
        return len(reglas)


def sincronizar_reglas_sistema_desde_json(ruta_json: Path | None = None) -> int:
    """Sincroniza reglas del JSON con bases existentes sin sobrescribir reglas creadas por UI."""
    ruta = ruta_json or resolver_ruta_proyecto("configuracion", "reglas_tipologia.json")
    contenido = cargar_json(ruta)
    if not isinstance(contenido, list):
        raise ValidacionDominioError("El archivo de reglas debe contener una lista JSON.")

    with sesion_scope() as sesion:
        servicio = ServicioReglas(sesion)
        return servicio.sincronizar_reglas_json(contenido)


def obtener_reglas_motor_desde_bd(ruta_json_legacy: Path | None = None) -> list[dict[str, Any]]:
    """Obtiene reglas activas desde BD, sembrando desde JSON legacy si la tabla esta vacia."""
    logger = logging.getLogger(__name__)
    ruta = ruta_json_legacy or resolver_ruta_proyecto("configuracion", "reglas_tipologia.json")

    try:
        with sesion_scope() as sesion:
            servicio = ServicioReglas(sesion)
            contenido = cargar_json(ruta)
            if isinstance(contenido, list):
                servicio.sincronizar_reglas_json(contenido)
            if not servicio.listar_reglas_activas():
                servicio.importar_desde_json(ruta, solo_si_vacio=True)
            return servicio.obtener_reglas_para_motor()
    except Exception as error:  # noqa: BLE001
        logger.warning("No fue posible cargar reglas desde BD: %s", error)
        return []


def obtener_reglas_motor_avanzado(ruta_json_legacy: Path | None = None) -> list:  # list[ReglaMotor]
    """Devuelve ReglaMotor con operador, lista_id y atributo_farmacia desde la BD.

    Siembra la BD desde el JSON legacy si aun no existen reglas activas.
    Importacion diferida de reglas.motor_reglas_avanzado para evitar ciclos.
    """
    from reglas.motor_reglas_avanzado import CondicionMotor, ReglaMotor  # noqa: PLC0415

    logger = logging.getLogger(__name__)
    ruta = ruta_json_legacy or resolver_ruta_proyecto("configuracion", "reglas_tipologia.json")

    try:
        with sesion_scope() as sesion:
            servicio = ServicioReglas(sesion)
            contenido = cargar_json(ruta)
            if isinstance(contenido, list):
                servicio.sincronizar_reglas_json(contenido)
            if not servicio.listar_reglas_activas():
                servicio.importar_desde_json(ruta, solo_si_vacio=True)

            reglas_motor: list[ReglaMotor] = []
            for regla in servicio._repo.listar_activas_ordenadas_por_prioridad():
                condiciones: list[CondicionMotor] = []
                for condicion in regla.condiciones:
                    if not condicion.activa:
                        continue
                    campo = normalizar_nombre_columna(condicion.campo)
                    valores: list[str] = []
                    if condicion.valor_texto:
                        valores.extend(servicio._leer_valores_texto(condicion.valor_texto))
                    valores = [
                        normalizar_valor_por_campo(campo, v)
                        for v in valores
                        if normalizar_valor_por_campo(campo, v)
                    ]
                    condiciones.append(
                        CondicionMotor(
                            campo=campo,
                            operador=condicion.operador or "EN",
                            valores=valores,
                            lista_id=condicion.lista_id,
                            atributo_farmacia=condicion.atributo_farmacia,
                        )
                    )
                if condiciones:
                    reglas_motor.append(
                        ReglaMotor(
                            id=regla.id,
                            nombre=regla.nombre,
                            prioridad=int(regla.prioridad),
                            tipologia_resultado=normalizar_texto(regla.tipologia_resultado),
                            condiciones=condiciones,
                        )
                    )
        return reglas_motor
    except Exception as error:  # noqa: BLE001
        logger.warning("No fue posible cargar reglas avanzadas desde BD: %s", error)
        return []


def obtener_contexto_motor() -> Any:  # -> ContextoMotor
    """Construye un ContextoMotor con lookups de farmacias y listas desde la BD.

    Importacion diferida para evitar ciclos entre servicios/ y reglas/.
    """
    from reglas.evaluador_condiciones import ContextoMotor, FarmaciaAtributos  # noqa: PLC0415

    logger = logging.getLogger(__name__)

    try:
        from repositorios.repositorio_farmacias import RepositorioFarmacias  # noqa: PLC0415
        from repositorios.repositorio_lista_items import RepositorioListaItems  # noqa: PLC0415
        from repositorios.repositorio_listas import RepositorioListas  # noqa: PLC0415

        farmacias: dict[str, FarmaciaAtributos] = {}
        listas: dict[int, frozenset[str]] = {}

        with sesion_scope() as sesion:
            repo_farmacias = RepositorioFarmacias(sesion)
            for farmacia in repo_farmacias.listar(activa=True):
                tipo_codigo = (
                    normalizar_texto(farmacia.tipo_farmacia.codigo) if farmacia.tipo_farmacia is not None else ""
                )
                atributos = FarmaciaAtributos(
                    tipo_codigo=tipo_codigo,
                    puede_prestar=bool(farmacia.puede_prestar),
                    es_interna=bool(farmacia.es_interna),
                    es_externa=bool(farmacia.es_externa),
                )
                farmacias[normalizar_codigo(farmacia.codigo)] = atributos
                farmacias[normalizar_codigo(farmacia.nombre_normalizado)] = atributos

            repo_listas = RepositorioListas(sesion)
            repo_items = RepositorioListaItems(sesion)
            for lista in repo_listas.listar_activas():
                items = repo_items.listar_activos_por_lista(lista.id)
                listas[lista.id] = frozenset(item.valor_normalizado for item in items)

        return ContextoMotor(farmacias=farmacias, listas=listas)
    except Exception as error:  # noqa: BLE001
        logger.warning("No fue posible construir el contexto del motor: %s", error)
        from reglas.evaluador_condiciones import ContextoMotor  # noqa: PLC0415

        return ContextoMotor()
