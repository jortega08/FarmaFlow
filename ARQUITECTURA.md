# Arquitectura - FarmaFlow

Documento de arquitectura tecnica que describe la aplicacion, su estado, los modulos, las clases, las funciones, los objetos y las dependencias externas.

---

## 1. Vision general

Aplicacion de escritorio en Python orientada a leer archivos Excel exportados desde Oracle con movimientos de inventario de farmacia, validar su estructura, normalizar contenido, detectar farmacias, preclasificar cada fila por tipologia mediante reglas externas configurables y exportar el resultado a un archivo Excel multihoja con formato.

**Estilo arquitectonico:** monolito de capas con separacion estricta entre interfaz (PySide6/Qt), logica de negocio (pandas) y modelos de datos (dataclasses). La configuracion vive en JSON externos y la comunicacion entre capas se realiza con `dataclass` inmutables-por-convenio.

**Flujo macro de la aplicacion:**

```
[Usuario]
   |
   v
main.py  ->  configura logging  ->  inicia QApplication  ->  VentanaPrincipal
                                                                   |
                            +--------------------------------------+--------------------------------------+
                            |                                                                             |
                       VistaCargaArchivo                                                          VistaResumenArchivo
                            |                                                                             |
                            v                                                                             v
                       LectorExcel.cargar_archivo                                          PanelInformacionArchivo
                            |
       +--------------------+----------------------+----------------------+----------------------+
       |                    |                      |                      |                      |
ValidadorEstructura  NormalizadorDatos     DetectorFarmacias     ClasificadorTipologia    GeneradorResumen
       |                    |                      |                      |                      |
       +-----------------------------------+-------+----------------------+----------------------+
                                           v
                                    ResultadoCarga
                                           |
                                           v
                            VistaValidacionPreclasificacion (ambos paneles)
                                           |
                                           v
                                  ExportadorExcel.exportar  ->  archivo .xlsx en /salidas
```

---

## 2. Estado de la aplicacion

El estado **no es global**. Vive distribuido en tres lugares y se propaga por composicion.

### 2.1 Estado en memoria

| Donde | Que guarda | Tipo | Persistencia |
|---|---|---|---|
| `VentanaPrincipal._configuracion` | parametros generales (nombre app, dimensiones, hoja por defecto, rutas) | `dict[str, Any]` | hasta el cierre de la app |
| `VentanaPrincipal._resultado_carga_actual` | ultimo resultado de carga procesado | `ResultadoCarga \| None` | hasta nuevo procesamiento o limpieza |
| `VentanaPrincipal._exportador_excel` | instancia reutilizable del exportador | `ExportadorExcel` | toda la sesion |
| `VistaCargaArchivo._lector_excel` | instancia reutilizable del lector | `LectorExcel` | toda la sesion |
| `VistaCargaArchivo._ruta_archivo` (texto) | ruta del archivo seleccionado | `QLabel` | hasta limpiar |
| Paneles (`PanelValidacion`, `PanelPreclasificacion`, ...) | textos, contadores y listas visibles | widgets Qt | hasta `limpiar()` |

### 2.2 Estado en disco

- `configuracion/configuracion_general.json` - parametros generales.
- `configuracion/columnas_requeridas.json` - estructura Oracle minima.
- `configuracion/alias_columnas.json` - alias por columna canonica.
- `configuracion/reglas_tipologia.json` - reglas declarativas para preclasificar.
- `logs/<app>_YYYYMMDD.log` - registro de sesion.
- `salidas/clasificado_<base>_<timestamp>.xlsx` - archivos exportados.
- `datos_prueba/movimientos_simulados.xlsx` - dataset sintetico.

### 2.3 Maquina de estados de la UI (informal)

```
LISTO
  |  seleccionar_archivo()
  v
ARCHIVO_SELECCIONADO  -- cancelar -->  LISTO
  |  cargar_archivo()
  v
PROCESANDO
  |
  +-- exito + estructura valida   --> ARCHIVO_CARGADO   (export disponible)
  +-- exito + estructura invalida --> ESTRUCTURA_INVALIDA (export deshabilitado)
  +-- fallo                        --> ERROR_LECTURA   (export deshabilitado)
                  |
                  | exportacion_solicitada()
                  v
              EXPORTACION_EXITOSA / ERROR_EXPORTACION
```

Los mensajes literales viven centralizados en `utilidades.mensajes.MensajesInterfaz`.

---

## 3. Estructura de carpetas

