"""Capa 3 — Estado entre periodos.

Sin historial persistido el Art. 15, fracc. III (dos clasificaciones
consecutivas en C derivan en D) es inimplementable.
"""
from acr.persistencia.almacen import (
    ESQUEMA_VERSION,
    Almacen,
    EsquemaIncompatibleError,
    PeriodoDuplicadoError,
    PeriodoRegistrado,
)

__all__ = [
    "ESQUEMA_VERSION",
    "Almacen",
    "EsquemaIncompatibleError",
    "PeriodoDuplicadoError",
    "PeriodoRegistrado",
]
