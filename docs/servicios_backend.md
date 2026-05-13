# Servicios backend

La capa `servicios/` es el contrato recomendado para conectar futuras pantallas PySide6 con SQLite. La UI no debe importar modelos ORM ni repositorios directamente; debe abrir una sesion, crear el servicio requerido y trabajar con DTOs Pydantic.

## Manejo de sesiones

Use `persistencia.conexion.sesion_scope` cuando la operacion deba confirmar cambios:

```python
from persistencia.conexion import sesion_scope
from dto.clinica_dto import ClinicaCrearDTO
from servicios.servicio_clinicas import ServicioClinicas

with sesion_scope() as sesion:
    servicio = ServicioClinicas(sesion)
    clinica = servicio.crear_clinica(ClinicaCrearDTO(codigo="CRS", nombre="Clinica del Rosario"))
```

Para pruebas se puede inyectar una sesion temporal sin usar la base local.

## Servicios disponibles

`ServicioClinicas`

- `crear_clinica(ClinicaCrearDTO) -> ClinicaDTO`
- `listar_clinicas(activa: bool | None = None) -> list[ClinicaDTO]`
- `buscar(texto: str, pagina: int = 1, filas_por_pagina: int = 20) -> list[ClinicaDTO]`
- `obtener_clinica(clinica_id: int) -> ClinicaDTO`
- `obtener_o_error(clinica_id: int) -> ClinicaDTO`
- `listar_farmacias_de_clinica(clinica_id: int) -> list[FarmaciaDTO]`
- `actualizar_clinica(clinica_id: int, ClinicaActualizarDTO) -> ClinicaDTO`
- `desactivar_clinica(clinica_id: int) -> ClinicaDTO`

estudiantes

2 false
3 true
4 true
2 false
1 false


{0,1,2,3,4}

for i=0 , n=4 , i--
    buscar.estudianteid = estudiante
    if estudiante.nota < 3
        paso = false
    if estudiante.nota >= 3
        paso = true
    if not
        print("nota no valida")
    n = n+1


`ServicioFarmacias`

- `crear_farmacia(FarmaciaCrearDTO) -> FarmaciaDTO`
- `listar_farmacias(activa: bool | None = None) -> list[FarmaciaDTO]`
- `buscar(texto: str, pagina: int = 1, filas_por_pagina: int = 20) -> list[FarmaciaDTO]`
- `listar_por_tipo(tipo_codigo: str) -> list[FarmaciaDTO]`
- `buscar_por_codigo_o_nombre(codigo: str | None = None, nombre: str | None = None) -> list[FarmaciaDTO]`
- `obtener_farmacia(farmacia_id: int) -> FarmaciaDTO`
- `actualizar_farmacia(farmacia_id: int, FarmaciaActualizarDTO) -> FarmaciaDTO`
- `desactivar_farmacia(farmacia_id: int) -> FarmaciaDTO`
- `registrar_detectada(codigo: str, nombre_original: str, tipo_codigo: str = "NO_CLASIFICABLE") -> FarmaciaDTO`
- `crear_desde_deteccion(...) -> FarmaciaDTO`
- `asociar_a_clinica(farmacia_id: int, clinica_id: int, relacion: str | None = None) -> FarmaciaDTO`
- `marcar_como_cedi(farmacia_id: int) -> FarmaciaDTO`
- `marcar_como_devoluciones(farmacia_id: int) -> FarmaciaDTO`
- `marcar_puede_prestar(farmacia_id: int, puede_prestar: bool = True) -> FarmaciaDTO`

`ServicioListas`

- `crear_lista(ListaConfigurableCrearDTO) -> ListaConfigurableDTO`
- `listar_listas(activa: bool | None = None) -> list[ListaConfigurableDTO]`
- `obtener_lista(lista_id: int) -> ListaConfigurableDTO`
- `obtener_o_error(lista_id: int) -> ListaConfigurableDTO`
- `actualizar_lista(lista_id: int, ListaConfigurableActualizarDTO) -> ListaConfigurableDTO`
- `desactivar_lista(lista_id: int) -> ListaConfigurableDTO`
- `agregar_item(ItemListaCrearDTO) -> ItemListaDTO`
- `agregar_items_masivo(lista_id: int, items: list[ItemListaCrearDTO], ignorar_duplicados: bool = True) -> list[ItemListaDTO]`
- `listar_items(lista_id: int, activos: bool | None = None) -> list[ItemListaDTO]`
- `buscar_items(lista_id: int, texto: str, pagina: int = 1, filas_por_pagina: int = 20) -> list[ItemListaDTO]`
- `actualizar_item(item_id: int, ItemListaActualizarDTO) -> ItemListaDTO`
- `desactivar_item(item_id: int) -> ItemListaDTO`