```
clasificador_farmacia/
├─ main.py                     # punto de entrada
├─ requirements.txt            # PySide6, pandas, openpyxl, xlrd
├─ README.md
├─ ARQUITECTURA.md             # (este documento)
├─ Documentacion_Clasificador_Farmacia.docx
│
├─ configuracion/              # JSON externos de configuracion
├─ interfaz/                   # capa Qt (vistas + componentes + estilos)
│   ├─ ventana_principal.py
│   ├─ estilos.py
│   ├─ vistas/
│   └─ componentes/
├─ logica/                     # capa de negocio (pandas)
├─ modelos/                    # dataclasses de transporte
├─ utilidades/                 # helpers transversales
├─ scripts/                    # scripts auxiliares (no productivos)
├─ tests/                      # unittest (3 archivos)
├─ datos_prueba/               # excels sinteticos
├─ logs/                       # logs por dia
└─ salidas/                    # archivos exportados
```

---

## 4. Punto de entrada: `main.py`

**Responsabilidad:** arrancar la aplicacion.

**Flujo:**
1. Carga `configuracion/configuracion_general.json` con `cargar_json` + `resolver_ruta_proyecto`.
2. Llama `configurar_registro(...)` para preparar logging dual (consola + archivo en `/logs`).
3. Crea `QApplication`, fija nombre de aplicacion y aplica `obtener_estilos_base()` como hoja de estilos global (QSS).
4. Instancia `VentanaPrincipal(configuracion=...)`, la muestra y entra en el bucle Qt con `aplicacion.exec()`.

**Funcion publica:** `main() -> int` — retorna el codigo de salida del bucle Qt.

---

## 5. Capa de interfaz (`interfaz/`)

Construida sobre **PySide6 6.7+**. Sigue el patron *vistas que orquestan + componentes que renderizan*. No contiene logica de negocio: delega en `logica/`.

### 5.1 `interfaz/estilos.py`

- **`obtener_estilos_base() -> str`**: devuelve la hoja de estilos QSS global. Define una paleta clara con tarjetas redondeadas (`#ffffff` sobre `#f2f5f7`), botones por rol (`botonPrincipal`, `botonSecundario`, `botonExito`, `botonTerciario`), insignias de estado (`insigniaCorrecta`, `insigniaError`, `insigniaAdvertencia`, `insigniaInfo`, `insigniaNeutra`) e indicadores en `BarraEstado`. Toda la apariencia se controla por `objectName` para repintar dinamicamente con `style().unpolish/polish`.

### 5.2 `interfaz/ventana_principal.py`

- **`VentanaPrincipal(QMainWindow)`** — contenedor raiz. Recibe el `dict` de configuracion.
  - Instancias internas:
    - `_barra_estado: BarraEstado`
    - `_vista_carga: VistaCargaArchivo`
    - `_vista_resumen: VistaResumenArchivo`
    - `_vista_validacion_preclasificacion: VistaValidacionPreclasificacion`
    - `_exportador_excel: ExportadorExcel`
    - `_resultado_carga_actual: ResultadoCarga | None`
  - Metodos privados:
    - `_configurar_interfaz()` — arma layout: `QScrollArea` -> contenedor con encabezado, zona superior (carga | resumen) y panel inferior de validacion+preclasificacion. Inserta la `BarraEstado` en una `QStatusBar`.
    - `_crear_encabezado()` — barra superior con titulo, subtitulo y "breadcrumb" del flujo (`Cargar archivo > Validar > Clasificar > Exportar`).
    - `_conectar_eventos()` — conecta signals de `_vista_carga`:
      - `archivo_cargado` -> `_mostrar_resumen_archivo`
      - `exportacion_solicitada` -> `_exportar_resultado_actual`
      - `estado_actualizado` -> `_actualizar_estado`
      - `vista_limpiada` -> `_limpiar_resumen_archivo`
    - `_mostrar_resumen_archivo(resultado)` — actualiza `_vista_resumen` y `_vista_validacion_preclasificacion`, evalua exportabilidad.
    - `_limpiar_resumen_archivo()` — resetea estado y vistas.
    - `_actualizar_estado(mensaje)` — sincroniza barra de estado y badge en la vista de carga.
    - `_exportar_resultado_actual()` — orquesta llamada a `generar_estructuras_exportacion` + `ExportadorExcel.exportar`. Muestra `QMessageBox` con resultado.
    - `_resultado_es_exportable(resultado)` — invariante: hay carga exitosa, estructura valida y `dataframe_procesado` no vacio.

### 5.3 `interfaz/vistas/`

