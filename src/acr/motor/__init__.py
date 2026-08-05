"""Capa 2 — Motor de cálculo puro. Única fuente de verdad de cada cifra.

Ningún otro módulo recalcula lo que aquí se calcula.
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
from acr.motor.cartera import (
    Credito,
    CreditoCalificado,
    EsquemaPagosNoPrevistoError,
    InsumoCarteraFaltanteError,
    ResumenCartera,
    calificar_cartera,
    calificar_credito,
    dias_mora,
    es_cartera_vencida,
    porcentaje_estimacion,
)
from acr.motor.certificados import (
    Certificado,
    EvaluacionCertificado,
    RequisitoDesconocidoError,
    ResumenCertificados,
    evaluar_certificado,
    evaluar_certificados,
)

__all__ = [
    "CapitalNeto",
    "Capitalizacion",
    "Certificado",
    "Clasificacion",
    "Credito",
    "CreditoCalificado",
    "EsquemaPagosNoPrevistoError",
    "EstadoInconsistenteError",
    "EvaluacionCertificado",
    "InsumoCarteraFaltanteError",
    "InsumoFaltanteError",
    "LimiteActivos",
    "PersonasRelacionadas",
    "RequisitoDesconocidoError",
    "ResumenCartera",
    "ResumenCertificados",
    "calcular_capital_neto",
    "calcular_capitalizacion",
    "calificar_cartera",
    "calificar_credito",
    "clasificar",
    "dias_mora",
    "es_cartera_vencida",
    "evaluar_certificado",
    "evaluar_certificados",
    "evaluar_limite_activos",
    "evaluar_personas_relacionadas",
    "porcentaje_estimacion",
]