`ServicioImportacionCatalogos`

- `validar_archivo_catalogo(ruta_archivo) -> PrevisualizacionImportacionDTO`
- `previsualizar_importacion(ruta_archivo, limite: int = 20) -> PrevisualizacionImportacionDTO`
- `importar_articulos_desde_excel(lista_id, ruta_archivo, columna_codigo, columna_descripcion) -> ResultadoImportacionCatalogoDTO`
- `importar_farmacias_desde_excel(lista_id, ruta_archivo, columna_codigo, columna_nombre) -> ResultadoImportacionCatalogoDTO`

Este servicio carga archivos Excel en `lista_items`, valida columnas por nombre normalizado y evita duplicados con `valor_normalizado`. Las importaciones de articulos usan el codigo como valor funcional; las importaciones de farmacias usan el nombre como valor y conservan el codigo en el campo `codigo`.

`ServicioDeteccionFarmacias`

- `detectar_farmacias(datos: pandas.DataFrame, clinica_id: int | None = None, ejecucion_id: int | None = None) -> ResultadoDeteccionFarmaciasDTO`
- `detectar_farmacias_en_archivo(ruta_archivo, clinica_id: int | None = None) -> ResultadoDeteccionFarmaciasDTO`
- `listar_farmacias_detectadas(ejecucion_id: int) -> list[FarmaciaDetectadaDTO]`
- `confirmar_farmacia_detectada(ConfirmacionFarmaciaDetectadaDTO) -> ResultadoConfirmacionFarmaciasDTO`
- `crear_farmacia_desde_deteccion(FarmaciaDetectadaDTO, tipo_codigo: str | None = None, clinica_id: int | None = None) -> FarmaciaDTO`
- `asociar_farmacia_a_clinica(farmacia_id: int, clinica_id: int, relacion: str | None = None) -> FarmaciaDTO`
- `marcar_farmacia_como_cedi(farmacia_id: int) -> FarmaciaDTO`
- `marcar_farmacia_como_no_puede_prestar(farmacia_id: int) -> FarmaciaDTO`

La deteccion lee `ORG_ORIGEN` y `ORG_DESTINO` aceptando variantes como `ORG ORIGEN` por normalizacion de encabezados. Para cada organizacion detectada retorna `codigo_detectado`, `nombre_detectado`, `nombre_normalizado`, cantidad de registros, estado (`EXISTENTE`, `NUEVA`, `AMBIGUA`, `IGNORADA`) y tipo sugerido (`INTERNA`, `EXTERNA`, `CEDI`, `DEVOLUCIONES`, `ALMACEN`, `NO_CLASIFICABLE`).

`ServicioReglas`

- `crear_regla(ReglaClasificacionCrearDTO) -> ReglaClasificacionDTO`
- `listar_reglas(activa: bool | None = None) -> list[ReglaClasificacionDTO]`
- `listar_reglas_activas() -> list[ReglaClasificacionDTO]`
- `buscar(texto: str, pagina: int = 1, filas_por_pagina: int = 20) -> list[ReglaClasificacionDTO]`
- `obtener_regla(regla_id: int) -> ReglaClasificacionDTO`
- `actualizar_regla(regla_id: int, ReglaClasificacionActualizarDTO) -> ReglaClasificacionDTO`
- `desactivar_regla(regla_id: int) -> ReglaClasificacionDTO`
- `importar_desde_json(ruta_json: Path, solo_si_vacio: bool = True) -> list[ReglaClasificacionDTO]`
- `obtener_reglas_para_motor() -> list[dict[str, object]]`

`ServicioEjecuciones`

- `registrar_inicio(EjecucionCrearDTO) -> EjecucionDTO`
- `finalizar_ejecucion(ejecucion_id: int, EjecucionFinalizarDTO) -> EjecucionDTO`
- `registrar_ejecucion_completa(EjecucionCrearDTO, EjecucionFinalizarDTO) -> EjecucionDTO`
- `obtener_ejecucion(ejecucion_id: int) -> EjecucionDTO`
- `listar_ejecuciones() -> list[EjecucionDTO]`
- `listar_recientes(limite: int = 20) -> list[EjecucionDTO]`

`ServicioTiposFarmacia`

- `listar_tipos() -> list[TipoFarmaciaDTO]`
- `obtener_tipo(tipo_id: int) -> TipoFarmaciaDTO`
- `obtener_por_codigo(codigo: str) -> TipoFarmaciaDTO`