#### 5.3.1 `vista_inicio.py`
- **`VistaInicio(QFrame)`** — vista de bienvenida (no se usa en el flujo actual; queda como placeholder). Tiene `Signal solicitar_seleccion_archivo`.

#### 5.3.2 `vista_carga_archivo.py`
- **`VistaCargaArchivo(QFrame)`** — orquesta seleccion, lectura y limpieza.
  - **Signals:** `archivo_cargado(object)`, `exportacion_solicitada()`, `estado_actualizado(str)`, `vista_limpiada()`.
  - Composicion: `PanelAcciones` + `QLabel` ruta + `QLabel` estado (insignia) + `QLabel` mensajes recientes.
  - **Slots/metodos publicos:**
    - `seleccionar_archivo()` — `QFileDialog` filtrando `.xlsx/.xls`.
    - `cargar_archivo()` — pone cursor `WaitCursor`, llama `LectorExcel.cargar_archivo(Path)` y emite `archivo_cargado`.
    - `limpiar()` — restablece la vista y emite `vista_limpiada`.
    - `establecer_exportacion_disponible(bool)` — habilita/deshabilita boton exportar.
    - `mostrar_resultado_exportacion(mensaje, exito)` — pinta resultado.
    - `actualizar_estado_flujo(mensaje)` — actualiza el badge.
  - **Metodos privados:**
    - `_mostrar_mensaje(mensaje, tipo)` — mapa `info|exito|advertencia|error` -> `objectName`.
    - `_obtener_nombre_estado(mensaje)` — heuristica por palabra clave -> tipo de insignia.
    - `_aplicar_estilo(widget)` — `unpolish/polish` para repintar.

#### 5.3.3 `vista_resumen_archivo.py`
- **`VistaResumenArchivo(QFrame)`** — alterna placeholder vacio vs `PanelInformacionArchivo`.
  - `actualizar_resultado(resultado: ResultadoCarga)` — esconde placeholder, pinta panel.
  - `limpiar()` — vuelve al placeholder.

#### 5.3.4 `vista_validacion_preclasificacion.py`
- **`VistaValidacionPreclasificacion(QFrame)`** — agrupa `PanelValidacion` y `PanelPreclasificacion` en `QHBoxLayout` con stretch 1:1.
  - `actualizar_resultado(resultado: ResultadoCarga)` — propaga a ambos paneles con `resultado_validacion+resumen_validacion` y `resultado_preclasificacion+resumen_preclasificacion`.
  - `limpiar()` — limpia ambos paneles.

### 5.4 `interfaz/componentes/`

#### 5.4.1 `barra_estado.py`
- **`BarraEstado(QFrame)`** — pildora inferior con indicador circular + texto.
  - `actualizar_mensaje(mensaje)` — pinta texto y elige color del indicador (`indicadorEstadoNeutro|Info|Correcto|Advertencia|Error`) por keyword.

#### 5.4.2 `panel_acciones.py`
- **`PanelAcciones(QWidget)`** — columna de cuatro botones.
  - **Signals:** `solicitar_seleccion`, `solicitar_carga`, `solicitar_exportacion`, `solicitar_limpieza`.
  - Botones: `Seleccionar archivo`, `Procesar archivo`, `Exportar resultado`, `Limpiar`.
  - `actualizar_estado_botones(hay_archivo, puede_exportar)` — habilita/deshabilita combinaciones.

#### 5.4.3 `panel_informacion_archivo.py`
- **`PanelInformacionArchivo(QFrame)`** — tarjeta con metadatos del archivo y 5 metricas.
  - `actualizar_desde_resultado(resultado: ResultadoCarga)` — rellena nombre, hoja, badge de estado y metricas: `total_registros`, `total_columnas`, `farmacias_detectadas`, `registros_clasificados`, `registros_sin_clasificar`.
  - `limpiar()` — vuelve a "-" y badge neutro.

#### 5.4.4 `panel_validacion.py`
- **`PanelValidacion(QFrame)`** — diagnostico estructural.
  - Cabecera (titulo + insignia "Valida/Invalida"), bloque de observacion, 4 contadores (`Encontradas`, `Faltantes`, `Mapeadas por alias`, `Adicionales`) y 4 `QListWidget` con los nombres concretos.
  - `actualizar_desde_resultado(resultado, resumen)` — lee `columnas_encontradas/faltantes/mapeadas_por_alias/desconocidas` del resumen y ajusta colores.

