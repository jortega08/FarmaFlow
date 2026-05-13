"""Excepciones de dominio para servicios de aplicacion."""

from __future__ import annotations


class ErrorDominio(Exception):
    """Error esperado dentro de una operacion de dominio."""


class EntidadNoEncontradaError(ErrorDominio):
    """La entidad solicitada no existe."""


class DatoDuplicadoError(ErrorDominio):
    """La operacion viola una regla de unicidad funcional."""


class ValidacionDominioError(ErrorDominio):
    """Los datos de entrada no satisfacen reglas de negocio."""


class OperacionNoPermitidaError(ErrorDominio):
    """La operacion no es valida para el estado actual."""
