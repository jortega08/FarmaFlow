"""DTOs Pydantic para entrada y salida de servicios."""

from dto.clinica_dto import ClinicaActualizarDTO, ClinicaCrearDTO, ClinicaDTO
from dto.ejecucion_dto import EjecucionCrearDTO, EjecucionDTO, EjecucionFinalizarDTO
from dto.deteccion_farmacias_dto import (
    ConfirmacionFarmaciaDetectadaDTO,
    FarmaciaDetectadaActualizarDTO,
    FarmaciaDetectadaDTO,
    ResultadoConfirmacionFarmaciasDTO,
    ResultadoDeteccionFarmaciasDTO,
)
from dto.farmacia_dto import FarmaciaActualizarDTO, FarmaciaCrearDTO, FarmaciaDTO, TipoFarmaciaDTO
from dto.importacion_catalogo_dto import (
    ErrorImportacionDTO,
    ItemImportacionDTO,
    PrevisualizacionImportacionDTO,
    ResultadoImportacionCatalogoDTO,
)
from dto.lista_dto import (
    ItemListaActualizarDTO,
    ItemListaCrearDTO,
    ItemListaDTO,
    ListaConfigurableActualizarDTO,
    ListaConfigurableCrearDTO,
    ListaConfigurableDTO,
)
from dto.regla_dto import (
    CondicionReglaCrearDTO,
    CondicionReglaDTO,
    ReglaClasificacionActualizarDTO,
    ReglaClasificacionCrearDTO,
    ReglaClasificacionDTO,
)

__all__ = [
    "ClinicaActualizarDTO",
    "ClinicaCrearDTO",
    "ClinicaDTO",
    "CondicionReglaCrearDTO",
    "CondicionReglaDTO",
    "ConfirmacionFarmaciaDetectadaDTO",
    "EjecucionCrearDTO",
    "EjecucionDTO",
    "EjecucionFinalizarDTO",
    "ErrorImportacionDTO",
    "FarmaciaActualizarDTO",
    "FarmaciaCrearDTO",
    "FarmaciaDetectadaActualizarDTO",
    "FarmaciaDetectadaDTO",
    "FarmaciaDTO",
    "ItemImportacionDTO",
    "ItemListaActualizarDTO",
    "ItemListaCrearDTO",
    "ItemListaDTO",
    "ListaConfigurableActualizarDTO",
    "ListaConfigurableCrearDTO",
    "ListaConfigurableDTO",
    "PrevisualizacionImportacionDTO",
    "ReglaClasificacionActualizarDTO",
    "ReglaClasificacionCrearDTO",
    "ReglaClasificacionDTO",
    "ResultadoConfirmacionFarmaciasDTO",
    "ResultadoDeteccionFarmaciasDTO",
    "ResultadoImportacionCatalogoDTO",
    "TipoFarmaciaDTO",
]