#### 5.4.5 `panel_preclasificacion.py`
- **`PanelPreclasificacion(QFrame)`** — resumen operativo de la clasificacion.
  - Estado, descripcion, 5 metricas (`Registros`, `Clasificados`, `Sin clasificar`, `Tipologias`, `Farmacias`) y 2 listas con conteos por tipologia y por farmacia.
  - `actualizar_desde_resultado(resultado, resumen)`, `mostrar_no_disponible(mensaje)`, `limpiar()`.

---

## 6. Capa de logica (`logica/`)

Negocio puro sobre `pandas.DataFrame`. Sin acceso a Qt. Cada componente recibe sus dependencias externas por argumento o las resuelve via `utilidades.rutas.resolver_ruta_proyecto`.

### 6.1 `lector_excel.py`
- **`LectorExcel`** — orquestador del pipeline de carga.
  - Constante: `EXTENSIONES_VALIDAS = {".xlsx", ".xls"}`.
  - Construccion: instancia `ValidadorEstructura`, `NormalizadorDatos`, `DetectorFarmacias`, `ClasificadorTipologia`. Lee `hoja_por_defecto` de la configuracion.
  - **`cargar_archivo(ruta_archivo: Path) -> ResultadoCarga`** — pipeline:
    1. Validar existencia y extension.
    2. Abrir con `pd.ExcelFile`, elegir hoja con `_seleccionar_hoja` (preferida -> primera disponible).
    3. Leer con `pd.read_excel`, generar resumen basico (`generar_resumen_dataframe`).
    4. Validar estructura (`ValidadorEstructura.validar`).
    5. Si la estructura es invalida: retornar `ResultadoCarga` con `estructura_valida=False`.
    6. Si es valida: normalizar (`NormalizadorDatos.normalizar`), detectar farmacias (`DetectorFarmacias.detectar`), clasificar (`ClasificadorTipologia.clasificar`), generar resumen (`generar_resumen_preclasificacion`) y retornar `ResultadoCarga` completo.
  - **Captura especifica de excepciones:** `FileNotFoundError`, `ValueError`, `Exception` generica con mensajes en `MensajesInterfaz`.

### 6.2 `validador_estructura.py`
- **`ValidadorEstructura`** — valida columnas contra `columnas_requeridas.json` + `alias_columnas.json`.
  - **`validar(columnas_archivo: list[str]) -> ResultadoValidacion`**:
    - Construye un indice de alias `{alias_normalizado -> columna_canonica}` (`_construir_indice_alias`).
    - Recorre las columnas del archivo, las normaliza con `normalizar_nombre_columna` y las mapea.
    - Reporta `columnas_encontradas`, `columnas_faltantes`, `columnas_mapeadas` (canonica -> original), `columnas_desconocidas`.
    - `estructura_valida = no hay faltantes` (las opcionales no afectan el veredicto).
  - **Tolerancia a fallos:** si los JSON no se pueden cargar retorna `exito=False` con `ResultadoValidacion` minimal.

### 6.3 `normalizador_datos.py`
- **`NormalizadorDatos`** — renombra columnas a canonicas y normaliza el contenido de campos clave.
  - Constante `COLUMNAS_TEXTO_CLAVE = ("SUBINVENTARIO","ORG_ORIGEN","ORG_DESTINO","TIPO_TRANSACCION","TIPO_ORIGEN","ORIGEN","MOTIVO","TIPOLOGIA")`.
  - **`normalizar(dataframe, columnas_mapeadas) -> pd.DataFrame`** — copia profunda, aplica `rename`, mapea `normalizar_texto` columna a columna sobre las claves disponibles.

### 6.4 `detector_farmacias.py`
- **`DetectorFarmacias`** — heuristica simple.
  - Constante `COLUMNAS_CANDIDATAS = ("ORG_DESTINO","ORG_ORIGEN")`.
  - **`detectar(dataframe) -> tuple[pd.DataFrame, dict[str,int]]`** — agrega columna `FARMACIA_DETECTADA` con el primer valor que contenga `"FARM"` (case-insensitive tras normalizar). Retorna conteos.

