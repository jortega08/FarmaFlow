"""Mensajes centralizados de interfaz y errores frecuentes."""


class MensajesInterfaz:
    """Coleccion de mensajes reutilizables en la aplicacion."""

    LISTO = "Listo."
    PROCESANDO = "Procesando archivo..."
    ARCHIVO_CARGADO = "Archivo cargado correctamente."
    ARCHIVO_SELECCIONADO = "Archivo seleccionado. Puede iniciar la carga."
    SELECCIONE_ARCHIVO = "Seleccione un archivo Excel para comenzar."
    NO_SELECCION = "No se selecciono ningun archivo."
    ERROR_LECTURA = "Error al leer archivo."
    ERROR_SIN_ARCHIVO = "Debe seleccionar un archivo antes de cargarlo."
    ERROR_ARCHIVO_NO_EXISTE = "El archivo seleccionado no existe."
    ERROR_APERTURA = "No fue posible abrir el archivo."
    ERROR_ARCHIVO_INVALIDO = "El archivo seleccionado no es un Excel valido."
    RESUMEN_GENERADO = "Archivo cargado correctamente. El resumen se encuentra disponible."
    ERROR_VALIDACION = "No fue posible validar la estructura del archivo."
    ESTRUCTURA_INVALIDA = (
        "Archivo cargado, pero la estructura Oracle es invalida. Revise columnas faltantes y mapeos."
    )
    RESUMEN_VALIDADO_GENERADO = (
        "Archivo cargado y validado. La preclasificacion preliminar ya se encuentra disponible."
    )
    EXPORTACION_DISPONIBLE = "La exportacion ya se encuentra disponible."
    EXPORTACION_EXITOSA = "Archivo exportado correctamente."
    ERROR_EXPORTACION = "No fue posible exportar el archivo."
    ERROR_SIN_DATOS_EXPORTAR = "No hay datos procesados listos para exportar."
    ERROR_CARPETA_SALIDA = "No fue posible preparar la carpeta de salida."
