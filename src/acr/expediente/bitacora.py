"""Bitácora de ejecución encadenada por hash.

Cada entrada incluye el hash de la anterior. Alterar un evento intermedio
rompe la cadena y `verificar_cadena()` lo detecta. Es la diferencia entre un
log —que cualquiera edita— y evidencia.

Función pura: los eventos y la semilla entran como parámetros.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntradaBitacora:
    secuencia: int
    evento: str
    detalle: str
    hash_previo: str
    hash: str

    def como_dict(self) -> dict[str, Any]:
        return {
            "secuencia": self.secuencia,
            "evento": self.evento,
            "detalle": self.detalle,
            "hash_previo": self.hash_previo,
            "hash": self.hash,
        }


def _hash_entrada(secuencia: int, evento: str, detalle: str, previo: str) -> str:
    payload = f"{secuencia}|{evento}|{detalle}|{previo}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encadenar(eventos: list[tuple[str, str]], semilla: str) -> list[EntradaBitacora]:
    """Construye la cadena. `semilla` ancla la bitácora a un insumo conocido."""
    if not eventos:
        raise ValueError("La bitácora no puede estar vacía.")
    entradas: list[EntradaBitacora] = []
    previo = hashlib.sha256(semilla.encode("utf-8")).hexdigest()
    for i, (evento, detalle) in enumerate(eventos, 1):
        actual = _hash_entrada(i, evento, detalle, previo)
        entradas.append(EntradaBitacora(i, evento, detalle, previo, actual))
        previo = actual
    return entradas


def verificar_cadena(entradas: list[EntradaBitacora], semilla: str) -> bool:
    """True solo si ninguna entrada fue alterada ni reordenada."""
    if not entradas:
        return False
    previo = hashlib.sha256(semilla.encode("utf-8")).hexdigest()
    for i, e in enumerate(entradas, 1):
        if e.secuencia != i or e.hash_previo != previo:
            return False
        if e.hash != _hash_entrada(e.secuencia, e.evento, e.detalle, e.hash_previo):
            return False
        previo = e.hash
    return True