### 6.5 `clasificador_tipologia.py`
- **`ClasificadorTipologia`** — motor de reglas declarativas.
  - Constante `REGLAS_FALLBACK` — lista minima de respaldo si el JSON falla.
  - **`clasificar(dataframe) -> ResultadoPreclasificacion`** — recorre cada fila aplicando reglas ordenadas por `prioridad` (asc); agrega `TIPOLOGIA_PRELIMINAR` y `REGLA_APLICADA`. Calcula totales y top de tipologias/farmacias.
  - **`_cargar_reglas() -> list[dict]`** — lee JSON, valida con `_validar_regla`, descarta mal formadas, ordena.
  - **`_validar_regla(regla)`** — exige `resultado` no vacio, `condiciones` `dict` no vacio. Normaliza nombres de campo y valores.
  - **`_clasificar_fila(fila, reglas) -> (tipologia, nombre_regla)`** — primer match gana. Sin coincidencia: `("SIN_CLASIFICAR", "")`.
  - **`_coincide_regla(fila, condiciones) -> bool`** — todas las condiciones deben cumplirse; comodin `*` (`es_valor_comodin`) acepta cualquier valor.

### 6.6 `generador_resumen.py`
Modulo funcional (sin clases) con utilidades para resumir y preparar la exportacion.

- Constante `COLUMNAS_AUXILIARES_EXPORTACION = ("FARMACIA_DETECTADA","TIPOLOGIA_PRELIMINAR","REGLA_APLICADA")`.
- **`generar_resumen_dataframe(df) -> (filas, columnas, list[str])`**.
- **`generar_resumen_validacion(resultado) -> dict`** — empaqueta listas y dict para la UI.
- **`generar_resumen_preclasificacion(resultado) -> dict`** — totales, conteos y tabla cruzada.
- **`generar_estructuras_exportacion(df_original, df_procesado) -> dict[str, DataFrame]`** — orquesta `detalle_clasificado`, `sin_clasificar`, `resumen_tipologia`, `resumen_farmacia`, `cruce_farmacia_tipologia`.
- **`generar_detalle_clasificado(df_original, df_procesado)`** — copia las filas originales y le pega las 3 columnas auxiliares (rellenando con `""` cuando faltan).
- **`generar_sin_clasificar(df)`** — filtra `TIPOLOGIA_PRELIMINAR == "SIN_CLASIFICAR"`.
- **`generar_resumen_tipologia(df)`** — `value_counts` -> dataframe `[TIPOLOGIA_PRELIMINAR, CANTIDAD]`.
- **`generar_resumen_farmacia(df)`** — `value_counts` excluyendo vacio -> `[FARMACIA_DETECTADA, CANTIDAD]`.
- **`generar_cruce_farmacia_tipologia(df)`** — `pd.pivot_table` cruzando farmacia y tipologia con `count(REGLA_APLICADA)`.

### 6.7 `exportador_excel.py`
- **`ExportadorExcel`** — escribe un `.xlsx` multihoja con formato.
  - **`HOJAS_OBLIGATORIAS = ("ORIGINAL","DETALLE_CLASIFICADO","RESUMEN_TIPOLOGIA","RESUMEN_FARMACIA","CRUCE_FARMACIA_TIPOLOGIA","SIN_CLASIFICAR")`** — orden estable de salida.
  - Constantes de ancho: `ANCHO_MINIMO=12`, `ANCHO_MAXIMO=40`.
  - Constructor inicializa estilos `openpyxl`: `PatternFill` azul `#1F4E78`, `Font` blanco bold, `Alignment` centrado, `Border` `thin` `#D9E2F3`.
  - **`exportar(...) -> ResultadoExportacion`**:
    - Valida que haya detalle clasificado (de lo contrario `ResultadoExportacion(exito=False, ...)`).
    - Asegura `ruta_salida` (crea directorios). Construye nombre con `construir_nombre_archivo_salida`.
    - Abre `pd.ExcelWriter(engine="openpyxl")` y escribe las 6 hojas en orden, aplicando `_aplicar_formato_hoja` a cada una.
  - **`_aplicar_formato_hoja(hoja)`** — `freeze_panes="A2"`, formato del encabezado, `auto_filter` sobre dimensiones y autoancho clamp `[12,40]`.

---

## 7. Capa de modelos (`modelos/`)

Todos son `dataclass(slots=True)` que viajan entre capas. Sin metodos: solo datos.

| Clase | Campos relevantes |
|---|---|
| `ResultadoCarga` | `exito, mensaje, ruta_archivo, nombre_archivo, hoja_utilizada, cantidad_filas, cantidad_columnas, columnas, dataframe (no repr), dataframe_procesado (no repr), resultado_validacion, resultado_preclasificacion, resumen_validacion, resumen_preclasificacion, estructura_valida` |
| `ResultadoValidacion` | `exito, mensaje, columnas_originales, columnas_normalizadas, columnas_encontradas, columnas_faltantes, columnas_mapeadas (dict canonica->original), columnas_desconocidas, estructura_valida` |
| `ResultadoPreclasificacion` | `exito, mensaje, cantidad_registros, cantidad_clasificados, cantidad_sin_clasificar, tipologias_detectadas (dict), farmacias_detectadas (dict), dataframe_resultado (no repr)` |
| `ResultadoExportacion` | `exito, mensaje, ruta_salida, nombre_archivo, hojas_generadas, cantidad_registros_exportados` |

