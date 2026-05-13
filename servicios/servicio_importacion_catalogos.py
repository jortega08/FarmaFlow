"""Importacion de catalogos configurables desde Excel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from dto.importacion_catalogo_dto import (
    ErrorImportacionDTO,
    ItemImportacionDTO,
    PrevisualizacionImportacionDTO,
    ResultadoImportacionCatalogoDTO,
)
from repositorios.repositorio_lista_items import RepositorioListaItems
from repositorios.repositorio_listas import RepositorioListas
from servicios.excepciones import EntidadNoEncontradaError, ValidacionDominioError
from utilidades.texto import normalizar_nombre_columna, normalizar_texto


EXTENSIONES_EXCEL_PERMITIDAS = {".xlsx", ".xls", ".xlsm"}


class ServicioImportacionCatalogos:
    """Carga items reutilizables en listas configurables."""

    def __init__(self, sesion: Session) -> None:
        self._repo_listas = RepositorioListas(sesion)
        self._repo_items = RepositorioListaItems(sesion)

    def validar_archivo_catalogo(self, ruta_archivo: str | Path) -> PrevisualizacionImportacionDTO:
        """Valida que la ruta sea un Excel legible y retorna sus columnas."""
        ruta = self._validar_ruta_excel(ruta_archivo)
        dataframe = self._leer_excel(ruta)
        return PrevisualizacionImportacionDTO(
            ruta_archivo=str(ruta),
            columnas=[str(columna) for columna in dataframe.columns],
            total_filas=len(dataframe),
            filas=[],
            errores=[],
        )

    def previsualizar_importacion(
        self,
        ruta_archivo: str | Path,
        limite: int = 20,
    ) -> PrevisualizacionImportacionDTO:
        if limite < 1:
            raise ValidacionDominioError("El limite de previsualizacion debe ser mayor o igual a 1.")

        ruta = self._validar_ruta_excel(ruta_archivo)
        dataframe = self._leer_excel(ruta)
        filas = [
            {str(columna): self._valor_serializable(valor) for columna, valor in fila.items()}
            for fila in dataframe.head(limite).to_dict(orient="records")
        ]
        return PrevisualizacionImportacionDTO(
            ruta_archivo=str(ruta),
            columnas=[str(columna) for columna in dataframe.columns],
            total_filas=len(dataframe),
            filas=filas,
            errores=[],
        )

    def importar_articulos_desde_excel(
        self,
        lista_id: int,
        ruta_archivo: str | Path,
        columna_codigo: str,
        columna_descripcion: str,
    ) -> ResultadoImportacionCatalogoDTO:
        return self._importar_items(
            lista_id=lista_id,
            ruta_archivo=ruta_archivo,
            columna_codigo=columna_codigo,
            columna_valor=columna_codigo,
            columna_descripcion=columna_descripcion,
            tipo_lista_esperado="ARTICULOS",
        )

    def importar_farmacias_desde_excel(
        self,
        lista_id: int,
        ruta_archivo: str | Path,
        columna_codigo: str,
        columna_nombre: str,
    ) -> ResultadoImportacionCatalogoDTO:
        return self._importar_items(
            lista_id=lista_id,
            ruta_archivo=ruta_archivo,
            columna_codigo=columna_codigo,
            columna_valor=columna_nombre,
            columna_descripcion=None,
            tipo_lista_esperado="FARMACIAS",
        )

    def _importar_items(
        self,
        *,
        lista_id: int,
        ruta_archivo: str | Path,
        columna_codigo: str,
        columna_valor: str,
        columna_descripcion: str | None,
        tipo_lista_esperado: str,
    ) -> ResultadoImportacionCatalogoDTO:
        lista = self._repo_listas.obtener(lista_id)
        if lista is None:
            raise EntidadNoEncontradaError(f"No existe la lista con id {lista_id}.")
        if lista.tipo_lista != tipo_lista_esperado:
            raise ValidacionDominioError(
                f"La lista {lista_id} es de tipo {lista.tipo_lista}; se esperaba {tipo_lista_esperado}."
            )

        ruta = self._validar_ruta_excel(ruta_archivo)
        dataframe = self._leer_excel(ruta)
        columna_codigo_real = self._resolver_columna(dataframe, columna_codigo)
        columna_valor_real = self._resolver_columna(dataframe, columna_valor)
        columna_descripcion_real = (
            self._resolver_columna(dataframe, columna_descripcion) if columna_descripcion else None
        )

        creados = 0
        duplicados = 0
        ignorados = 0
        errores: list[ErrorImportacionDTO] = []
        items_creados: list[ItemImportacionDTO] = []
        vistos_en_archivo: set[str] = set()

        for indice, fila in dataframe.iterrows():
            numero_fila = int(indice) + 2
            codigo = self._texto_celda(fila.get(columna_codigo_real))
            valor = self._texto_celda(fila.get(columna_valor_real))
            descripcion = (
                self._texto_celda(fila.get(columna_descripcion_real))
                if columna_descripcion_real is not None
                else None
            )

            if not valor:
                valor = codigo
            if not valor:
                ignorados += 1
                errores.append(
                    ErrorImportacionDTO(
                        fila=numero_fila,
                        columna=str(columna_valor_real),
                        mensaje="Fila sin valor importable.",
                    )
                )
                continue

            valor_normalizado = normalizar_texto(valor)
            if not valor_normalizado:
                ignorados += 1
                continue

            if valor_normalizado in vistos_en_archivo or self._repo_items.buscar_en_lista(lista_id, valor):
                duplicados += 1
                continue

            item = self._repo_items.crear(
                lista_id=lista_id,
                codigo=codigo,
                valor=valor,
                descripcion=descripcion,
                activo=True,
            )
            vistos_en_archivo.add(item.valor_normalizado)
            creados += 1
            items_creados.append(
                ItemImportacionDTO(
                    fila=numero_fila,
                    codigo=item.codigo,
                    valor=item.valor,
                    descripcion=item.descripcion,
                    valor_normalizado=item.valor_normalizado,
                    estado="CREADO",
                )
            )

        return ResultadoImportacionCatalogoDTO(
            lista_id=lista.id,
            tipo_lista=lista.tipo_lista,
            total_filas=len(dataframe),
            creados=creados,
            duplicados=duplicados,
            ignorados=ignorados,
            errores=errores,
            items_creados=items_creados,
        )

    def _validar_ruta_excel(self, ruta_archivo: str | Path) -> Path:
        ruta = Path(ruta_archivo)
        if not ruta.exists():
            raise ValidacionDominioError(f"No existe el archivo de catalogo: {ruta}.")
        if not ruta.is_file():
            raise ValidacionDominioError(f"La ruta de catalogo no es un archivo: {ruta}.")
        if ruta.suffix.lower() not in EXTENSIONES_EXCEL_PERMITIDAS:
            permitidas = ", ".join(sorted(EXTENSIONES_EXCEL_PERMITIDAS))
            raise ValidacionDominioError(f"Formato de catalogo no soportado. Use: {permitidas}.")
        return ruta

    def _leer_excel(self, ruta: Path) -> pd.DataFrame:
        try:
            return pd.read_excel(ruta, dtype=object)
        except Exception as exc:
            raise ValidacionDominioError(f"No se pudo leer el archivo de catalogo {ruta}: {exc}") from exc

    def _resolver_columna(self, dataframe: pd.DataFrame, columna: str) -> str:
        if columna in dataframe.columns:
            return columna

        columna_normalizada = normalizar_nombre_columna(columna)
        columnas_por_nombre = {
            normalizar_nombre_columna(columna_existente): str(columna_existente)
            for columna_existente in dataframe.columns
        }
        columna_resuelta = columnas_por_nombre.get(columna_normalizada)
        if columna_resuelta is None:
            disponibles = ", ".join(str(columna_existente) for columna_existente in dataframe.columns)
            raise ValidacionDominioError(
                f"No existe la columna {columna}. Columnas disponibles: {disponibles}."
            )
        return columna_resuelta

    def _texto_celda(self, valor: Any) -> str | None:
        if self._es_vacio(valor):
            return None
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        return str(valor).strip()

    def _valor_serializable(self, valor: Any) -> str | int | float | bool | None:
        if self._es_vacio(valor):
            return None
        if isinstance(valor, float) and valor.is_integer():
            return int(valor)
        return valor if isinstance(valor, str | int | float | bool) else str(valor)

    def _es_vacio(self, valor: Any) -> bool:
        if valor is None:
            return True
        try:
            if bool(pd.isna(valor)):
                return True
        except (TypeError, ValueError):
            pass
        return str(valor).strip() == ""
