"""Capa 0 — Registro normativo versionado.

La norma es DATO, no código. Ninguna constante regulatoria vive en un .py.
"""
from acr.normativa.esquema import Registro
from acr.normativa.registro import (
    RUTA_REGISTRO,
    RegistroNoVigenteError,
    VigenciaBloqueadaError,
    cargar_registro,
    hash_registro,
    verificar_fecha_corte_trimestral,
    verificar_vigencia,
)

__all__ = [
    "RUTA_REGISTRO",
    "Registro",
    "RegistroNoVigenteError",
    "VigenciaBloqueadaError",
    "cargar_registro",
    "hash_registro",
    "verificar_fecha_corte_trimestral",
    "verificar_vigencia",
]
