"""Utilidades especificas para integracion con Windows."""

from __future__ import annotations

import sys


def configurar_app_user_model_id(app_id: str) -> None:
    """Configura el AppUserModelID del proceso actual en Windows."""
    if not sys.platform.startswith("win"):
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        return