`modelos/__init__.py` re-exporta las cuatro clases para imports cortos.

---

## 8. Utilidades (`utilidades/`)

### 8.1 `rutas.py`
- **`obtener_ruta_proyecto() -> Path`** — calcula la raiz del proyecto.
- **`resolver_ruta_proyecto(*segmentos) -> Path`** — concatena.
- **`obtener_ruta_salidas(configuracion=None) -> Path`** — resuelve `ruta_salidas` desde configuracion (default `salidas`).
- **`asegurar_directorio(ruta) -> Path`** — `mkdir(parents=True, exist_ok=True)`.
- **`limpiar_nombre_archivo(nombre) -> str`** — sanea caracteres invalidos `<>:"/\\|?*`, colapsa espacios y guiones bajos. Fallback `"archivo"`.
- **`construir_nombre_archivo_salida(nombre_base="", extension=".xlsx") -> str`** — formato `clasificado_<base_limpia>_<YYYYMMDD_HHMMSS>.xlsx`.
- **`cargar_json(ruta) -> Any`** — `json.load` UTF-8.

### 8.2 `mensajes.py`
- **`MensajesInterfaz`** — clase con constantes de string para todos los mensajes de UI: `LISTO`, `PROCESANDO`, `ARCHIVO_CARGADO`, `ARCHIVO_SELECCIONADO`, `SELECCIONE_ARCHIVO`, `NO_SELECCION`, `ERROR_LECTURA`, `ERROR_SIN_ARCHIVO`, `ERROR_ARCHIVO_NO_EXISTE`, `ERROR_APERTURA`, `ERROR_ARCHIVO_INVALIDO`, `RESUMEN_GENERADO`, `ERROR_VALIDACION`, `ESTRUCTURA_INVALIDA`, `RESUMEN_VALIDADO_GENERADO`, `EXPORTACION_DISPONIBLE`, `EXPORTACION_EXITOSA`, `ERROR_EXPORTACION`, `ERROR_SIN_DATOS_EXPORTAR`, `ERROR_CARPETA_SALIDA`.

### 8.3 `registro.py`
- **`configurar_registro(nombre_aplicacion, ruta_logs)`** — configura un logger raiz con dos handlers (archivo `<app>_<YYYYMMDD>.log` UTF-8 + consola). Formato `%(asctime)s | %(levelname)s | %(name)s | %(message)s`. Idempotente via flag `_configurado_por_clasificador`.
- **`_normalizar_nombre(texto)`** — `lower + replace(" ","_")`.

### 8.4 `texto.py`
- **`quitar_espacios_repetidos(texto) -> str`** — colapsa whitespace.
- **`reemplazar_tildes(texto) -> str`** — `unicodedata.NFD` + filtro `Mn`.
- **`normalizar_texto(valor) -> str`** — `str -> strip -> sin tildes -> sin espacios repetidos -> upper`. `None`/`"nan"` -> `""`.
- **`normalizar_nombre_columna(valor) -> str`** — normaliza y reemplaza no-alfanumericos por `_`, sin guiones bajos repetidos.
- **`es_valor_comodin(valor) -> bool`** — `True` si normaliza a `"*"`.

---

## 9. Configuracion (`configuracion/`)

### 9.1 `configuracion_general.json`
```json
{
  "nombre_aplicacion": "FarmaFlow",
  "ancho_ventana": 1180,
  "alto_ventana": 760,
  "hoja_por_defecto": "Movimientos",
  "ruta_salidas": "salidas",
  "ruta_logs": "logs"
}
```

### 9.2 `columnas_requeridas.json`
- `columnas_requeridas`: `SUBINVENTARIO, ORG_ORIGEN, ORG_DESTINO, TIPO_TRANSACCION, TIPO_ORIGEN, ORIGEN, MOTIVO`.
- `columnas_opcionales`: `TIPOLOGIA`.
- `version: 2`. Las columnas opcionales se mapean si aparecen pero no provocan invalidez.

