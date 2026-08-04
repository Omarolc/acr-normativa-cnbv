"""Capa 2 — Motor de calculo puro. Unica fuente de verdad de cada cifra.

Ningun otro modulo recalcula lo que aqui se calcula. El validador consume
este resultado; no lo reproduce.
"""
from acr.motor.capitalizacion import (
    Capitalizacion,
    CapitalNeto,
    Clasificacion,
    EstadoInconsistenteError,
    InsumoFaltanteError,
    LimiteActivos,
    PersonasRelacionadas,
    calcular_capital_neto,
    calcular_capitalizacion,
    clasificar,
    evaluar_limite_activos,
    evaluar_personas_relacionadas,
)

__all__ = [
    "CapitalNeto",
    "Capitalizacion",
    "Clasificacion",
    "EstadoInconsistenteError",
    "InsumoFaltanteError",
    "LimiteActivos",
    "PersonasRelacionadas",
    "calcular_capital_neto",
    "calcular_capitalizacion",
    "clasificar",
    "evaluar_limite_activos",
    "evaluar_personas_relacionadas",
]
