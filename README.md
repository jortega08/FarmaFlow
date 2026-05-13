# FarmaFlow

Aplicacion de escritorio en Python orientada a la carga, validacion estructural y preclasificacion inicial de archivos Excel exportados desde Oracle.

## Alcance de esta fase

- Interfaz base en PySide6.
- Seleccion y carga de archivos Excel.
- Validacion estructural con columnas requeridas y alias.
- Normalizacion de columnas y valores de texto clave.
- Deteccion preliminar de farmacias.
- Preclasificacion inicial por tipologia con reglas JSON y comodines.
- Resumen visual de validacion y preclasificacion.
- Configuracion centralizada en JSON.
- Sistema basico de logs.
- Base preparada para la exportacion y refinamiento de reglas en fases posteriores.

## Requisitos

- Python 3.11 o superior

## Ejecucion local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Ejecutable Windows

No hay un archivo `.spec` en el proyecto. Para generar un ejecutable con PyInstaller y conservar el icono de FarmaFlow:

```bash
pyinstaller --name FarmaFlow --windowed --icon "interfaz/assets/ICONO_FARMAFLOW.ico" --add-data "interfaz/assets;interfaz/assets" --add-data "configuracion;configuracion" main.py
```

El icono visible del `.exe` sale de `--icon`; los assets usados por la ventana se incluyen con `--add-data`.

## Estructura principal

- `interfaz/`: componentes visuales y vistas.
- `logica/`: lectura, validacion y placeholders de procesamiento.
- `tests/`: pruebas basicas de validacion, normalizacion y reglas.
- `modelos/`: estructuras de datos compartidas.
- `utilidades/`: rutas, mensajes y registro.
- `configuracion/`: archivos JSON de configuracion.

## Notas

- Esta version trabaja solo con la estructura principal de Oracle.
- SAP no forma parte de esta fase.
- La exportacion final multihoja se deja preparada para una fase posterior.
