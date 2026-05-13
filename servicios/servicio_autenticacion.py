"""Servicio local de autenticacion para usuarios de la aplicacion."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from utilidades.rutas import asegurar_directorio, obtener_directorio_datos_app

_ITERACIONES_HASH = 240_000
_LONGITUD_SALT = 16


@dataclass(frozen=True)
class UsuarioSesion:
    """Datos minimos del usuario autenticado."""

    usuario_id: str
    usuario: str
    empresa: str
    nombres: str
    apellidos: str


class ErrorAutenticacion(ValueError):
    """Error controlado de validacion o autenticacion."""


class ServicioAutenticacion:
    """Administra usuarios locales con contrasenas hasheadas."""

    def __init__(self, ruta_usuarios: Path | None = None) -> None:
        if ruta_usuarios is None:
            ruta_usuarios = obtener_directorio_datos_app() / "seguridad" / "usuarios.json"
        self._ruta_usuarios = ruta_usuarios
        asegurar_directorio(self._ruta_usuarios.parent)

    def registrar(
        self,
        *,
        usuario: str,
        contrasena: str,
        empresa: str,
        nombres: str,
        apellidos: str,
    ) -> UsuarioSesion:
        """Registra un usuario nuevo y retorna la sesion creada."""
        usuario_limpio = self._limpiar_requerido(usuario, "Usuario")
        empresa_limpia = self._limpiar_requerido(empresa, "Empresa")
        nombres_limpio = self._limpiar_requerido(nombres, "Nombres")
        apellidos_limpio = self._limpiar_requerido(apellidos, "Apellidos")
        self._validar_contrasena(contrasena)

        datos = self._cargar_datos()
        usuario_normalizado = self._normalizar_usuario(usuario_limpio)
        if any(
            registro.get("usuario_normalizado") == usuario_normalizado
            for registro in datos["usuarios"]
        ):
            raise ErrorAutenticacion("Ya existe una cuenta con ese usuario.")

        salt = secrets.token_bytes(_LONGITUD_SALT)
        ahora = datetime.now().isoformat(timespec="seconds")
        datos["usuarios"].append(
            {
                "usuario": usuario_limpio,
                "usuario_normalizado": usuario_normalizado,
                "usuario_id": usuario_normalizado,
                "empresa": empresa_limpia,
                "nombres": nombres_limpio,
                "apellidos": apellidos_limpio,
                "salt": salt.hex(),
                "hash_contrasena": self._hash_contrasena(contrasena, salt),
                "creado_en": ahora,
                "actualizado_en": ahora,
            }
        )
        self._guardar_datos(datos)
        return UsuarioSesion(
            usuario_id=usuario_normalizado,
            usuario=usuario_limpio,
            empresa=empresa_limpia,
            nombres=nombres_limpio,
            apellidos=apellidos_limpio,
        )

    def autenticar(self, usuario: str, contrasena: str) -> UsuarioSesion:
        """Valida credenciales y retorna la sesion autenticada."""
        usuario_normalizado = self._normalizar_usuario(usuario)
        if not usuario_normalizado or not contrasena:
            raise ErrorAutenticacion("Ingrese usuario y contrasena.")

        registro = self._buscar_usuario(usuario_normalizado)
        if registro is None or not self._contrasena_coincide(registro, contrasena):
            raise ErrorAutenticacion("Usuario o contrasena incorrectos.")

        return self._crear_sesion(registro)

    def restablecer_contrasena(
        self,
        *,
        usuario: str,
        empresa: str,
        nueva_contrasena: str,
    ) -> UsuarioSesion:
        """Restablece la contrasena si usuario y empresa coinciden."""
        usuario_normalizado = self._normalizar_usuario(usuario)
        empresa_limpia = self._limpiar_requerido(empresa, "Empresa")
        self._validar_contrasena(nueva_contrasena)

        datos = self._cargar_datos()
        for registro in datos["usuarios"]:
            misma_empresa = str(registro.get("empresa", "")).strip().casefold()
            if (
                registro.get("usuario_normalizado") == usuario_normalizado
                and misma_empresa == empresa_limpia.casefold()
            ):
                salt = secrets.token_bytes(_LONGITUD_SALT)
                registro["salt"] = salt.hex()
                registro["hash_contrasena"] = self._hash_contrasena(
                    nueva_contrasena, salt
                )
                registro["actualizado_en"] = datetime.now().isoformat(
                    timespec="seconds"
                )
                self._guardar_datos(datos)
                return self._crear_sesion(registro)

        raise ErrorAutenticacion(
            "No encontramos una cuenta con ese usuario y empresa."
        )

    def _buscar_usuario(self, usuario_normalizado: str) -> dict[str, Any] | None:
        datos = self._cargar_datos()
        for registro in datos["usuarios"]:
            if registro.get("usuario_normalizado") == usuario_normalizado:
                return registro
        return None

    def _cargar_datos(self) -> dict[str, Any]:
        if not self._ruta_usuarios.exists():
            return {"usuarios": []}
        with self._ruta_usuarios.open("r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not isinstance(datos, dict) or not isinstance(datos.get("usuarios"), list):
            raise ErrorAutenticacion("El archivo local de usuarios no es valido.")
        return datos

    def _guardar_datos(self, datos: dict[str, Any]) -> None:
        temporal = self._ruta_usuarios.with_suffix(".tmp")
        with temporal.open("w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
        temporal.replace(self._ruta_usuarios)

    @staticmethod
    def _normalizar_usuario(usuario: str) -> str:
        return str(usuario).strip().casefold()

    @staticmethod
    def _limpiar_requerido(valor: str, etiqueta: str) -> str:
        limpio = str(valor).strip()
        if not limpio:
            raise ErrorAutenticacion(f"{etiqueta} es obligatorio.")
        return limpio

    @staticmethod
    def _validar_contrasena(contrasena: str) -> None:
        if len(str(contrasena)) < 6:
            raise ErrorAutenticacion("La contrasena debe tener al menos 6 caracteres.")

    @staticmethod
    def _hash_contrasena(contrasena: str, salt: bytes) -> str:
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            contrasena.encode("utf-8"),
            salt,
            _ITERACIONES_HASH,
        )
        return digest.hex()

    def _contrasena_coincide(
        self, registro: dict[str, Any], contrasena: str
    ) -> bool:
        try:
            salt = bytes.fromhex(str(registro["salt"]))
            hash_esperado = str(registro["hash_contrasena"])
        except (KeyError, ValueError, TypeError):
            return False
        hash_recibido = self._hash_contrasena(contrasena, salt)
        return hmac.compare_digest(hash_esperado, hash_recibido)

    @staticmethod
    def _crear_sesion(registro: dict[str, Any]) -> UsuarioSesion:
        usuario = str(registro.get("usuario", ""))
        usuario_id = str(
            registro.get("usuario_id")
            or registro.get("usuario_normalizado")
            or usuario.strip().casefold()
        )
        return UsuarioSesion(
            usuario_id=usuario_id,
            usuario=usuario,
            empresa=str(registro.get("empresa", "")),
            nombres=str(registro.get("nombres", "")),
            apellidos=str(registro.get("apellidos", "")),
        )