## DTOs principales

Entradas de creacion y actualizacion:

- `ClinicaCrearDTO`, `ClinicaActualizarDTO`
- `FarmaciaCrearDTO`, `FarmaciaActualizarDTO`
- `ListaConfigurableCrearDTO`, `ListaConfigurableActualizarDTO`
- `ItemListaCrearDTO`, `ItemListaActualizarDTO`
- `ReglaClasificacionCrearDTO`, `ReglaClasificacionActualizarDTO`, `CondicionReglaCrearDTO`
- `EjecucionCrearDTO`, `EjecucionFinalizarDTO`

Salidas hacia UI:

- `ClinicaDTO`
- `FarmaciaDTO`, `TipoFarmaciaDTO`
- `ListaConfigurableDTO`, `ItemListaDTO`
- `ReglaClasificacionDTO`, `CondicionReglaDTO`
- `EjecucionDTO`
- `PrevisualizacionImportacionDTO`, `ResultadoImportacionCatalogoDTO`, `ErrorImportacionDTO`, `ItemImportacionDTO`
- `FarmaciaDetectadaDTO`, `ResultadoDeteccionFarmaciasDTO`, `FarmaciaDetectadaActualizarDTO`, `ConfirmacionFarmaciaDetectadaDTO`, `ResultadoConfirmacionFarmaciasDTO`

## Ejemplos de uso

Buscar farmacias para una tabla paginada:

```python
with sesion_scope() as sesion:
    servicio = ServicioFarmacias(sesion)
    pagina = servicio.buscar("farmacia", pagina=1, filas_por_pagina=25)
```

Crear una regla simple:

```python
from dto.regla_dto import CondicionReglaCrearDTO, ReglaClasificacionCrearDTO

with sesion_scope() as sesion:
    servicio = ServicioReglas(sesion)
    regla = servicio.crear_regla(
        ReglaClasificacionCrearDTO(
            nombre="devoluciones",
            tipologia_resultado="DEVOLUCIONES",
            prioridad=50,
            condiciones=[
                CondicionReglaCrearDTO(
                    campo="TIPO_TRANSACCION",
                    operador="IGUAL",
                    valor_texto="RMA_RECEIPT",
                )
            ],
        )
    )
```

Registrar una ejecucion:

```python
with sesion_scope() as sesion:
    servicio = ServicioEjecuciones(sesion)
    ejecucion = servicio.registrar_inicio(EjecucionCrearDTO(archivo_nombre="movimientos.xlsx"))
    servicio.finalizar_ejecucion(
        ejecucion.id,
        EjecucionFinalizarDTO(
            estado="CLASIFICADA",
            total_registros=100,
            total_columnas=12,
            total_clasificados=90,
            total_sin_clasificar=10,
        ),
    )
```

Importar catalogos desde Excel:

```python
from servicios.servicio_importacion_catalogos import ServicioImportacionCatalogos

with sesion_scope() as sesion:
    servicio = ServicioImportacionCatalogos(sesion)
    preview = servicio.previsualizar_importacion("catalogo_farmacias.xlsx", limite=20)
    resultado = servicio.importar_farmacias_desde_excel(
        lista_id=3,
        ruta_archivo="catalogo_farmacias.xlsx",
        columna_codigo="CODIGO",
        columna_nombre="NOMBRE",
    )
```

Detectar farmacias para la futura pantalla Clinica y farmacias:

```python
from servicios.servicio_deteccion_farmacias import ServicioDeteccionFarmacias

with sesion_scope() as sesion:
    servicio = ServicioDeteccionFarmacias(sesion)
    resultado = servicio.detectar_farmacias_en_archivo("movimientos.xlsx", clinica_id=1)
    nuevas = [
        farmacia
        for farmacia in resultado.farmacias_detectadas
        if farmacia.estado_deteccion in {"NUEVA", "AMBIGUA"}
    ]
```

## Notas para PySide6

- Los widgets deben recibir DTOs o diccionarios derivados de DTOs, nunca instancias ORM.
- Abra y cierre sesiones en controladores, presenters o funciones de aplicacion, no dentro de los widgets visuales.
- Capture `ErrorDominio` para mostrar mensajes claros con `QMessageBox` o un panel de estado.
- Para operaciones pesadas como lectura de Excel o exportacion, use workers Qt si el flujo llega a bloquear la ventana.
- Las busquedas actuales retornan paginas 1-indexed; si se necesita total de registros para paginadores visuales, agregue un DTO de resultado paginado sin cambiar los modelos ORM.
