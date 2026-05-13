"""Validacion estructural para archivos Oracle."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from modelos.resultado_validacion import ResultadoValidacion
from utilidades.rutas import cargar_json, resolver_ruta_proyecto
from utilidades.texto import normalizar_nombre_columna


class ValidadorEstructura:
    """Valida columnas requeridas y detecta alias configurados."""

    def __init__(
        self,
        ruta_columnas_requeridas: Path | None = None,
        ruta_alias_columnas: Path | None = None,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._ruta_columnas_requeridas = ruta_columnas_requeridas or resolver_ruta_proyecto(
            "configuracion",
            "columnas_requeridas.json",
        )
        self._ruta_alias_columnas = ruta_alias_columnas or resolver_ruta_proyecto(
            "configuracion",
            "alias_columnas.json",
        )

    def validar(self, columnas_archivo: list[str]) -> ResultadoValidacion:
        """Valida la estructura del archivo contra la configuracion Oracle."""
        self._logger.info("Iniciando validacion estructural con %s columnas.", len(columnas_archivo))

        try:
            configuracion_columnas = cargar_json(self._ruta_columnas_requeridas)
            alias_configurados = cargar_json(self._ruta_alias_columnas)
        except Exception as error:  # noqa: BLE001
            self._logger.exception("No fue posible cargar la configuracion de validacion.")
            return ResultadoValidacion(
                exito=False,
                mensaje=f"No fue posible cargar la configuracion de validacion: {error}",
                columnas_originales=list(columnas_archivo),
                columnas_normalizadas=[normalizar_nombre_columna(columna) for columna in columnas_archivo],
            )

        columnas_requeridas = [
            normalizar_nombre_columna(columna)
            for columna in configuracion_columnas.get("columnas_requeridas", [])
        ]
        columnas_opcionales = [
            normalizar_nombre_columna(columna)
            for columna in configuracion_columnas.get("columnas_opcionales", [])
        ]

        indice_alias = self._construir_indice_alias(alias_configurados)
        columnas_mapeadas: dict[str, str] = {}
        columnas_desconocidas: list[str] = []

        for columna_original in columnas_archivo:
            columna_normalizada = normalizar_nombre_columna(columna_original)
            columna_canonica = indice_alias.get(columna_normalizada)

            if not columna_canonica:
                columnas_desconocidas.append(str(columna_original))
                continue

            if columna_canonica in columnas_mapeadas:
                self._logger.warning(
                    "Se encontro una columna duplicada para %s. Se conserva la primera coincidencia: %s",
                    columna_canonica,
                    columnas_mapeadas[columna_canonica],
                )
                continue

            columnas_mapeadas[columna_canonica] = str(columna_original)

        columnas_encontradas = [
            columna
            for columna in [*columnas_requeridas, *columnas_opcionales]
            if columna in columnas_mapeadas
        ]
        columnas_faltantes = [
            columna for columna in columnas_requeridas if columna not in columnas_mapeadas
        ]
        estructura_valida = not columnas_faltantes

        mensaje = (
            "Estructura Oracle valida. Se identificaron las columnas minimas requeridas."
            if estructura_valida
            else "La estructura Oracle es invalida. Faltan columnas requeridas para continuar."
        )

        self._logger.info(
            "Validacion finalizada. Estructura valida: %s. Faltantes: %s. Mapeadas: %s.",
            estructura_valida,
            len(columnas_faltantes),
            len(columnas_mapeadas),
        )

        return ResultadoValidacion(
            exito=True,
            mensaje=mensaje,
            columnas_originales=[str(columna) for columna in columnas_archivo],
            columnas_normalizadas=[normalizar_nombre_columna(columna) for columna in columnas_archivo],
            columnas_encontradas=columnas_encontradas,
            columnas_faltantes=columnas_faltantes,
            columnas_mapeadas=columnas_mapeadas,
            columnas_desconocidas=columnas_desconocidas,
            estructura_valida=estructura_valida,
        )

    def _construir_indice_alias(self, alias_configurados: dict[str, Any]) -> dict[str, str]:
        """Genera un indice de alias normalizados a nombre canonico."""
        indice_alias: dict[str, str] = {}

        for columna_canonica, aliases in alias_configurados.items():
            columna_normalizada = normalizar_nombre_columna(columna_canonica)
            indice_alias[columna_normalizada] = columna_normalizada

            for alias in aliases:
                indice_alias[normalizar_nombre_columna(alias)] = columna_normalizada

        return indice_alias
