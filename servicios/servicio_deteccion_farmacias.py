"""Deteccion avanzada de farmacias desde movimientos."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from dto.deteccion_farmacias_dto import (
    ConfirmacionFarmaciaDetectadaDTO,
    FarmaciaDetectadaDTO,
    ResultadoConfirmacionFarmaciasDTO,
    ResultadoDeteccionFarmaciasDTO,
)
from dto.farmacia_dto import FarmaciaActualizarDTO, FarmaciaDTO
from persistencia.modelos_orm import Farmacia
from repositorios.repositorio_clinicas import RepositorioClinicas
from repositorios.repositorio_ejecuciones import RepositorioEjecuciones
from repositorios.repositorio_farmacias import RepositorioFarmacias
from repositorios.repositorio_tipos_farmacia import RepositorioTiposFarmacia
from servicios.excepciones import EntidadNoEncontradaError, ValidacionDominioError
from servicios.servicio_farmacias import ServicioFarmacias
from utilidades.texto import normalizar_nombre_columna, normalizar_texto


ESTADOS_DETECCION = {"EXISTENTE", "NUEVA", "AMBIGUA", "IGNORADA"}
TIPOS_SUGERIDOS = {"INTERNA", "EXTERNA", "CEDI", "DEVOLUCIONES", "ALMACEN", "NO_CLASIFICABLE"}
COLUMNAS_ORGANIZACION = ("ORG_ORIGEN", "ORG_DESTINO")


@dataclass
class _OrganizacionDetectada:
    nombre: str
    cantidad: int = 0
    columnas: set[str] = field(default_factory=set)


class ServicioDeteccionFarmacias:
    """Detecta organizaciones de farmacia y propone clasificacion inicial."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion
        self._repo_farmacias = RepositorioFarmacias(sesion)
        self._repo_tipos = RepositorioTiposFarmacia(sesion)
        self._repo_clinicas = RepositorioClinicas(sesion)
        self._repo_ejecuciones = RepositorioEjecuciones(sesion)
        self._detecciones_por_ejecucion: dict[int, list[FarmaciaDetectadaDTO]] = {}

    def detectar_farmacias_en_archivo(
        self,
        ruta_archivo: str | Path,
        clinica_id: int | None = None,
    ) -> ResultadoDeteccionFarmaciasDTO:
        ruta = Path(ruta_archivo)
        if not ruta.exists() or not ruta.is_file():
            raise ValidacionDominioError(f"No existe el archivo de movimientos: {ruta}.")
        if clinica_id is not None and self._repo_clinicas.obtener(clinica_id) is None:
            raise EntidadNoEncontradaError(f"No existe la clinica con id {clinica_id}.")

        dataframe = self._leer_excel(ruta)
        ejecucion = self._repo_ejecuciones.crear_iniciada(
            archivo_nombre=ruta.name,
            archivo_ruta=str(ruta),
            clinica_id=clinica_id,
            mensaje="Deteccion de farmacias",
        )
        resultado = self.detectar_farmacias(dataframe, clinica_id=clinica_id, ejecucion_id=ejecucion.id)
        self._repo_ejecuciones.marcar_finalizada(
            ejecucion.id,
            estado="VALIDADA",
            totales={
                "total_registros": resultado.total_registros,
                "total_columnas": len(dataframe.columns),
                "total_clasificados": 0,
                "total_sin_clasificar": 0,
            },
            mensaje=f"Farmacias detectadas: {resultado.total_organizaciones}",
        )
        self._detecciones_por_ejecucion[ejecucion.id] = resultado.farmacias_detectadas
        return resultado

    def detectar_farmacias(
        self,
        datos: pd.DataFrame,
        clinica_id: int | None = None,
        ejecucion_id: int | None = None,
    ) -> ResultadoDeteccionFarmaciasDTO:
        if clinica_id is not None and self._repo_clinicas.obtener(clinica_id) is None:
            raise EntidadNoEncontradaError(f"No existe la clinica con id {clinica_id}.")

        columnas = self._resolver_columnas_organizacion(datos)
        conteos = self._contar_organizaciones(datos, columnas)
        detectadas = [
            self._detectar_organizacion(organizacion)
            for organizacion in conteos.values()
        ]
        detectadas = sorted(
            detectadas,
            key=lambda farmacia: (farmacia.estado_deteccion, farmacia.nombre_normalizado, farmacia.nombre_detectado),
        )

        resultado = ResultadoDeteccionFarmaciasDTO(
            ejecucion_id=ejecucion_id,
            clinica_id=clinica_id,
            total_registros=len(datos),
            total_organizaciones=len(detectadas),
            columnas_analizadas=columnas,
            farmacias_detectadas=detectadas,
        )
        if ejecucion_id is not None:
            self._detecciones_por_ejecucion[ejecucion_id] = detectadas
        return resultado

    def listar_farmacias_detectadas(self, ejecucion_id: int) -> list[FarmaciaDetectadaDTO]:
        """Retorna las detecciones hechas por esta instancia para una ejecucion."""
        return list(self._detecciones_por_ejecucion.get(ejecucion_id, []))

    def confirmar_farmacia_detectada(
        self,
        confirmacion: ConfirmacionFarmaciaDetectadaDTO,
    ) -> ResultadoConfirmacionFarmaciasDTO:
        servicio_farmacias = ServicioFarmacias(self._sesion)
        creadas = 0
        actualizadas = 0
        asociadas = 0

        if confirmacion.farmacia_id is None:
            farmacia = servicio_farmacias.crear_desde_deteccion(
                codigo_detectado=confirmacion.codigo_detectado,
                nombre_detectado=confirmacion.nombre_detectado,
                tipo_codigo=confirmacion.tipo_codigo,
                puede_prestar=confirmacion.puede_prestar,
                es_interna=confirmacion.es_interna,
                es_externa=confirmacion.es_externa,
            )
            creadas = 1
        else:
            campos_actualizacion: dict[str, Any] = {}
            tipo = self._repo_tipos.buscar_por_codigo(confirmacion.tipo_codigo)
            if tipo is None:
                raise EntidadNoEncontradaError(f"No existe el tipo de farmacia {confirmacion.tipo_codigo}.")
            campos_actualizacion["tipo_farmacia_id"] = tipo.id
            if confirmacion.puede_prestar is not None:
                campos_actualizacion["puede_prestar"] = confirmacion.puede_prestar
            if confirmacion.es_interna is not None:
                campos_actualizacion["es_interna"] = confirmacion.es_interna
            if confirmacion.es_externa is not None:
                campos_actualizacion["es_externa"] = confirmacion.es_externa
            farmacia = servicio_farmacias.actualizar_farmacia(
                confirmacion.farmacia_id,
                FarmaciaActualizarDTO(**campos_actualizacion),
            )
            actualizadas = 1

        if confirmacion.clinica_id is not None:
            farmacia = servicio_farmacias.asociar_a_clinica(
                farmacia.id,
                confirmacion.clinica_id,
                relacion=confirmacion.relacion_clinica,
            )
            asociadas = 1

        return ResultadoConfirmacionFarmaciasDTO(
            total_confirmadas=1,
            total_creadas=creadas,
            total_actualizadas=actualizadas,
            total_asociadas=asociadas,
            farmacias=[farmacia],
            errores=[],
        )

    def crear_farmacia_desde_deteccion(
        self,
        farmacia_detectada: FarmaciaDetectadaDTO,
        tipo_codigo: str | None = None,
        clinica_id: int | None = None,
    ) -> FarmaciaDTO:
        servicio_farmacias = ServicioFarmacias(self._sesion)
        farmacia = servicio_farmacias.crear_desde_deteccion(
            codigo_detectado=farmacia_detectada.codigo_detectado,
            nombre_detectado=farmacia_detectada.nombre_detectado,
            tipo_codigo=tipo_codigo or farmacia_detectada.tipo_sugerido or "NO_CLASIFICABLE",
            puede_prestar=farmacia_detectada.puede_prestar,
            es_interna=farmacia_detectada.es_interna,
            es_externa=farmacia_detectada.es_externa,
        )
        if clinica_id is not None:
            return servicio_farmacias.asociar_a_clinica(farmacia.id, clinica_id)
        return farmacia

    def asociar_farmacia_a_clinica(
        self,
        farmacia_id: int,
        clinica_id: int,
        relacion: str | None = None,
    ) -> FarmaciaDTO:
        return ServicioFarmacias(self._sesion).asociar_a_clinica(farmacia_id, clinica_id, relacion=relacion)

    def marcar_farmacia_como_cedi(self, farmacia_id: int) -> FarmaciaDTO:
        return ServicioFarmacias(self._sesion).marcar_como_cedi(farmacia_id)

    def marcar_farmacia_como_no_puede_prestar(self, farmacia_id: int) -> FarmaciaDTO:
        return ServicioFarmacias(self._sesion).marcar_puede_prestar(farmacia_id, False)

    @staticmethod
    def extraer_codigo_desde_texto(texto: Any) -> str | None:
        codigo, _nombre = ServicioDeteccionFarmacias.extraer_codigo_y_nombre(texto)
        return codigo

    @staticmethod
    def extraer_codigo_y_nombre(texto: Any) -> tuple[str | None, str]:
        if texto is None:
            return None, ""

        valor = str(texto).strip()
        if not valor or valor.lower() == "nan":
            return None, ""

        coincidencia = re.match(r"^\s*(?P<codigo>[A-Za-z]{0,8}\d+[A-Za-z0-9]*)\s*[_\-:]\s*(?P<nombre>.+)$", valor)
        if coincidencia:
            return coincidencia.group("codigo").strip(), coincidencia.group("nombre").strip()

        coincidencia = re.match(r"^\s*(?P<codigo>\d+)\s+(?P<nombre>.+)$", valor)
        if coincidencia:
            return coincidencia.group("codigo").strip(), coincidencia.group("nombre").strip()

        return None, valor

    @staticmethod
    def sugerir_tipo_farmacia(nombre: Any, *, desde_org_destino: bool = False) -> str:
        if desde_org_destino:
            return "INTERNA"
        nombre_normalizado = normalizar_texto(nombre)
        if "CEDI" in nombre_normalizado:
            return "CEDI"
        if "DEVOL" in nombre_normalizado:
            return "DEVOLUCIONES"
        if "REEMPAQUE" in nombre_normalizado or "REENVASE" in nombre_normalizado:
            return "REEMPAQUE"
        if "ALMACEN" in nombre_normalizado:
            return "ALMACEN"
        if "FARM" in nombre_normalizado:
            return "EXTERNA"
        return "NO_CLASIFICABLE"

    def _detectar_organizacion(self, organizacion: _OrganizacionDetectada) -> FarmaciaDetectadaDTO:
        nombre_detectado = organizacion.nombre
        codigo_detectado, nombre_sin_codigo = self.extraer_codigo_y_nombre(nombre_detectado)
        nombre_normalizado = normalizar_texto(nombre_sin_codigo)
        if not nombre_normalizado:
            return FarmaciaDetectadaDTO(
                codigo_detectado=None,
                nombre_detectado=nombre_detectado,
                nombre_normalizado="",
                cantidad_registros=organizacion.cantidad,
                estado_deteccion="IGNORADA",
                tipo_sugerido=None,
                farmacia_id=None,
                puede_prestar=None,
                es_interna=None,
                es_externa=None,
            )

        candidatas = self._repo_farmacias.buscar_por_codigo_o_nombre(codigo_detectado, nombre_sin_codigo)
        farmacia_existente = self._resolver_farmacia_existente(candidatas, codigo_detectado, nombre_sin_codigo)
        if farmacia_existente is not None:
            estado = "EXISTENTE"
            farmacia_id = farmacia_existente.id
            puede_prestar = farmacia_existente.puede_prestar
            es_interna = farmacia_existente.es_interna
            es_externa = farmacia_existente.es_externa
        elif candidatas:
            estado = "AMBIGUA"
            farmacia_id = None
            puede_prestar = True
            es_interna = None
            es_externa = None
        else:
            estado = "NUEVA"
            farmacia_id = None
            puede_prestar = True
            es_interna = None
            es_externa = None

        desde_org_destino = "ORG_DESTINO" in organizacion.columnas
        tipo_sugerido = self.sugerir_tipo_farmacia(
            nombre_detectado,
            desde_org_destino=desde_org_destino,
        )
        if es_interna is None:
            es_interna = tipo_sugerido == "INTERNA"
        if es_externa is None:
            es_externa = tipo_sugerido == "EXTERNA"

        return FarmaciaDetectadaDTO(
            codigo_detectado=codigo_detectado,
            nombre_detectado=nombre_detectado,
            nombre_normalizado=nombre_normalizado,
            cantidad_registros=organizacion.cantidad,
            estado_deteccion=estado,
            tipo_sugerido=tipo_sugerido,
            farmacia_id=farmacia_id,
            puede_prestar=puede_prestar,
            es_interna=es_interna,
            es_externa=es_externa,
        )

    def _resolver_farmacia_existente(
        self,
        candidatas: list[Farmacia],
        codigo_detectado: str | None,
        nombre_sin_codigo: str,
    ) -> Farmacia | None:
        if not candidatas:
            return None

        nombre_normalizado = normalizar_texto(nombre_sin_codigo)
        exactas = [
            farmacia
            for farmacia in candidatas
            if farmacia.nombre_normalizado == nombre_normalizado
            or (
                codigo_detectado is not None
                and farmacia.codigo == codigo_detectado
                and len(candidatas) == 1
            )
        ]
        if len(exactas) == 1:
            return exactas[0]
        if len(candidatas) == 1:
            return candidatas[0]
        return None

    def _resolver_columnas_organizacion(self, dataframe: pd.DataFrame) -> list[str]:
        columnas_por_nombre = {
            normalizar_nombre_columna(columna): str(columna) for columna in dataframe.columns
        }
        columnas = [
            columnas_por_nombre[columna]
            for columna in COLUMNAS_ORGANIZACION
            if columna in columnas_por_nombre
        ]
        if not columnas:
            esperadas = ", ".join(COLUMNAS_ORGANIZACION)
            disponibles = ", ".join(str(columna) for columna in dataframe.columns)
            raise ValidacionDominioError(
                f"No se encontraron columnas de organizacion ({esperadas}). Columnas disponibles: {disponibles}."
            )
        return columnas

    def _contar_organizaciones(self, dataframe: pd.DataFrame, columnas: list[str]) -> dict[str, _OrganizacionDetectada]:
        conteos: dict[str, _OrganizacionDetectada] = {}
        for _indice, fila in dataframe.iterrows():
            organizaciones_fila: dict[str, set[str]] = {}
            for columna in columnas:
                organizacion = self._texto_celda(fila.get(columna))
                if not organizacion:
                    continue
                columna_normalizada = normalizar_nombre_columna(columna)
                organizaciones_fila.setdefault(organizacion, set()).add(columna_normalizada)
            for organizacion, columnas_origen in organizaciones_fila.items():
                deteccion = conteos.setdefault(
                    organizacion,
                    _OrganizacionDetectada(nombre=organizacion),
                )
                deteccion.cantidad += 1
                deteccion.columnas.update(columnas_origen)
        return conteos

    def _leer_excel(self, ruta: Path) -> pd.DataFrame:
        try:
            return pd.read_excel(ruta, dtype=object)
        except Exception as exc:
            raise ValidacionDominioError(f"No se pudo leer el archivo de movimientos {ruta}: {exc}") from exc

    def _texto_celda(self, valor: Any) -> str | None:
        if valor is None:
            return None
        try:
            if bool(pd.isna(valor)):
                return None
        except (TypeError, ValueError):
            pass
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        texto = str(valor).strip()
        return texto or None