### 9.3 `alias_columnas.json`
Diccionario `columna_canonica -> [aliases]`. Ejemplos: `SUBINVENTARIO`/`SUB INVENTARIO`, `ORG_DESTINO`/`ORG DESTINO`/`ORGANIZACION_DESTINO`, etc. La normalizacion uniformiza espacios/tildes/mayusculas.

### 9.4 `reglas_tipologia.json`
Lista de reglas con la forma:
```json
{
  "nombre_regla": "ajustes_base_captura",
  "prioridad": 10,
  "condiciones": {
    "TIPO_TRANSACCION": ["ACCOUNT_ALIAS_ISSUE"],
    "TIPO_ORIGEN": ["ACCOUNT_ALIAS"],
    "ORG_DESTINO": ["16_FARMA_FARMACIA_INTERNA_CRS", "47_FARMA_ALMACEN_CIRUGIA_CRS"],
    "ORIGEN": ["AA PRODUCTOS AVERIADOS DE PUNTOS", "..."]
  },
  "resultado": "AJUSTES_BASE_CAPTURA"
}
```

Semantica:
- Cada regla define `condiciones` por campo canonico. Una fila las cumple si su valor (normalizado) esta en la lista, o si la lista contiene `"*"` (comodin).
- Las reglas se evaluan ordenadas por `prioridad` ascendente. La primera coincidencia gana.
- `prioridad`: `10` para reglas muy especificas (ajustes), `20-50` para reglas tipologicas, `999` para fallback (`conteo_ciclico_fallback`).
- Si ninguna regla coincide la tipologia es `SIN_CLASIFICAR`.

### 9.5 `reglas_tipologia_ejemplo.json.bak`
Backup de un set de reglas anterior, mantenido como referencia.

---

## 10. Scripts auxiliares (`scripts/`)

### 10.1 `generar_datos_prueba.py`
Genera `datos_prueba/movimientos_simulados.xlsx` con `openpyxl`. Una sola hoja `Movimientos` con 16 grupos sintetizados que cubren las 15 tipologias del cuadro de filtros + casos `SIN_CLASIFICAR` + conteo ciclico. Usa `random.Random(20260428)` para reproducibilidad. Funciones clave: `fila_base`, `generar_filas`, `escribir_excel`, `main`.

### 10.2 `generar_reglas_desde_excel.py`
Convierte un Excel de "Cuadro de Filtros" en `configuracion/reglas_tipologia.json`.
- Soporta paso de ruta por `sys.argv[1]`; default `~/Downloads/CRITERIOS DE FILTROS .xlsx`.
- **`detectar_secciones`** identifica encabezados de tipologia.
- **`construir_condiciones`** agrupa filas que comparten `TIPO_TRANSACCION+TIPO_ORIGEN` y unifica el resto de campos en listas.
- Tabla `ETIQUETA_A_CODIGO` traduce nombres de UI a codigos Oracle.
- Tabla `PRIORIDADES` impone los pesos por tipologia.
- Inyecta el `conteo_ciclico_fallback` al final.
- Salida: JSON UTF-8 con indent 2.

---

## 11. Tests (`tests/`)

Suite con `unittest`. Cada archivo agrega `Path(__file__).resolve().parents[1]` al `sys.path` para importar el proyecto sin instalacion.

### 11.1 `test_fase_2.py` — `PruebasFaseDos`
- `test_validacion_con_columnas_correctas`
- `test_validacion_con_columnas_faltantes`
- `test_mapeo_por_alias`
- `test_normalizacion_de_texto_y_columna`
- `test_detector_preliminar_de_farmacia`
- `test_preclasificacion_con_reglas_ejemplo`
- `test_regla_con_comodin_personalizada` (carga reglas desde un JSON temporal)
- `test_normalizador_renombra_y_normaliza_campos`

### 11.2 `test_fase_3.py` — `PruebasFaseTres`
- `test_generacion_resumen_tipologia`
- `test_generacion_resumen_farmacia`
- `test_generacion_cruce_farmacia_tipologia`
- `test_filtrado_de_sin_clasificar`
- `test_validacion_del_nombre_de_archivo_generado`
- `test_creacion_automatica_del_directorio_de_salida`
- `test_exportacion_exitosa_con_hojas_obligatorias` (verifica las 6 hojas obligatorias y `freeze_panes`/`auto_filter`)

### 11.3 `test_clasificador_tipologia_reglas.py` — `PruebasReglasTipologia`
- Cobre cada tipologia generada del cuadro: `dispensacion_al_paciente`, `devoluciones`, `entradas/salidas_prestamos_internos`, `entradas_cedi`, `ordenes_de_compra`, `salidas_prestamos_externos`, `entradas_consignacion`, `entradas_central_prep/rere`, `conteo_ciclico`, `prestamos_bopos`, `ajustes_base_captura`, `ajustes_inconsistencias`, `traslados_hacia_cedi`.
- Valida que el clasificador real (cargando `reglas_tipologia.json`) clasifique cada caso.

