"""DTOs para deteccion y confirmacion de farmacias."""

from __future__ import annotations

from pydantic import BaseModel

from dto.farmacia_dto import FarmaciaDTO


class FarmaciaDetectadaDTO(BaseModel):
    codigo_detectado: str | None
    nombre_detectado: str
    nombre_normalizado: str
    cantidad_registros: int
    estado_deteccion: str
    tipo_sugerido: str | None
    farmacia_id: int | None
    puede_prestar: bool | None
    es_interna: bool | None
    es_externa: bool | None


class ResultadoDeteccionFarmaciasDTO(BaseModel):
    ejecucion_id: int | None = None
    clinica_id: int | None = None
    total_registros: int
    total_organizaciones: int
    columnas_analizadas: list[str]
    farmacias_detectadas: list[FarmaciaDetectadaDTO]


class FarmaciaDetectadaActualizarDTO(BaseModel):
    codigo_detectado: str | None = None
    nombre_detectado: str | None = None
    tipo_sugerido: str | None = None
    farmacia_id: int | None = None
    puede_prestar: bool | None = None
    es_interna: bool | None = None
    es_externa: bool | None = None


class ConfirmacionFarmaciaDetectadaDTO(BaseModel):
    codigo_detectado: str | None = None
    nombre_detectado: str
    tipo_codigo: str = "NO_CLASIFICABLE"
    farmacia_id: int | None = None
    clinica_id: int | None = None
    puede_prestar: bool | None = None
    es_interna: bool | None = None
    es_externa: bool | None = None
    relacion_clinica: str | None = None


class ResultadoConfirmacionFarmaciasDTO(BaseModel):
    total_confirmadas: int
    total_creadas: int
    total_actualizadas: int
    total_asociadas: int
    farmacias: list[FarmaciaDTO] = []
    errores: list[str] = []
