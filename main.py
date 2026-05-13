from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from interfaz.branding import APP_USER_MODEL_ID, NOMBRE_APP, RUTA_ICONO_APP_ICO
from interfaz.estilos import obtener_estilos_base
from interfaz.ventana_principal import VentanaPrincipal
from interfaz.ventana_login import VentanaLogin
from persistencia.conexion import configurar_conexion
from persistencia.migraciones_utils import asegurar_base_datos_actualizada
from servicios.servicio_autenticacion import ServicioAutenticacion
from servicios.servicio_reglas import sincronizar_reglas_sistema_desde_json
from utilidades.registro import configurar_registro
from utilidades.rutas import (
    cargar_json,
    limpiar_nombre_archivo,
    obtener_ruta_logs,
    resolver_ruta_proyecto,
)
from utilidades.windows import configurar_app_user_model_id


def _configuracion_para_usuario(
    configuracion: dict[str, object],
    usuario_id: str,
) -> dict[str, object]:
    """Crea una configuracion aislada para los datos del usuario autenticado."""
    configuracion_usuario = dict(configuracion)
    usuario_limpio = limpiar_nombre_archivo(usuario_id).lower()
    configuracion_usuario["usuario_base_datos"] = usuario_limpio
    configuracion_usuario["copiar_plantilla_base_datos"] = False
    configuracion_usuario["ruta_salidas"] = f"salidas/{usuario_limpio}"
    return configuracion_usuario


def main() -> int:
    """Inicializa y ejecuta la aplicacion principal."""
    configurar_app_user_model_id(APP_USER_MODEL_ID)

    configuracion = cargar_json(resolver_ruta_proyecto("configuracion", "configuracion_general.json"))

    configurar_registro(
        nombre_aplicacion=configuracion["nombre_aplicacion"],
        ruta_logs=obtener_ruta_logs(configuracion),
    )

    aplicacion = QApplication(sys.argv)
    aplicacion.setApplicationName(NOMBRE_APP)
    aplicacion.setApplicationDisplayName(NOMBRE_APP)
    if RUTA_ICONO_APP_ICO.exists():
        aplicacion.setWindowIcon(QIcon(str(RUTA_ICONO_APP_ICO)))

    aplicacion.setStyleSheet(obtener_estilos_base())

    servicio_autenticacion = ServicioAutenticacion()
    login = VentanaLogin(servicio_autenticacion=servicio_autenticacion)
    if login.exec() != QDialog.Accepted:
        return 0
    if login.sesion is None:
        QMessageBox.critical(None, "Inicio de sesion", "No se pudo obtener la sesion del usuario.")
        return 1

    configuracion_usuario = _configuracion_para_usuario(
        configuracion,
        login.sesion.usuario_id,
    )

    try:
        asegurar_base_datos_actualizada(configuracion_usuario)
        configurar_conexion(configuracion_usuario)
        sincronizar_reglas_sistema_desde_json()
    except Exception as error:  # noqa: BLE001
        QMessageBox.critical(None, "Base de datos", str(error))
        return 1

    ventana = VentanaPrincipal(
        configuracion=configuracion_usuario,
        usuario_sesion=login.sesion,
    )
    ventana.showMaximized()

    return aplicacion.exec()


if __name__ == "__main__":
    sys.exit(main())