---

## 12. Dependencias externas

| Libreria | Version minima | Uso |
|---|---|---|
| **PySide6** | 6.7 | Toda la capa de interfaz: `QApplication`, `QMainWindow`, `QFrame`, `QLabel`, `QPushButton`, `QVBoxLayout`, `QHBoxLayout`, `QGridLayout`, `QListWidget`, `QFileDialog`, `QMessageBox`, `QStatusBar`, `QScrollArea`, `Signal`, `Qt`. |
| **pandas** | 2.2 | Lectura `pd.read_excel`/`pd.ExcelFile`, manipulacion `DataFrame`, `pivot_table`, `value_counts`, escritura via `pd.ExcelWriter`. |
| **openpyxl** | 3.1 | Engine de escritura para `.xlsx`. Estilos `PatternFill`, `Font`, `Alignment`, `Border`, `Side`. Lectura en scripts. |
| **xlrd** | 2.0 | Compatibilidad de lectura para `.xls` legacy. |

Bibliotecas estandar usadas: `json`, `re`, `unicodedata`, `logging`, `pathlib`, `datetime`, `dataclasses`, `typing`, `random`, `tempfile`, `unittest`, `sys`.

---

## 13. Convenciones transversales

- **Idioma:** todo el codigo, identificadores y mensajes estan en espanol sin tildes.
- **Tipado:** anotaciones obligatorias (`from __future__ import annotations` en cada modulo).
- **Inmutabilidad de modelos:** `dataclass(slots=True)`. No se mutan tras crearse.
- **Logging:** un `logger = logging.getLogger(__name__)` por clase/modulo. La configuracion del root logger ocurre una sola vez en `main`.
- **Errores:**
  - La capa de logica nunca lanza al UI: convierte excepciones en `ResultadoX(exito=False, mensaje=...)`.
  - Excepciones especificas (`FileNotFoundError`, `ValueError`) se manejan antes del fallback `Exception`.
- **Pintado dinamico de Qt:** se cambia `objectName` y se invoca `style().unpolish/polish` para forzar repintado QSS.
- **Senales:** las vistas se comunican hacia arriba con `Signal`. La logica nunca conoce `Signal`.
- **Normalizacion:** todo texto entrante a la logica pasa por `normalizar_texto`/`normalizar_nombre_columna` para garantizar comparaciones estables.

---

## 14. Ciclo de vida de una ejecucion tipica

1. **Inicio.** `main.py` arma `QApplication`, instancia `VentanaPrincipal`.
2. **Seleccion.** Click en *Seleccionar archivo* -> `QFileDialog` -> `_ruta_archivo` actualizado.
3. **Procesamiento.** Click en *Procesar archivo* -> `LectorExcel.cargar_archivo` ejecuta secuencia: `pd.ExcelFile -> pd.read_excel -> ValidadorEstructura.validar -> NormalizadorDatos.normalizar -> DetectorFarmacias.detectar -> ClasificadorTipologia.clasificar -> generar_resumen_*`.
4. **Resultado.** Se construye `ResultadoCarga` y se emite `archivo_cargado`. `VentanaPrincipal` distribuye al `PanelInformacionArchivo`, `PanelValidacion` y `PanelPreclasificacion`.
5. **Exportacion (opcional).** Click en *Exportar resultado* -> `generar_estructuras_exportacion` -> `ExportadorExcel.exportar` -> archivo en `salidas/clasificado_<base>_<timestamp>.xlsx` con 6 hojas.
6. **Limpieza.** Click en *Limpiar* -> emite `vista_limpiada` -> `VentanaPrincipal` resetea estado y vistas.

---

## 15. Limites conocidos

- Solo soporta estructura Oracle (la fase actual no contempla SAP).
- La deteccion de farmacia es heuristica simple por substring `FARM`.
- El motor de reglas es de coincidencia exacta + comodin `*`. No soporta regex, rangos numericos ni operadores.
- La preclasificacion recorre fila a fila con `iterrows`: aceptable para los volumenes esperados, pero no esta optimizada para datasets de millones de registros.
- La hoja de estilos es estatica (no hay temas oscuros ni variantes).
- La exportacion siempre genera las 6 hojas obligatorias, incluso vacias.
